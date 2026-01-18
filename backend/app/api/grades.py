"""Grade API endpoints for grade management.

This module provides REST API endpoints for grade operations
including creation, listing, updating, and report card generation.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.schemas.auth import ErrorResponse
from app.schemas.exam import (
    BulkGradeCreate,
    BulkGradeResponse,
    GradeAnalyticsResponse,
    GradeCreate,
    GradeListResponse,
    GradeResponse,
    GradeUpdate,
    ReportCardResponse,
)
from app.services.grade_service import (
    DuplicateGradeError,
    GradeNotFoundError,
    GradeService,
    InvalidGradeDataError,
)

router = APIRouter(prefix="/api/grades", tags=["Grades"])


def get_db(request: Request) -> Session:
    """Get database session from request state."""
    if hasattr(request.state, "db"):
        return request.state.db
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not available",
    )


def get_tenant_id(request: Request) -> int:
    """Get tenant ID from request state."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "TENANT_REQUIRED",
                    "message": "Tenant context is required",
                }
            },
        )
    return tenant_id


def get_grade_service(request: Request) -> GradeService:
    """Get GradeService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return GradeService(db, tenant_id)


@router.post(
    "",
    response_model=GradeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        409: {"model": ErrorResponse, "description": "Grade already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_grade(
    request: Request,
    data: GradeCreate,
    current_user: ActiveUserDep,
) -> GradeResponse:
    """Create a new grade entry with automatic grade letter calculation.

    The grade letter is automatically calculated based on the percentage
    using the configured grading scale.

    Args:
        request: The incoming request.
        data: Grade creation data.
        current_user: Current authenticated user.

    Returns:
        GradeResponse with created grade data including calculated grade letter.

    Raises:
        HTTPException: If permission denied, duplicate grade, or validation error.
    """
    # Check permission - only admins and teachers can create grades
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create grades",
                }
            },
        )

    service = get_grade_service(request)

    try:
        grade = service.create_grade(
            student_id=data.student_id,
            subject_id=data.subject_id,
            exam_id=data.exam_id,
            marks_obtained=data.marks_obtained,
            max_marks=data.max_marks,
            remarks=data.remarks,
        )

        percentage = service.calculate_percentage(
            grade.marks_obtained, grade.max_marks
        )

        return GradeResponse(
            id=grade.id,
            student_id=grade.student_id,
            student_name=None,  # Will be populated by service
            subject_id=grade.subject_id,
            subject_name=grade.subject.name if grade.subject else None,
            exam_id=grade.exam_id,
            exam_name=grade.exam.name if grade.exam else None,
            marks_obtained=float(grade.marks_obtained),
            max_marks=float(grade.max_marks),
            percentage=percentage,
            grade=grade.grade,
            remarks=grade.remarks,
        )

    except DuplicateGradeError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidGradeDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/bulk",
    response_model=BulkGradeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def bulk_create_grades(
    request: Request,
    data: BulkGradeCreate,
    current_user: ActiveUserDep,
) -> BulkGradeResponse:
    """Create multiple grade entries in bulk with automatic grade calculation.

    This endpoint allows teachers and admins to enter grades for multiple
    students at once. Grade letters are automatically calculated for each entry.
    If a grade already exists for a student/subject/exam combination, it will
    be updated.

    Args:
        request: The incoming request.
        data: Bulk grade creation data.
        current_user: Current authenticated user.

    Returns:
        BulkGradeResponse with summary of created grades.

    Raises:
        HTTPException: If permission denied or validation error.
    """
    # Check permission - only admins and teachers can create grades
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create grades",
                }
            },
        )

    service = get_grade_service(request)

    try:
        # Convert grades to dict format
        grades = [
            {
                "student_id": g.student_id,
                "marks_obtained": g.marks_obtained,
                "remarks": g.remarks,
            }
            for g in data.grades
        ]

        result = service.bulk_create_grades(
            subject_id=data.subject_id,
            exam_id=data.exam_id,
            max_marks=data.max_marks,
            grades=grades,
        )

        return BulkGradeResponse(**result)

    except InvalidGradeDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "",
    response_model=GradeListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_grades(
    request: Request,
    current_user: ActiveUserDep,
    student_id: int | None = Query(None, description="Filter by student ID"),
    subject_id: int | None = Query(None, description="Filter by subject ID"),
    exam_id: int | None = Query(None, description="Filter by exam ID"),
    class_id: int | None = Query(None, description="Filter by class ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> GradeListResponse:
    """List grades with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        student_id: Optional student ID filter.
        subject_id: Optional subject ID filter.
        exam_id: Optional exam ID filter.
        class_id: Optional class ID filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        GradeListResponse with paginated grade list.
    """
    service = get_grade_service(request)

    result = service.list_grades(
        student_id=student_id,
        subject_id=subject_id,
        exam_id=exam_id,
        class_id=class_id,
        page=page,
        page_size=page_size,
    )

    return GradeListResponse(**result)


@router.get(
    "/report-card/{student_id}",
    response_model=ReportCardResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Student not found"},
    },
)
async def get_report_card(
    request: Request,
    student_id: int,
    current_user: ActiveUserDep,
    academic_year: str | None = Query(None, description="Academic year filter"),
) -> ReportCardResponse:
    """Generate a report card for a student.

    This endpoint generates a comprehensive report card including all
    exam results, subject grades, and cumulative performance.

    Args:
        request: The incoming request.
        student_id: The student ID.
        current_user: Current authenticated user.
        academic_year: Optional academic year filter.

    Returns:
        ReportCardResponse with complete report card data.

    Raises:
        HTTPException: If student not found.
    """
    service = get_grade_service(request)

    try:
        result = service.get_report_card(
            student_id=student_id,
            academic_year=academic_year,
        )

        return ReportCardResponse(**result)

    except GradeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "/analytics",
    response_model=GradeAnalyticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        400: {"model": ErrorResponse, "description": "Missing required parameters"},
    },
)
async def get_grade_analytics(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int = Query(..., description="Class ID (required)"),
    exam_id: int = Query(..., description="Exam ID (required)"),
) -> GradeAnalyticsResponse:
    """Get grade analytics for a class and exam.

    This endpoint provides comprehensive analytics including class-level
    statistics, subject-level breakdown, and student rankings.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: The class ID (required).
        exam_id: The exam ID (required).

    Returns:
        GradeAnalyticsResponse with analytics data.
    """
    service = get_grade_service(request)

    result = service.get_grade_analytics(
        class_id=class_id,
        exam_id=exam_id,
    )

    return GradeAnalyticsResponse(**result)


@router.get(
    "/{grade_id}",
    response_model=GradeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Grade not found"},
    },
)
async def get_grade(
    request: Request,
    grade_id: int,
    current_user: ActiveUserDep,
) -> GradeResponse:
    """Get a grade by ID.

    Args:
        request: The incoming request.
        grade_id: The grade ID.
        current_user: Current authenticated user.

    Returns:
        GradeResponse with grade data.

    Raises:
        HTTPException: If grade not found.
    """
    service = get_grade_service(request)

    try:
        grade = service.get_grade(grade_id)
        percentage = service.calculate_percentage(
            grade.marks_obtained, grade.max_marks
        )

        student_name = None
        if grade.student and grade.student.user:
            first_name = grade.student.user.profile_data.get("first_name", "")
            last_name = grade.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return GradeResponse(
            id=grade.id,
            student_id=grade.student_id,
            student_name=student_name,
            subject_id=grade.subject_id,
            subject_name=grade.subject.name if grade.subject else None,
            exam_id=grade.exam_id,
            exam_name=grade.exam.name if grade.exam else None,
            marks_obtained=float(grade.marks_obtained),
            max_marks=float(grade.max_marks),
            percentage=percentage,
            grade=grade.grade,
            remarks=grade.remarks,
        )

    except GradeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{grade_id}",
    response_model=GradeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Grade not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_grade(
    request: Request,
    grade_id: int,
    data: GradeUpdate,
    current_user: ActiveUserDep,
) -> GradeResponse:
    """Update a grade entry with automatic grade letter recalculation.

    The grade letter is automatically recalculated when marks are updated.

    Args:
        request: The incoming request.
        grade_id: The grade ID.
        data: Grade update data.
        current_user: Current authenticated user.

    Returns:
        GradeResponse with updated grade data.

    Raises:
        HTTPException: If grade not found, permission denied, or validation error.
    """
    # Check permission - only admins and teachers can update grades
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update grades",
                }
            },
        )

    service = get_grade_service(request)

    try:
        grade = service.update_grade(
            grade_id=grade_id,
            marks_obtained=data.marks_obtained,
            max_marks=data.max_marks,
            remarks=data.remarks,
        )

        percentage = service.calculate_percentage(
            grade.marks_obtained, grade.max_marks
        )

        student_name = None
        if grade.student and grade.student.user:
            first_name = grade.student.user.profile_data.get("first_name", "")
            last_name = grade.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return GradeResponse(
            id=grade.id,
            student_id=grade.student_id,
            student_name=student_name,
            subject_id=grade.subject_id,
            subject_name=grade.subject.name if grade.subject else None,
            exam_id=grade.exam_id,
            exam_name=grade.exam.name if grade.exam else None,
            marks_obtained=float(grade.marks_obtained),
            max_marks=float(grade.max_marks),
            percentage=percentage,
            grade=grade.grade,
            remarks=grade.remarks,
        )

    except GradeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidGradeDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{grade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Grade not found"},
    },
)
async def delete_grade(
    request: Request,
    grade_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a grade.

    Args:
        request: The incoming request.
        grade_id: The grade ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If grade not found or permission denied.
    """
    # Check permission - only admins can delete grades
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete grades",
                }
            },
        )

    service = get_grade_service(request)

    try:
        service.delete_grade(grade_id)
    except GradeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
