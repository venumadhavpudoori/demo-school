"""Timetable API endpoints for timetable management.

This module provides REST API endpoints for timetable operations
including creation, listing, updating, and deletion with conflict detection.
"""

from datetime import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.schemas.auth import ErrorResponse
from app.schemas.timetable import (
    ClassTimetableResponse,
    ConflictCheckResponse,
    TeacherTimetableResponse,
    TimetableCreate,
    TimetableListResponse,
    TimetableResponse,
    TimetableUpdate,
)
from app.services.timetable_service import (
    InvalidTimetableDataError,
    TimetableConflictError,
    TimetableNotFoundError,
    TimetableService,
)

router = APIRouter(prefix="/api/timetable", tags=["Timetable"])


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


def get_timetable_service(request: Request) -> TimetableService:
    """Get TimetableService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    redis = getattr(request.state, "redis", None)
    return TimetableService(db, tenant_id, redis)


@router.post(
    "",
    response_model=TimetableResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        409: {"model": ErrorResponse, "description": "Timetable conflict"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_timetable_entry(
    request: Request,
    data: TimetableCreate,
    current_user: ActiveUserDep,
) -> TimetableResponse:
    """Create a new timetable entry.

    Args:
        request: The incoming request.
        data: Timetable creation data.
        current_user: Current authenticated user.

    Returns:
        TimetableResponse with created timetable entry data.

    Raises:
        HTTPException: If permission denied, conflict, or validation error.
    """
    # Check permission - only admins can create timetable entries
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create timetable entries",
                }
            },
        )

    service = get_timetable_service(request)

    try:
        timetable = service.create_timetable_entry(
            class_id=data.class_id,
            section_id=data.section_id,
            day_of_week=data.day_of_week,
            period_number=data.period_number,
            subject_id=data.subject_id,
            teacher_id=data.teacher_id,
            start_time=data.start_time,
            end_time=data.end_time,
        )

        return TimetableResponse(**service._timetable_to_dict(timetable))

    except InvalidTimetableDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except TimetableConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "conflict_type": e.conflict_type,
                }
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )


@router.get(
    "",
    response_model=TimetableListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_timetable(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    teacher_id: int | None = Query(None, description="Filter by teacher ID"),
    subject_id: int | None = Query(None, description="Filter by subject ID"),
    day_of_week: int | None = Query(
        None, ge=0, le=6, description="Filter by day of week (0=Monday, 6=Sunday)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> TimetableListResponse:
    """List timetable entries with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        section_id: Optional section ID filter.
        teacher_id: Optional teacher ID filter.
        subject_id: Optional subject ID filter.
        day_of_week: Optional day of week filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        TimetableListResponse with paginated timetable list.
    """
    service = get_timetable_service(request)

    result = service.list_timetable(
        class_id=class_id,
        section_id=section_id,
        teacher_id=teacher_id,
        subject_id=subject_id,
        day_of_week=day_of_week,
        page=page,
        page_size=page_size,
    )

    return TimetableListResponse(**result)


@router.get(
    "/class/{class_id}",
    response_model=ClassTimetableResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_class_timetable(
    request: Request,
    class_id: int,
    current_user: ActiveUserDep,
    section_id: int | None = Query(None, description="Filter by section ID"),
) -> ClassTimetableResponse:
    """Get complete timetable for a class.

    Args:
        request: The incoming request.
        class_id: The class ID.
        current_user: Current authenticated user.
        section_id: Optional section ID filter.

    Returns:
        ClassTimetableResponse with class timetable entries.
    """
    service = get_timetable_service(request)

    entries = service.get_class_timetable(class_id, section_id)

    return ClassTimetableResponse(
        class_id=class_id,
        section_id=section_id,
        entries=entries,
    )


@router.get(
    "/teacher/{teacher_id}",
    response_model=TeacherTimetableResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_teacher_timetable(
    request: Request,
    teacher_id: int,
    current_user: ActiveUserDep,
) -> TeacherTimetableResponse:
    """Get complete timetable for a teacher.

    Args:
        request: The incoming request.
        teacher_id: The teacher ID.
        current_user: Current authenticated user.

    Returns:
        TeacherTimetableResponse with teacher timetable entries.
    """
    service = get_timetable_service(request)

    entries = service.get_teacher_timetable(teacher_id)

    return TeacherTimetableResponse(
        teacher_id=teacher_id,
        entries=entries,
    )


@router.get(
    "/check-conflicts",
    response_model=ConflictCheckResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def check_conflicts(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int = Query(..., description="Class ID"),
    day_of_week: int = Query(..., ge=0, le=6, description="Day of week"),
    period_number: int = Query(..., ge=1, description="Period number"),
    start_time: time = Query(..., description="Start time"),
    end_time: time = Query(..., description="End time"),
    teacher_id: int | None = Query(None, description="Optional teacher ID"),
    section_id: int | None = Query(None, description="Optional section ID"),
    exclude_id: int | None = Query(
        None, description="Timetable ID to exclude (for updates)"
    ),
) -> ConflictCheckResponse:
    """Check for potential timetable conflicts.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: The class ID.
        day_of_week: Day of week (0=Monday, 6=Sunday).
        period_number: Period number.
        start_time: Start time of the period.
        end_time: End time of the period.
        teacher_id: Optional teacher ID.
        section_id: Optional section ID.
        exclude_id: Optional timetable ID to exclude.

    Returns:
        ConflictCheckResponse with conflict information.
    """
    service = get_timetable_service(request)

    result = service.check_conflicts(
        class_id=class_id,
        day_of_week=day_of_week,
        period_number=period_number,
        start_time=start_time,
        end_time=end_time,
        teacher_id=teacher_id,
        section_id=section_id,
        exclude_id=exclude_id,
    )

    return ConflictCheckResponse(**result)


@router.get(
    "/{timetable_id}",
    response_model=TimetableResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Timetable entry not found"},
    },
)
async def get_timetable_entry(
    request: Request,
    timetable_id: int,
    current_user: ActiveUserDep,
) -> TimetableResponse:
    """Get a timetable entry by ID.

    Args:
        request: The incoming request.
        timetable_id: The timetable entry ID.
        current_user: Current authenticated user.

    Returns:
        TimetableResponse with timetable entry data.

    Raises:
        HTTPException: If timetable entry not found.
    """
    service = get_timetable_service(request)

    try:
        timetable = service.get_timetable_entry(timetable_id)

        return TimetableResponse(**service._timetable_to_dict(timetable))

    except TimetableNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{timetable_id}",
    response_model=TimetableResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Timetable entry not found"},
        409: {"model": ErrorResponse, "description": "Timetable conflict"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_timetable_entry(
    request: Request,
    timetable_id: int,
    data: TimetableUpdate,
    current_user: ActiveUserDep,
) -> TimetableResponse:
    """Update a timetable entry.

    Args:
        request: The incoming request.
        timetable_id: The timetable entry ID.
        data: Timetable update data.
        current_user: Current authenticated user.

    Returns:
        TimetableResponse with updated timetable entry data.

    Raises:
        HTTPException: If not found, permission denied, conflict, or validation error.
    """
    # Check permission - only admins can update timetable entries
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update timetable entries",
                }
            },
        )

    service = get_timetable_service(request)

    try:
        timetable = service.update_timetable_entry(
            timetable_id=timetable_id,
            day_of_week=data.day_of_week,
            period_number=data.period_number,
            subject_id=data.subject_id,
            teacher_id=data.teacher_id,
            start_time=data.start_time,
            end_time=data.end_time,
            section_id=data.section_id,
        )

        return TimetableResponse(**service._timetable_to_dict(timetable))

    except TimetableNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidTimetableDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except TimetableConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "conflict_type": e.conflict_type,
                }
            },
        )


@router.delete(
    "/{timetable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Timetable entry not found"},
    },
)
async def delete_timetable_entry(
    request: Request,
    timetable_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a timetable entry.

    Args:
        request: The incoming request.
        timetable_id: The timetable entry ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If timetable entry not found or permission denied.
    """
    # Check permission - only admins can delete timetable entries
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete timetable entries",
                }
            },
        )

    service = get_timetable_service(request)

    try:
        service.delete_timetable_entry(timetable_id)
    except TimetableNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
