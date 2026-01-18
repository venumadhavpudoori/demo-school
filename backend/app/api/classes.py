"""Class and Section API endpoints for school management.

This module provides REST API endpoints for class and section CRUD operations
including listing, creating, updating, and deleting classes and sections.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.schemas.auth import ErrorResponse
from app.schemas.school import (
    ClassCreate,
    ClassListResponse,
    ClassResponse,
    ClassUpdate,
    EnrolledStudentsResponse,
    SectionCreate,
    SectionListResponse,
    SectionResponse,
    SectionSummary,
    SectionUpdate,
    SubjectSummary,
)
from app.services.school_service import (
    ClassNotFoundError,
    ClassService,
    DuplicateClassNameError,
    DuplicateSectionNameError,
    SectionNotFoundError,
    SectionService,
)

router = APIRouter(prefix="/api/classes", tags=["Classes"])
sections_router = APIRouter(prefix="/api/sections", tags=["Sections"])


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


def get_class_service(request: Request) -> ClassService:
    """Get ClassService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    redis = getattr(request.state, "redis", None)
    return ClassService(db, tenant_id, redis)


def get_section_service(request: Request) -> SectionService:
    """Get SectionService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return SectionService(db, tenant_id)


# ============================================================================
# Class Endpoints
# ============================================================================


@router.get(
    "",
    response_model=ClassListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_classes(
    request: Request,
    current_user: ActiveUserDep,
    academic_year: str | None = Query(None, description="Filter by academic year"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ClassListResponse:
    """List classes with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        academic_year: Optional academic year filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        ClassListResponse with paginated class list.
    """
    service = get_class_service(request)

    result = service.list_classes(
        academic_year=academic_year,
        page=page,
        page_size=page_size,
    )

    return ClassListResponse(**result)


@router.post(
    "",
    response_model=ClassResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        409: {"model": ErrorResponse, "description": "Duplicate class name"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_class(
    request: Request,
    data: ClassCreate,
    current_user: ActiveUserDep,
) -> ClassResponse:
    """Create a new class.

    Args:
        request: The incoming request.
        data: Class creation data.
        current_user: Current authenticated user.

    Returns:
        ClassResponse with created class data.

    Raises:
        HTTPException: If class name already exists or permission denied.
    """
    # Check permission - only admins can create classes
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create classes",
                }
            },
        )

    service = get_class_service(request)

    try:
        class_obj = service.create_class(
            name=data.name,
            grade_level=data.grade_level,
            academic_year=data.academic_year,
            class_teacher_id=data.class_teacher_id,
        )

        return ClassResponse(
            id=class_obj.id,
            name=class_obj.name,
            grade_level=class_obj.grade_level,
            academic_year=class_obj.academic_year,
            class_teacher_id=class_obj.class_teacher_id,
            class_teacher=None,  # Not loaded on create
            created_at=class_obj.created_at,
            updated_at=class_obj.updated_at,
        )

    except DuplicateClassNameError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "/{class_id}",
    response_model=ClassResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Class not found"},
    },
)
async def get_class(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
) -> ClassResponse:
    """Get a class by ID.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.

    Returns:
        ClassResponse with class data.

    Raises:
        HTTPException: If class not found.
    """
    try:
        service = get_class_service(request)
        class_obj = service.get_class(class_id)

        # Build class teacher data safely
        class_teacher_data = None
        if class_obj.class_teacher:
            class_teacher_data = {
                "id": class_obj.class_teacher.id,
                "employee_id": class_obj.class_teacher.employee_id,
                "user": None,
            }
            if class_obj.class_teacher.user:
                class_teacher_data["user"] = {
                    "email": class_obj.class_teacher.user.email,
                    "profile_data": class_obj.class_teacher.user.profile_data,
                }

        return ClassResponse(
            id=class_obj.id,
            name=class_obj.name,
            grade_level=class_obj.grade_level,
            academic_year=class_obj.academic_year,
            class_teacher_id=class_obj.class_teacher_id,
            class_teacher=class_teacher_data,
            created_at=class_obj.created_at,
            updated_at=class_obj.updated_at,
        )

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )


@router.put(
    "/{class_id}",
    response_model=ClassResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Class not found"},
        409: {"model": ErrorResponse, "description": "Duplicate class name"},
    },
)
async def update_class(
    request: Request,
    class_id: int,
    data: ClassUpdate,
    current_user: ActiveUserDep,
) -> ClassResponse:
    """Update a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        data: Class update data.
        current_user: Current authenticated user.

    Returns:
        ClassResponse with updated class data.

    Raises:
        HTTPException: If class not found, name exists, or permission denied.
    """
    # Check permission - only admins can update classes
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update classes",
                }
            },
        )

    service = get_class_service(request)

    try:
        class_obj = service.update_class(
            class_id=class_id,
            name=data.name,
            grade_level=data.grade_level,
            academic_year=data.academic_year,
            class_teacher_id=data.class_teacher_id,
        )

        return ClassResponse(
            id=class_obj.id,
            name=class_obj.name,
            grade_level=class_obj.grade_level,
            academic_year=class_obj.academic_year,
            class_teacher_id=class_obj.class_teacher_id,
            class_teacher=None,  # Not loaded on update
            created_at=class_obj.created_at,
            updated_at=class_obj.updated_at,
        )

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateClassNameError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{class_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Class not found"},
    },
)
async def delete_class(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If class not found or permission denied.
    """
    # Check permission - only admins can delete classes
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete classes",
                }
            },
        )

    service = get_class_service(request)

    try:
        service.delete_class(class_id)
    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


# ============================================================================
# Class Sections Endpoints
# ============================================================================


@router.get(
    "/{class_id}/sections",
    response_model=list[SectionSummary],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Class not found"},
    },
)
async def get_class_sections(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
) -> list[SectionSummary]:
    """Get all sections for a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.

    Returns:
        List of SectionSummary objects.

    Raises:
        HTTPException: If class not found.
    """
    service = get_class_service(request)

    try:
        sections = service.get_class_sections(class_id)
        return [SectionSummary(**section) for section in sections]

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/{class_id}/sections",
    response_model=SectionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Class not found"},
        409: {"model": ErrorResponse, "description": "Duplicate section name"},
    },
)
async def create_class_section(
    request: Request,
    class_id: int,
    data: SectionCreate,
    current_user: ActiveUserDep,
) -> SectionResponse:
    """Create a new section for a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        data: Section creation data.
        current_user: Current authenticated user.

    Returns:
        SectionResponse with created section data.

    Raises:
        HTTPException: If class not found, section name exists, or permission denied.
    """
    # Check permission - only admins can create sections
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create sections",
                }
            },
        )

    # Ensure class_id in path matches data
    if data.class_id != class_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "CLASS_ID_MISMATCH",
                    "message": "Class ID in path does not match class_id in request body",
                }
            },
        )

    section_service = get_section_service(request)

    try:
        section = section_service.create_section(
            class_id=class_id,
            name=data.name,
            capacity=data.capacity,
        )

        return SectionResponse(
            id=section.id,
            class_id=section.class_id,
            class_name=None,  # Not loaded on create
            name=section.name,
            capacity=section.capacity,
            students_count=section.students_count,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateSectionNameError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


# ============================================================================
# Class Subjects Endpoints
# ============================================================================


@router.get(
    "/{class_id}/subjects",
    response_model=list[SubjectSummary],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Class not found"},
    },
)
async def get_class_subjects(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
) -> list[SubjectSummary]:
    """Get all subjects for a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.

    Returns:
        List of SubjectSummary objects.

    Raises:
        HTTPException: If class not found.
    """
    service = get_class_service(request)

    try:
        subjects = service.get_class_subjects(class_id)
        return [SubjectSummary(**subject) for subject in subjects]

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


# ============================================================================
# Class Students Endpoints
# ============================================================================


@router.get(
    "/{class_id}/students",
    response_model=EnrolledStudentsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Class not found"},
    },
)
async def get_class_students(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
    section_id: int | None = Query(None, description="Filter by section ID"),
    include_inactive: bool = Query(False, description="Include inactive students"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> EnrolledStudentsResponse:
    """Get students enrolled in a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.
        section_id: Optional section ID filter.
        include_inactive: Whether to include inactive students.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        EnrolledStudentsResponse with paginated student list.

    Raises:
        HTTPException: If class not found.
    """
    service = get_class_service(request)

    try:
        result = service.get_enrolled_students(
            class_id=class_id,
            section_id=section_id,
            include_inactive=include_inactive,
            page=page,
            page_size=page_size,
        )

        return EnrolledStudentsResponse(**result)

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


# ============================================================================
# Section Endpoints (standalone router)
# ============================================================================


@sections_router.get(
    "",
    response_model=SectionListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_sections(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> SectionListResponse:
    """List sections with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        SectionListResponse with paginated section list.
    """
    service = get_section_service(request)

    result = service.list_sections(
        class_id=class_id,
        page=page,
        page_size=page_size,
    )

    return SectionListResponse(**result)


@sections_router.post(
    "",
    response_model=SectionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Class not found"},
        409: {"model": ErrorResponse, "description": "Duplicate section name"},
    },
)
async def create_section(
    request: Request,
    data: SectionCreate,
    current_user: ActiveUserDep,
) -> SectionResponse:
    """Create a new section.

    Args:
        request: The incoming request.
        data: Section creation data.
        current_user: Current authenticated user.

    Returns:
        SectionResponse with created section data.

    Raises:
        HTTPException: If class not found, section name exists, or permission denied.
    """
    # Check permission - only admins can create sections
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create sections",
                }
            },
        )

    service = get_section_service(request)

    try:
        section = service.create_section(
            class_id=data.class_id,
            name=data.name,
            capacity=data.capacity,
        )

        return SectionResponse(
            id=section.id,
            class_id=section.class_id,
            class_name=None,  # Not loaded on create
            name=section.name,
            capacity=section.capacity,
            students_count=section.students_count,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )

    except ClassNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateSectionNameError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@sections_router.get(
    "/{section_id}",
    response_model=SectionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Section not found"},
    },
)
async def get_section(
    request: Request,
    section_id: int,
    current_user: ActiveUserDep,
) -> SectionResponse:
    """Get a section by ID.

    Args:
        request: The incoming request.
        section_id: The section ID.
        current_user: Current authenticated user.

    Returns:
        SectionResponse with section data.

    Raises:
        HTTPException: If section not found.
    """
    service = get_section_service(request)

    try:
        section = service.get_section(section_id)

        return SectionResponse(
            id=section.id,
            class_id=section.class_id,
            class_name=section.class_.name if section.class_ else None,
            name=section.name,
            capacity=section.capacity,
            students_count=section.students_count,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )

    except SectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@sections_router.put(
    "/{section_id}",
    response_model=SectionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Section not found"},
        409: {"model": ErrorResponse, "description": "Duplicate section name"},
    },
)
async def update_section(
    request: Request,
    section_id: int,
    data: SectionUpdate,
    current_user: ActiveUserDep,
) -> SectionResponse:
    """Update a section.

    Args:
        request: The incoming request.
        section_id: The section ID.
        data: Section update data.
        current_user: Current authenticated user.

    Returns:
        SectionResponse with updated section data.

    Raises:
        HTTPException: If section not found, name exists, or permission denied.
    """
    # Check permission - only admins can update sections
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update sections",
                }
            },
        )

    service = get_section_service(request)

    try:
        section = service.update_section(
            section_id=section_id,
            name=data.name,
            capacity=data.capacity,
        )

        return SectionResponse(
            id=section.id,
            class_id=section.class_id,
            class_name=None,  # Not loaded on update
            name=section.name,
            capacity=section.capacity,
            students_count=section.students_count,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )

    except SectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except DuplicateSectionNameError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@sections_router.delete(
    "/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Section not found"},
    },
)
async def delete_section(
    request: Request,
    section_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a section.

    Args:
        request: The incoming request.
        section_id: The section ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If section not found or permission denied.
    """
    # Check permission - only admins can delete sections
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete sections",
                }
            },
        )

    service = get_section_service(request)

    try:
        service.delete_section(section_id)
    except SectionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
