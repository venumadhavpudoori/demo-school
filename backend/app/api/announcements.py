"""Announcement API endpoints for announcement management.

This module provides REST API endpoints for announcement CRUD operations
with role-based filtering as per Property 14.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.models.announcement import TargetAudience
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.schemas.auth import ErrorResponse
from app.services.announcement_service import (
    AnnouncementNotFoundError,
    AnnouncementService,
    InvalidAnnouncementDataError,
)

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


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


def get_announcement_service(request: Request) -> AnnouncementService:
    """Get AnnouncementService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return AnnouncementService(db, tenant_id)


@router.get(
    "",
    response_model=AnnouncementListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_announcements(
    request: Request,
    current_user: ActiveUserDep,
    target_audience: str | None = Query(None, description="Filter by target audience"),
    search: str | None = Query(None, description="Search by title or content"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AnnouncementListResponse:
    """List announcements with role-based filtering.

    Returns announcements visible to the current user based on their role.
    Announcements are visible if target_audience is 'all' or matches the user's role.

    **Property 14: Announcement Role Filtering**
    For any user requesting announcements, the returned announcements SHALL only
    include those where target_audience is 'all' OR matches the user's role.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        target_audience: Optional target audience filter (admin only).
        search: Optional search query.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        AnnouncementListResponse with paginated announcement list.
    """
    service = get_announcement_service(request)

    # Admins can filter by target_audience, others see role-filtered results
    if current_user.is_admin and target_audience:
        try:
            audience_enum = TargetAudience(target_audience)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_TARGET_AUDIENCE",
                        "message": f"Invalid target audience value: {target_audience}",
                    }
                },
            )
        result = service.list_announcements(
            target_audience=audience_enum,
            search=search,
            page=page,
            page_size=page_size,
        )
    else:
        # Role-based filtering for non-admin users or when no filter specified
        result = service.list_announcements_for_role(
            user_role=current_user.role,
            page=page,
            page_size=page_size,
        )

    return AnnouncementListResponse(**result)


@router.post(
    "",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_announcement(
    request: Request,
    data: AnnouncementCreate,
    current_user: ActiveUserDep,
) -> AnnouncementResponse:
    """Create a new announcement.

    Only admins and teachers can create announcements.

    Args:
        request: The incoming request.
        data: Announcement creation data.
        current_user: Current authenticated user.

    Returns:
        AnnouncementResponse with created announcement data.

    Raises:
        HTTPException: If permission denied or validation error.
    """
    # Check permission - only admins and teachers can create announcements
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create announcements",
                }
            },
        )

    service = get_announcement_service(request)

    try:
        target_audience = TargetAudience(data.target_audience)
        announcement = service.create_announcement(
            title=data.title,
            content=data.content,
            created_by=current_user.user_id,
            target_audience=target_audience,
        )

        return AnnouncementResponse(
            id=announcement.id,
            title=announcement.title,
            content=announcement.content,
            target_audience=announcement.target_audience.value,
            created_by=announcement.created_by,
            author={
                "id": announcement.author.id,
                "email": announcement.author.email,
                "profile_data": announcement.author.profile_data,
            } if announcement.author else None,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at,
        )

    except InvalidAnnouncementDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "/recent",
    response_model=list[AnnouncementResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_recent_announcements(
    request: Request,
    current_user: ActiveUserDep,
    limit: int = Query(5, ge=1, le=20, description="Number of announcements to return"),
) -> list[AnnouncementResponse]:
    """Get recent announcements for the current user.

    Returns the most recent announcements visible to the user based on their role.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        limit: Maximum number of announcements to return.

    Returns:
        List of recent announcements.
    """
    service = get_announcement_service(request)

    announcements = service.get_recent_announcements(
        user_role=current_user.role,
        limit=limit,
    )

    return [
        AnnouncementResponse(
            id=a["id"],
            title=a["title"],
            content=a["content"],
            target_audience=a["target_audience"],
            created_by=a["created_by"],
            author=a["author"],
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in announcements
    ]


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Announcement not found"},
    },
)
async def get_announcement(
    request: Request,
    announcement_id: int,
    current_user: ActiveUserDep,
) -> AnnouncementResponse:
    """Get an announcement by ID.

    Users can only view announcements targeted to 'all' or their role.

    Args:
        request: The incoming request.
        announcement_id: The announcement ID.
        current_user: Current authenticated user.

    Returns:
        AnnouncementResponse with announcement data.

    Raises:
        HTTPException: If announcement not found or permission denied.
    """
    service = get_announcement_service(request)

    try:
        announcement = service.get_announcement(announcement_id)

        # Check if user can view this announcement (role-based filtering)
        if not current_user.is_admin:
            role_to_audience = {
                "admin": TargetAudience.ADMIN,
                "teacher": TargetAudience.TEACHER,
                "student": TargetAudience.STUDENT,
                "parent": TargetAudience.PARENT,
                "super_admin": TargetAudience.ADMIN,
            }
            user_audience = role_to_audience.get(current_user.role.value, TargetAudience.ALL)

            if announcement.target_audience not in (TargetAudience.ALL, user_audience):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "PERMISSION_DENIED",
                            "message": "You don't have permission to view this announcement",
                        }
                    },
                )

        return AnnouncementResponse(
            id=announcement.id,
            title=announcement.title,
            content=announcement.content,
            target_audience=announcement.target_audience.value,
            created_by=announcement.created_by,
            author={
                "id": announcement.author.id,
                "email": announcement.author.email,
                "profile_data": announcement.author.profile_data,
            } if announcement.author else None,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at,
        )

    except AnnouncementNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Announcement not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_announcement(
    request: Request,
    announcement_id: int,
    data: AnnouncementUpdate,
    current_user: ActiveUserDep,
) -> AnnouncementResponse:
    """Update an announcement.

    Only admins can update announcements. Teachers can only update their own.

    Args:
        request: The incoming request.
        announcement_id: The announcement ID.
        data: Announcement update data.
        current_user: Current authenticated user.

    Returns:
        AnnouncementResponse with updated announcement data.

    Raises:
        HTTPException: If permission denied, not found, or validation error.
    """
    service = get_announcement_service(request)

    try:
        # Get the announcement first to check ownership
        announcement = service.get_announcement(announcement_id)

        # Check permission - admins can update any, teachers only their own
        if not current_user.is_admin:
            if not current_user.is_teacher or announcement.created_by != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": {
                            "code": "PERMISSION_DENIED",
                            "message": "You don't have permission to update this announcement",
                        }
                    },
                )

        target_audience = None
        if data.target_audience:
            target_audience = TargetAudience(data.target_audience)

        updated = service.update_announcement(
            announcement_id=announcement_id,
            title=data.title,
            content=data.content,
            target_audience=target_audience,
        )

        return AnnouncementResponse(
            id=updated.id,
            title=updated.title,
            content=updated.content,
            target_audience=updated.target_audience.value,
            created_by=updated.created_by,
            author={
                "id": updated.author.id,
                "email": updated.author.email,
                "profile_data": updated.author.profile_data,
            } if updated.author else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    except AnnouncementNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidAnnouncementDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Announcement not found"},
    },
)
async def delete_announcement(
    request: Request,
    announcement_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete an announcement.

    Only admins can delete announcements.

    Args:
        request: The incoming request.
        announcement_id: The announcement ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If permission denied or not found.
    """
    # Check permission - only admins can delete announcements
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete announcements",
                }
            },
        )

    service = get_announcement_service(request)

    try:
        service.delete_announcement(announcement_id)
    except AnnouncementNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
