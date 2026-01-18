"""Student API endpoints for student management.

This module provides REST API endpoints for student CRUD operations
including listing, creating, updating, and deleting students.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep, get_auth_service
from app.models.student import Gender, StudentStatus
from app.schemas.auth import ErrorResponse
from app.schemas.student import (
    StudentCreate,
    StudentListResponse,
    StudentProfileResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services.auth_service import AuthService
from app.services.student_service import (
    DuplicateAdmissionNumberError,
    DuplicateEmailError,
    StudentNotFoundError,
    StudentService,
)

router = APIRouter(prefix="/api/students", tags=["Students"])


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


def get_student_service(request: Request) -> StudentService:
    """Get StudentService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return StudentService(db, tenant_id)


@router.get(
    "",
    response_model=StudentListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_students(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    student_status: str | None = Query(None, alias="status", description="Filter by status"),
    search: str | None = Query(None, description="Search by name, email, or admission number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> StudentListResponse:
    """List students with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        section_id: Optional section ID filter.
        student_status: Optional status filter.
        search: Optional search query.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        StudentListResponse with paginated student list.
    """
    service = get_student_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if student_status:
        try:
            status_enum = StudentStatus(student_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {student_status}",
                    }
                },
            )

    result = service.list_students(
        class_id=class_id,
        section_id=section_id,
        status=status_enum,
        search=search,
        page=page,
        page_size=page_size,
    )

    return StudentListResponse(**result)


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Duplicate admission number or email"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_student(
    request: Request,
    data: StudentCreate,
    current_user: ActiveUserDep,
) -> StudentResponse:
    """Create a new student.

    Args:
        request: The incoming request.
        data: Student creation data.
        current_user: Current authenticated user.

    Returns:
        StudentResponse with created student data.

    Raises:
        HTTPException: If admission number or email already exists.
    """
    # Check permission - only admins and teachers can create students
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create students",
                }
            },
        )

    service = get_student_service(request)

    try:
        # Convert gender string to enum
        gender_enum = Gender(data.gender)

        # Convert profile_data to dict if provided
        profile_data = data.profile_data.model_dump() if data.profile_data else None

        student = service.create_student(
            admission_number=data.admission_number,
            email=data.email,
            password=data.password,
            date_of_birth=data.date_of_birth,
            gender=gender_enum,
            admission_date=data.admission_date,
            class_id=data.class_id,
            section_id=data.section_id,
            roll_number=data.roll_number,
            address=data.address,
            parent_ids=data.parent_ids,
            profile_data=profile_data,
        )

        return StudentResponse(
            id=student.id,
            admission_number=student.admission_number,
            class_id=student.class_id,
            section_id=student.section_id,
            roll_number=student.roll_number,
            date_of_birth=student.date_of_birth,
            gender=student.gender.value,
            address=student.address,
            admission_date=student.admission_date,
            status=student.status.value,
            user={
                "id": student.user.id,
                "email": student.user.email,
                "profile_data": student.user.profile_data,
                "is_active": student.user.is_active,
            } if student.user else None,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    except DuplicateAdmissionNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateEmailError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Student not found"},
    },
)
async def get_student(
    request: Request,
    student_id: int,
    current_user: ActiveUserDep,
) -> StudentResponse:
    """Get a student by ID.

    Args:
        request: The incoming request.
        student_id: The student ID.
        current_user: Current authenticated user.

    Returns:
        StudentResponse with student data.

    Raises:
        HTTPException: If student not found.
    """
    service = get_student_service(request)

    try:
        student = service.get_student(student_id)

        return StudentResponse(
            id=student.id,
            admission_number=student.admission_number,
            class_id=student.class_id,
            section_id=student.section_id,
            roll_number=student.roll_number,
            date_of_birth=student.date_of_birth,
            gender=student.gender.value,
            address=student.address,
            admission_date=student.admission_date,
            status=student.status.value,
            user={
                "id": student.user.id,
                "email": student.user.email,
                "profile_data": student.user.profile_data,
                "is_active": student.user.is_active,
            } if student.user else None,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    except StudentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Student not found"},
        409: {"model": ErrorResponse, "description": "Duplicate admission number"},
    },
)
async def update_student(
    request: Request,
    student_id: int,
    data: StudentUpdate,
    current_user: ActiveUserDep,
) -> StudentResponse:
    """Update a student.

    Args:
        request: The incoming request.
        student_id: The student ID.
        data: Student update data.
        current_user: Current authenticated user.

    Returns:
        StudentResponse with updated student data.

    Raises:
        HTTPException: If student not found or admission number exists.
    """
    # Check permission - only admins and teachers can update students
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update students",
                }
            },
        )

    service = get_student_service(request)

    try:
        # Convert status string to enum if provided
        status_enum = None
        if data.status:
            status_enum = StudentStatus(data.status)

        # Convert profile_data to dict if provided
        profile_data = data.profile_data.model_dump() if data.profile_data else None

        student = service.update_student(
            student_id=student_id,
            admission_number=data.admission_number,
            class_id=data.class_id,
            section_id=data.section_id,
            roll_number=data.roll_number,
            address=data.address,
            parent_ids=data.parent_ids,
            status=status_enum,
            profile_data=profile_data,
        )

        return StudentResponse(
            id=student.id,
            admission_number=student.admission_number,
            class_id=student.class_id,
            section_id=student.section_id,
            roll_number=student.roll_number,
            date_of_birth=student.date_of_birth,
            gender=student.gender.value,
            address=student.address,
            admission_date=student.admission_date,
            status=student.status.value,
            user={
                "id": student.user.id,
                "email": student.user.email,
                "profile_data": student.user.profile_data,
                "is_active": student.user.is_active,
            } if student.user else None,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    except StudentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateAdmissionNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Student not found"},
    },
)
async def delete_student(
    request: Request,
    student_id: int,
    current_user: ActiveUserDep,
    hard_delete: bool = Query(False, description="Permanently delete the student"),
) -> None:
    """Delete a student (soft delete by default).

    Args:
        request: The incoming request.
        student_id: The student ID.
        current_user: Current authenticated user.
        hard_delete: If True, permanently delete the record.

    Raises:
        HTTPException: If student not found or permission denied.
    """
    # Check permission - only admins can delete students
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete students",
                }
            },
        )

    service = get_student_service(request)

    try:
        service.delete_student(student_id, hard_delete=hard_delete)
    except StudentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )



@router.get(
    "/{student_id}/profile",
    response_model=StudentProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Student not found"},
    },
)
async def get_student_profile(
    request: Request,
    student_id: int,
    current_user: ActiveUserDep,
) -> StudentProfileResponse:
    """Get complete student profile with aggregated data.

    This endpoint returns the student's basic information along with
    aggregated attendance, grades, and fees data.

    Args:
        request: The incoming request.
        student_id: The student ID.
        current_user: Current authenticated user.

    Returns:
        StudentProfileResponse with complete profile data.

    Raises:
        HTTPException: If student not found.
    """
    service = get_student_service(request)

    try:
        profile = service.get_student_profile(student_id)

        return StudentProfileResponse(
            student={
                "id": profile["student"]["id"],
                "admission_number": profile["student"]["admission_number"],
                "class_id": profile["student"]["class_id"],
                "class_name": profile["student"]["class_name"],
                "section_id": profile["student"]["section_id"],
                "section_name": profile["student"]["section_name"],
                "roll_number": profile["student"]["roll_number"],
                "date_of_birth": profile["student"]["date_of_birth"],
                "gender": profile["student"]["gender"],
                "address": profile["student"]["address"],
                "admission_date": profile["student"]["admission_date"],
                "status": profile["student"]["status"],
                "user": profile["student"]["user"],
            },
            attendance={
                "total_days": profile["attendance"]["total_days"],
                "present_days": profile["attendance"]["present_days"],
                "absent_days": profile["attendance"]["absent_days"],
                "late_days": profile["attendance"]["late_days"],
                "half_days": profile["attendance"]["half_days"],
                "attendance_percentage": profile["attendance"]["attendance_percentage"],
            },
            grades=profile["grades"],
            fees={
                "total_amount": profile["fees"]["total_amount"],
                "total_paid": profile["fees"]["total_paid"],
                "balance": profile["fees"]["balance"],
                "pending_count": profile["fees"]["pending_count"],
                "recent_fees": profile["fees"]["recent_fees"],
            },
        )

    except StudentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
