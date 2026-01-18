"""Leave request API endpoints for leave management.

This module provides REST API endpoints for leave request CRUD operations
with approval workflow for admins.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.models.leave_request import LeaveStatus, RequesterType
from app.schemas.auth import ErrorResponse
from app.schemas.leave_request import (
    ApprovalAction,
    LeaveRequestCreate,
    LeaveRequestListResponse,
    LeaveRequestResponse,
    LeaveRequestUpdate,
    PendingCountResponse,
)
from app.services.leave_request_service import (
    InvalidLeaveRequestDataError,
    InvalidStatusTransitionError,
    LeaveRequestNotFoundError,
    LeaveRequestService,
    OverlappingLeaveRequestError,
)

router = APIRouter(prefix="/api/leave-requests", tags=["Leave Requests"])


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


def get_leave_request_service(request: Request) -> LeaveRequestService:
    """Get LeaveRequestService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return LeaveRequestService(db, tenant_id)


@router.get(
    "",
    response_model=LeaveRequestListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_leave_requests(
    request: Request,
    current_user: ActiveUserDep,
    requester_type: str | None = Query(None, description="Filter by requester type"),
    leave_status: str | None = Query(None, alias="status", description="Filter by status"),
    from_date: date | None = Query(None, description="Filter by start date"),
    to_date: date | None = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> LeaveRequestListResponse:
    """List leave requests with filtering and pagination.

    Admins can see all leave requests. Teachers and students can only see their own.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        requester_type: Optional requester type filter.
        leave_status: Optional status filter.
        from_date: Optional start date filter.
        to_date: Optional end date filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        LeaveRequestListResponse with paginated leave request list.
    """
    service = get_leave_request_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if leave_status:
        try:
            status_enum = LeaveStatus(leave_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {leave_status}",
                    }
                },
            )

    # Convert requester_type string to enum if provided
    requester_type_enum = None
    if requester_type:
        try:
            requester_type_enum = RequesterType(requester_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_REQUESTER_TYPE",
                        "message": f"Invalid requester type value: {requester_type}",
                    }
                },
            )

    # Non-admins can only see their own requests
    requester_id = None if current_user.is_admin else current_user.user_id

    result = service.list_leave_requests(
        requester_id=requester_id,
        requester_type=requester_type_enum,
        status=status_enum,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )

    return LeaveRequestListResponse(**result)


@router.post(
    "",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Overlapping leave request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_leave_request(
    request: Request,
    data: LeaveRequestCreate,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Create a new leave request.

    Teachers and students can create leave requests for themselves.

    Args:
        request: The incoming request.
        data: Leave request creation data.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with created leave request data.

    Raises:
        HTTPException: If validation error or overlapping request.
    """
    # Validate requester type matches user role
    if data.requester_type == "teacher" and not current_user.is_teacher:
        if not current_user.is_admin:  # Admins can create for anyone
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Only teachers can create teacher leave requests",
                    }
                },
            )

    if data.requester_type == "student" and not current_user.is_student:
        if not current_user.is_admin:  # Admins can create for anyone
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Only students can create student leave requests",
                    }
                },
            )

    service = get_leave_request_service(request)

    try:
        requester_type = RequesterType(data.requester_type)
        leave_request = service.create_leave_request(
            requester_id=current_user.user_id,
            requester_type=requester_type,
            from_date=data.from_date,
            to_date=data.to_date,
            reason=data.reason,
        )

        return LeaveRequestResponse(
            id=leave_request.id,
            requester_id=leave_request.requester_id,
            requester_type=leave_request.requester_type.value,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status.value,
            approved_by=leave_request.approved_by,
            requester={
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            approver=None,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )

    except InvalidLeaveRequestDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except OverlappingLeaveRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "/pending",
    response_model=LeaveRequestListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def list_pending_requests(
    request: Request,
    current_user: ActiveUserDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> LeaveRequestListResponse:
    """List pending leave requests.

    Only admins can view all pending requests.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        LeaveRequestListResponse with pending leave requests.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Only admins can view all pending requests",
                }
            },
        )

    service = get_leave_request_service(request)
    result = service.list_pending_requests(page=page, page_size=page_size)

    return LeaveRequestListResponse(**result)


@router.get(
    "/pending/count",
    response_model=PendingCountResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_pending_count(
    request: Request,
    current_user: ActiveUserDep,
) -> PendingCountResponse:
    """Get count of pending leave requests.

    Only admins can view the pending count.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.

    Returns:
        PendingCountResponse with the count.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Only admins can view pending count",
                }
            },
        )

    service = get_leave_request_service(request)
    count = service.get_pending_count()

    return PendingCountResponse(pending_count=count)


@router.get(
    "/my",
    response_model=LeaveRequestListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_my_requests(
    request: Request,
    current_user: ActiveUserDep,
    leave_status: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> LeaveRequestListResponse:
    """List current user's leave requests.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        leave_status: Optional status filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        LeaveRequestListResponse with user's leave requests.
    """
    service = get_leave_request_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if leave_status:
        try:
            status_enum = LeaveStatus(leave_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {leave_status}",
                    }
                },
            )

    result = service.list_my_requests(
        requester_id=current_user.user_id,
        status=status_enum,
        page=page,
        page_size=page_size,
    )

    return LeaveRequestListResponse(**result)


@router.get(
    "/{leave_request_id}",
    response_model=LeaveRequestResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
    },
)
async def get_leave_request(
    request: Request,
    leave_request_id: int,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Get a leave request by ID.

    Users can only view their own requests unless they are admins.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with leave request data.

    Raises:
        HTTPException: If not found or permission denied.
    """
    service = get_leave_request_service(request)

    try:
        leave_request = service.get_leave_request(leave_request_id)

        # Check permission - users can only view their own requests
        if not current_user.is_admin and leave_request.requester_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "You can only view your own leave requests",
                    }
                },
            )

        return LeaveRequestResponse(
            id=leave_request.id,
            requester_id=leave_request.requester_id,
            requester_type=leave_request.requester_type.value,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status.value,
            approved_by=leave_request.approved_by,
            requester={
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            approver={
                "id": leave_request.approver.id,
                "email": leave_request.approver.email,
                "profile_data": leave_request.approver.profile_data,
            } if leave_request.approver else None,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{leave_request_id}",
    response_model=LeaveRequestResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
        409: {"model": ErrorResponse, "description": "Overlapping leave request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_leave_request(
    request: Request,
    leave_request_id: int,
    data: LeaveRequestUpdate,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Update a leave request.

    Only the requester can update their own pending request.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        data: Leave request update data.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with updated leave request data.

    Raises:
        HTTPException: If not found, permission denied, or validation error.
    """
    service = get_leave_request_service(request)

    try:
        # Get the leave request first to check ownership
        leave_request = service.get_leave_request(leave_request_id)

        # Check permission - only the requester can update their own request
        if leave_request.requester_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "You can only update your own leave requests",
                    }
                },
            )

        updated = service.update_leave_request(
            leave_request_id=leave_request_id,
            from_date=data.from_date,
            to_date=data.to_date,
            reason=data.reason,
        )

        return LeaveRequestResponse(
            id=updated.id,
            requester_id=updated.requester_id,
            requester_type=updated.requester_type.value,
            from_date=updated.from_date,
            to_date=updated.to_date,
            reason=updated.reason,
            status=updated.status.value,
            approved_by=updated.approved_by,
            requester={
                "id": updated.requester.id,
                "email": updated.requester.email,
                "profile_data": updated.requester.profile_data,
            } if updated.requester else None,
            approver={
                "id": updated.approver.id,
                "email": updated.approver.email,
                "profile_data": updated.approver.profile_data,
            } if updated.approver else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidLeaveRequestDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except OverlappingLeaveRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/{leave_request_id}/approve",
    response_model=LeaveRequestResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
        422: {"model": ErrorResponse, "description": "Invalid status transition"},
    },
)
async def approve_leave_request(
    request: Request,
    leave_request_id: int,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Approve a leave request.

    Only admins can approve leave requests.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with approved leave request data.

    Raises:
        HTTPException: If not found, permission denied, or invalid transition.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Only admins can approve leave requests",
                }
            },
        )

    service = get_leave_request_service(request)

    try:
        leave_request = service.approve_leave_request(
            leave_request_id=leave_request_id,
            approved_by=current_user.user_id,
        )

        return LeaveRequestResponse(
            id=leave_request.id,
            requester_id=leave_request.requester_id,
            requester_type=leave_request.requester_type.value,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status.value,
            approved_by=leave_request.approved_by,
            requester={
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            approver={
                "id": leave_request.approver.id,
                "email": leave_request.approver.email,
                "profile_data": leave_request.approver.profile_data,
            } if leave_request.approver else None,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/{leave_request_id}/reject",
    response_model=LeaveRequestResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
        422: {"model": ErrorResponse, "description": "Invalid status transition"},
    },
)
async def reject_leave_request(
    request: Request,
    leave_request_id: int,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Reject a leave request.

    Only admins can reject leave requests.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with rejected leave request data.

    Raises:
        HTTPException: If not found, permission denied, or invalid transition.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Only admins can reject leave requests",
                }
            },
        )

    service = get_leave_request_service(request)

    try:
        leave_request = service.reject_leave_request(
            leave_request_id=leave_request_id,
            rejected_by=current_user.user_id,
        )

        return LeaveRequestResponse(
            id=leave_request.id,
            requester_id=leave_request.requester_id,
            requester_type=leave_request.requester_type.value,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status.value,
            approved_by=leave_request.approved_by,
            requester={
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            approver={
                "id": leave_request.approver.id,
                "email": leave_request.approver.email,
                "profile_data": leave_request.approver.profile_data,
            } if leave_request.approver else None,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/{leave_request_id}/cancel",
    response_model=LeaveRequestResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
        422: {"model": ErrorResponse, "description": "Invalid status transition"},
    },
)
async def cancel_leave_request(
    request: Request,
    leave_request_id: int,
    current_user: ActiveUserDep,
) -> LeaveRequestResponse:
    """Cancel a leave request.

    Only the requester can cancel their own pending or approved request.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        current_user: Current authenticated user.

    Returns:
        LeaveRequestResponse with cancelled leave request data.

    Raises:
        HTTPException: If not found, permission denied, or invalid transition.
    """
    service = get_leave_request_service(request)

    try:
        leave_request = service.cancel_leave_request(
            leave_request_id=leave_request_id,
            requester_id=current_user.user_id,
        )

        return LeaveRequestResponse(
            id=leave_request.id,
            requester_id=leave_request.requester_id,
            requester_type=leave_request.requester_type.value,
            from_date=leave_request.from_date,
            to_date=leave_request.to_date,
            reason=leave_request.reason,
            status=leave_request.status.value,
            approved_by=leave_request.approved_by,
            requester={
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            approver={
                "id": leave_request.approver.id,
                "email": leave_request.approver.email,
                "profile_data": leave_request.approver.profile_data,
            } if leave_request.approver else None,
            created_at=leave_request.created_at,
            updated_at=leave_request.updated_at,
        )

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidLeaveRequestDataError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{leave_request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Leave request not found"},
        422: {"model": ErrorResponse, "description": "Cannot delete non-pending request"},
    },
)
async def delete_leave_request(
    request: Request,
    leave_request_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a leave request.

    Only the requester can delete their own pending request.
    Admins can delete any pending request.

    Args:
        request: The incoming request.
        leave_request_id: The leave request ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If not found, permission denied, or not pending.
    """
    service = get_leave_request_service(request)

    try:
        # Get the leave request first to check ownership
        leave_request = service.get_leave_request(leave_request_id)

        # Check permission - only the requester or admin can delete
        if not current_user.is_admin and leave_request.requester_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "You can only delete your own leave requests",
                    }
                },
            )

        service.delete_leave_request(leave_request_id)

    except LeaveRequestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidLeaveRequestDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )
