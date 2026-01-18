"""Exam API endpoints for exam management.

This module provides REST API endpoints for exam operations
including creation, listing, updating, and deletion.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.schemas.auth import ErrorResponse
from app.schemas.exam import (
    ExamCreate,
    ExamListResponse,
    ExamResponse,
    ExamUpdate,
)
from app.services.exam_service import (
    ExamNotFoundError,
    ExamService,
    InvalidExamDataError,
)

router = APIRouter(prefix="/api/exams", tags=["Exams"])


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


def get_exam_service(request: Request) -> ExamService:
    """Get ExamService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return ExamService(db, tenant_id)


@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_exam(
    request: Request,
    data: ExamCreate,
    current_user: ActiveUserDep,
) -> ExamResponse:
    """Create a new exam.

    Args:
        request: The incoming request.
        data: Exam creation data.
        current_user: Current authenticated user.

    Returns:
        ExamResponse with created exam data.

    Raises:
        HTTPException: If permission denied or validation error.
    """
    # Check permission - only admins can create exams
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create exams",
                }
            },
        )

    service = get_exam_service(request)

    try:
        exam = service.create_exam(
            name=data.name,
            exam_type=data.exam_type,
            class_id=data.class_id,
            start_date=data.start_date,
            end_date=data.end_date,
            academic_year=data.academic_year,
        )

        return ExamResponse(
            id=exam.id,
            name=exam.name,
            exam_type=exam.exam_type.value,
            class_id=exam.class_id,
            class_name=exam.class_.name if exam.class_ else None,
            start_date=exam.start_date,
            end_date=exam.end_date,
            academic_year=exam.academic_year,
        )

    except InvalidExamDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "",
    response_model=ExamListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_exams(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    exam_type: str | None = Query(None, description="Filter by exam type"),
    academic_year: str | None = Query(None, description="Filter by academic year"),
    start_date: date | None = Query(None, description="Filter by start date"),
    end_date: date | None = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ExamListResponse:
    """List exams with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        exam_type: Optional exam type filter.
        academic_year: Optional academic year filter.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        ExamListResponse with paginated exam list.
    """
    service = get_exam_service(request)

    result = service.list_exams(
        class_id=class_id,
        exam_type=exam_type,
        academic_year=academic_year,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    return ExamListResponse(**result)


@router.get(
    "/{exam_id}",
    response_model=ExamResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Exam not found"},
    },
)
async def get_exam(
    request: Request,
    exam_id: int,
    current_user: ActiveUserDep,
) -> ExamResponse:
    """Get an exam by ID.

    Args:
        request: The incoming request.
        exam_id: The exam ID.
        current_user: Current authenticated user.

    Returns:
        ExamResponse with exam data.

    Raises:
        HTTPException: If exam not found.
    """
    service = get_exam_service(request)

    try:
        exam = service.get_exam(exam_id)

        return ExamResponse(
            id=exam.id,
            name=exam.name,
            exam_type=exam.exam_type.value,
            class_id=exam.class_id,
            class_name=exam.class_.name if exam.class_ else None,
            start_date=exam.start_date,
            end_date=exam.end_date,
            academic_year=exam.academic_year,
        )

    except ExamNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{exam_id}",
    response_model=ExamResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Exam not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_exam(
    request: Request,
    exam_id: int,
    data: ExamUpdate,
    current_user: ActiveUserDep,
) -> ExamResponse:
    """Update an exam.

    Args:
        request: The incoming request.
        exam_id: The exam ID.
        data: Exam update data.
        current_user: Current authenticated user.

    Returns:
        ExamResponse with updated exam data.

    Raises:
        HTTPException: If exam not found, permission denied, or validation error.
    """
    # Check permission - only admins can update exams
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update exams",
                }
            },
        )

    service = get_exam_service(request)

    try:
        exam = service.update_exam(
            exam_id=exam_id,
            name=data.name,
            exam_type=data.exam_type,
            start_date=data.start_date,
            end_date=data.end_date,
            academic_year=data.academic_year,
        )

        return ExamResponse(
            id=exam.id,
            name=exam.name,
            exam_type=exam.exam_type.value,
            class_id=exam.class_id,
            class_name=exam.class_.name if exam.class_ else None,
            start_date=exam.start_date,
            end_date=exam.end_date,
            academic_year=exam.academic_year,
        )

    except ExamNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidExamDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Exam not found"},
    },
)
async def delete_exam(
    request: Request,
    exam_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete an exam.

    Args:
        request: The incoming request.
        exam_id: The exam ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If exam not found or permission denied.
    """
    # Check permission - only admins can delete exams
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete exams",
                }
            },
        )

    service = get_exam_service(request)

    try:
        service.delete_exam(exam_id)
    except ExamNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
