"""Teacher API endpoints for teacher management.

This module provides REST API endpoints for teacher CRUD operations
including listing, creating, updating, and retrieving teacher data.
"""

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.models.teacher import TeacherStatus
from app.schemas.auth import ErrorResponse
from app.schemas.teacher import (
    TeacherClassesResponse,
    TeacherCreate,
    TeacherListResponse,
    TeacherResponse,
    TeacherUpdate,
)
from app.services.teacher_service import (
    DuplicateEmailError,
    DuplicateEmployeeIdError,
    TeacherNotFoundError,
    TeacherService,
)

router = APIRouter(prefix="/api/teachers", tags=["Teachers"])


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


def get_teacher_service(request: Request) -> TeacherService:
    """Get TeacherService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return TeacherService(db, tenant_id)


@router.get(
    "",
    response_model=TeacherListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_teachers(
    request: Request,
    current_user: ActiveUserDep,
    teacher_status: str | None = Query(None, alias="status", description="Filter by status"),
    search: str | None = Query(None, description="Search by name, email, or employee ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> TeacherListResponse:
    """List teachers with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        teacher_status: Optional status filter.
        search: Optional search query.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        TeacherListResponse with paginated teacher list.
    """
    service = get_teacher_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if teacher_status:
        try:
            status_enum = TeacherStatus(teacher_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {teacher_status}",
                    }
                },
            )

    result = service.list_teachers(
        status=status_enum,
        search=search,
        page=page,
        page_size=page_size,
    )

    return TeacherListResponse(**result)


@router.post(
    "",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        409: {"model": ErrorResponse, "description": "Duplicate employee ID or email"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_teacher(
    request: Request,
    data: TeacherCreate,
    current_user: ActiveUserDep,
) -> TeacherResponse:
    """Create a new teacher.

    Args:
        request: The incoming request.
        data: Teacher creation data.
        current_user: Current authenticated user.

    Returns:
        TeacherResponse with created teacher data.

    Raises:
        HTTPException: If employee ID or email already exists.
    """
    # Check permission - only admins can create teachers
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create teachers",
                }
            },
        )

    service = get_teacher_service(request)

    try:
        # Convert profile_data to dict if provided
        profile_data = data.profile_data.model_dump() if data.profile_data else None

        teacher = service.create_teacher(
            employee_id=data.employee_id,
            email=data.email,
            password=data.password,
            joining_date=data.joining_date,
            subjects=data.subjects,
            classes_assigned=data.classes_assigned,
            qualifications=data.qualifications,
            profile_data=profile_data,
        )

        return TeacherResponse(
            id=teacher.id,
            employee_id=teacher.employee_id,
            subjects=teacher.subjects,
            classes_assigned=teacher.classes_assigned,
            qualifications=teacher.qualifications,
            joining_date=teacher.joining_date,
            status=teacher.status.value,
            user={
                "id": teacher.user.id,
                "email": teacher.user.email,
                "profile_data": teacher.user.profile_data,
                "is_active": teacher.user.is_active,
            } if teacher.user else None,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
        )

    except DuplicateEmployeeIdError as e:
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
    "/{teacher_id}",
    response_model=TeacherResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Teacher not found"},
    },
)
async def get_teacher(
    request: Request,
    teacher_id: int,
    current_user: ActiveUserDep,
) -> TeacherResponse:
    """Get a teacher by ID.

    Args:
        request: The incoming request.
        teacher_id: The teacher ID.
        current_user: Current authenticated user.

    Returns:
        TeacherResponse with teacher data.

    Raises:
        HTTPException: If teacher not found.
    """
    service = get_teacher_service(request)

    try:
        teacher = service.get_teacher(teacher_id)

        return TeacherResponse(
            id=teacher.id,
            employee_id=teacher.employee_id,
            subjects=teacher.subjects,
            classes_assigned=teacher.classes_assigned,
            qualifications=teacher.qualifications,
            joining_date=teacher.joining_date,
            status=teacher.status.value,
            user={
                "id": teacher.user.id,
                "email": teacher.user.email,
                "profile_data": teacher.user.profile_data,
                "is_active": teacher.user.is_active,
            } if teacher.user else None,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
        )

    except TeacherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{teacher_id}",
    response_model=TeacherResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Teacher not found"},
        409: {"model": ErrorResponse, "description": "Duplicate employee ID"},
    },
)
async def update_teacher(
    request: Request,
    teacher_id: int,
    data: TeacherUpdate,
    current_user: ActiveUserDep,
) -> TeacherResponse:
    """Update a teacher.

    Args:
        request: The incoming request.
        teacher_id: The teacher ID.
        data: Teacher update data.
        current_user: Current authenticated user.

    Returns:
        TeacherResponse with updated teacher data.

    Raises:
        HTTPException: If teacher not found or employee ID exists.
    """
    # Check permission - only admins can update teachers
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update teachers",
                }
            },
        )

    service = get_teacher_service(request)

    try:
        # Convert status string to enum if provided
        status_enum = None
        if data.status:
            status_enum = TeacherStatus(data.status)

        # Convert profile_data to dict if provided
        profile_data = data.profile_data.model_dump() if data.profile_data else None

        teacher = service.update_teacher(
            teacher_id=teacher_id,
            employee_id=data.employee_id,
            subjects=data.subjects,
            classes_assigned=data.classes_assigned,
            qualifications=data.qualifications,
            status=status_enum,
            profile_data=profile_data,
        )

        return TeacherResponse(
            id=teacher.id,
            employee_id=teacher.employee_id,
            subjects=teacher.subjects,
            classes_assigned=teacher.classes_assigned,
            qualifications=teacher.qualifications,
            joining_date=teacher.joining_date,
            status=teacher.status.value,
            user={
                "id": teacher.user.id,
                "email": teacher.user.email,
                "profile_data": teacher.user.profile_data,
                "is_active": teacher.user.is_active,
            } if teacher.user else None,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
        )

    except TeacherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateEmployeeIdError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )



@router.get(
    "/{teacher_id}/classes",
    response_model=TeacherClassesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Teacher not found"},
    },
)
async def get_teacher_classes(
    request: Request,
    teacher_id: int,
    current_user: ActiveUserDep,
) -> TeacherClassesResponse:
    """Get classes assigned to a teacher.

    Returns both the classes the teacher is assigned to teach
    and the classes where the teacher is the class teacher.

    Args:
        request: The incoming request.
        teacher_id: The teacher ID.
        current_user: Current authenticated user.

    Returns:
        TeacherClassesResponse with assigned classes and class teacher classes.

    Raises:
        HTTPException: If teacher not found.
    """
    service = get_teacher_service(request)

    try:
        result = service.get_teacher_classes(teacher_id)

        return TeacherClassesResponse(
            teacher_id=result["teacher_id"],
            assigned_classes=[
                {
                    "id": cls["id"],
                    "name": cls["name"],
                    "grade_level": cls["grade_level"],
                    "academic_year": cls["academic_year"],
                    "is_class_teacher": cls.get("is_class_teacher", False),
                }
                for cls in result["assigned_classes"]
            ],
            class_teacher_of=[
                {
                    "id": cls["id"],
                    "name": cls["name"],
                    "grade_level": cls["grade_level"],
                    "academic_year": cls["academic_year"],
                    "is_class_teacher": True,
                }
                for cls in result["class_teacher_of"]
            ],
        )

    except TeacherNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
