"""Leave request service for business logic operations.

This module provides the LeaveRequestService class that handles all business logic
related to leave request management including CRUD operations and approval workflow.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.leave_request import LeaveRequest, LeaveStatus, RequesterType
from app.repositories.leave_request import LeaveRequestRepository


class LeaveRequestServiceError(Exception):
    """Base exception for leave request service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class LeaveRequestNotFoundError(LeaveRequestServiceError):
    """Raised when a leave request is not found."""

    def __init__(self, leave_request_id: int):
        super().__init__(
            message=f"Leave request with ID {leave_request_id} not found",
            code="LEAVE_REQUEST_NOT_FOUND",
        )


class InvalidLeaveRequestDataError(LeaveRequestServiceError):
    """Raised when leave request data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_LEAVE_REQUEST_DATA",
        )


class OverlappingLeaveRequestError(LeaveRequestServiceError):
    """Raised when there's an overlapping leave request."""

    def __init__(self):
        super().__init__(
            message="An overlapping leave request already exists for this period",
            code="OVERLAPPING_LEAVE_REQUEST",
        )


class InvalidStatusTransitionError(LeaveRequestServiceError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            message=f"Cannot transition from '{current_status}' to '{new_status}'",
            code="INVALID_STATUS_TRANSITION",
        )


class LeaveRequestService:
    """Service class for leave request business logic.

    Handles all business operations related to leave requests including
    creation, updates, approval workflow, and status management.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the leave request service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = LeaveRequestRepository(db, tenant_id)

    def create_leave_request(
        self,
        requester_id: int,
        requester_type: RequesterType,
        from_date: date,
        to_date: date,
        reason: str,
    ) -> LeaveRequest:
        """Create a new leave request.

        Args:
            requester_id: The user ID of the requester.
            requester_type: The type of requester (teacher/student).
            from_date: Start date of the leave.
            to_date: End date of the leave.
            reason: Reason for the leave.

        Returns:
            The created LeaveRequest object.

        Raises:
            InvalidLeaveRequestDataError: If the data is invalid.
            OverlappingLeaveRequestError: If there's an overlapping request.
        """
        # Validate dates
        if from_date > to_date:
            raise InvalidLeaveRequestDataError(
                "From date cannot be after to date"
            )

        if from_date < date.today():
            raise InvalidLeaveRequestDataError(
                "Cannot create leave request for past dates"
            )

        # Validate reason
        if not reason or not reason.strip():
            raise InvalidLeaveRequestDataError("Reason cannot be empty")

        # Check for overlapping requests
        if self.repository.has_overlapping_request(
            requester_id=requester_id,
            from_date=from_date,
            to_date=to_date,
        ):
            raise OverlappingLeaveRequestError()

        # Create leave request
        leave_request = self.repository.create({
            "requester_id": requester_id,
            "requester_type": requester_type,
            "from_date": from_date,
            "to_date": to_date,
            "reason": reason.strip(),
            "status": LeaveStatus.PENDING,
        })

        return leave_request

    def get_leave_request(self, leave_request_id: int) -> LeaveRequest:
        """Get a leave request by ID.

        Args:
            leave_request_id: The leave request ID.

        Returns:
            The LeaveRequest object.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
        """
        leave_request = self.repository.get_by_id_with_relations(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)
        return leave_request

    def update_leave_request(
        self,
        leave_request_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        reason: str | None = None,
    ) -> LeaveRequest:
        """Update a leave request.

        Only pending requests can be updated.

        Args:
            leave_request_id: The leave request ID.
            from_date: Optional new start date.
            to_date: Optional new end date.
            reason: Optional new reason.

        Returns:
            The updated LeaveRequest object.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
            InvalidLeaveRequestDataError: If the data is invalid.
            OverlappingLeaveRequestError: If there's an overlapping request.
        """
        leave_request = self.repository.get_by_id(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)

        # Only pending requests can be updated
        if leave_request.status != LeaveStatus.PENDING:
            raise InvalidLeaveRequestDataError(
                "Only pending leave requests can be updated"
            )

        # Determine final dates
        new_from_date = from_date if from_date is not None else leave_request.from_date
        new_to_date = to_date if to_date is not None else leave_request.to_date

        # Validate dates
        if new_from_date > new_to_date:
            raise InvalidLeaveRequestDataError(
                "From date cannot be after to date"
            )

        # Check for overlapping requests (excluding current)
        if from_date is not None or to_date is not None:
            if self.repository.has_overlapping_request(
                requester_id=leave_request.requester_id,
                from_date=new_from_date,
                to_date=new_to_date,
                exclude_id=leave_request_id,
            ):
                raise OverlappingLeaveRequestError()

        # Update fields
        if from_date is not None:
            leave_request.from_date = from_date
        if to_date is not None:
            leave_request.to_date = to_date
        if reason is not None:
            if not reason.strip():
                raise InvalidLeaveRequestDataError("Reason cannot be empty")
            leave_request.reason = reason.strip()

        self.db.commit()
        self.db.refresh(leave_request)

        return leave_request

    def approve_leave_request(
        self,
        leave_request_id: int,
        approved_by: int,
    ) -> LeaveRequest:
        """Approve a leave request.

        Args:
            leave_request_id: The leave request ID.
            approved_by: The user ID of the approver.

        Returns:
            The approved LeaveRequest object.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
            InvalidStatusTransitionError: If request is not pending.
        """
        leave_request = self.repository.get_by_id(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)

        if leave_request.status != LeaveStatus.PENDING:
            raise InvalidStatusTransitionError(
                leave_request.status.value, LeaveStatus.APPROVED.value
            )

        leave_request.status = LeaveStatus.APPROVED
        leave_request.approved_by = approved_by

        self.db.commit()
        self.db.refresh(leave_request)

        return leave_request

    def reject_leave_request(
        self,
        leave_request_id: int,
        rejected_by: int,
    ) -> LeaveRequest:
        """Reject a leave request.

        Args:
            leave_request_id: The leave request ID.
            rejected_by: The user ID of the rejector.

        Returns:
            The rejected LeaveRequest object.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
            InvalidStatusTransitionError: If request is not pending.
        """
        leave_request = self.repository.get_by_id(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)

        if leave_request.status != LeaveStatus.PENDING:
            raise InvalidStatusTransitionError(
                leave_request.status.value, LeaveStatus.REJECTED.value
            )

        leave_request.status = LeaveStatus.REJECTED
        leave_request.approved_by = rejected_by  # Store who rejected it

        self.db.commit()
        self.db.refresh(leave_request)

        return leave_request

    def cancel_leave_request(
        self,
        leave_request_id: int,
        requester_id: int,
    ) -> LeaveRequest:
        """Cancel a leave request.

        Only the requester can cancel their own pending or approved request.

        Args:
            leave_request_id: The leave request ID.
            requester_id: The user ID of the requester.

        Returns:
            The cancelled LeaveRequest object.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
            InvalidLeaveRequestDataError: If user is not the requester.
            InvalidStatusTransitionError: If request cannot be cancelled.
        """
        leave_request = self.repository.get_by_id(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)

        # Only the requester can cancel their own request
        if leave_request.requester_id != requester_id:
            raise InvalidLeaveRequestDataError(
                "Only the requester can cancel their own leave request"
            )

        # Can only cancel pending or approved requests
        if leave_request.status not in (LeaveStatus.PENDING, LeaveStatus.APPROVED):
            raise InvalidStatusTransitionError(
                leave_request.status.value, LeaveStatus.CANCELLED.value
            )

        leave_request.status = LeaveStatus.CANCELLED

        self.db.commit()
        self.db.refresh(leave_request)

        return leave_request

    def delete_leave_request(self, leave_request_id: int) -> bool:
        """Delete a leave request.

        Only pending requests can be deleted.

        Args:
            leave_request_id: The leave request ID.

        Returns:
            True if deleted successfully.

        Raises:
            LeaveRequestNotFoundError: If leave request not found.
            InvalidLeaveRequestDataError: If request is not pending.
        """
        leave_request = self.repository.get_by_id(leave_request_id)
        if leave_request is None:
            raise LeaveRequestNotFoundError(leave_request_id)

        # Only pending requests can be deleted
        if leave_request.status != LeaveStatus.PENDING:
            raise InvalidLeaveRequestDataError(
                "Only pending leave requests can be deleted"
            )

        self.repository.hard_delete(leave_request_id)
        return True


    def list_leave_requests(
        self,
        requester_id: int | None = None,
        requester_type: RequesterType | None = None,
        status: LeaveStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List leave requests with filtering and pagination.

        Args:
            requester_id: Optional requester ID filter.
            requester_type: Optional requester type filter.
            status: Optional status filter.
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        # If date range is provided, use date range query
        if from_date is not None and to_date is not None:
            result = self.repository.list_by_date_range(
                start_date=from_date,
                end_date=to_date,
                status=status,
                page=page,
                page_size=page_size,
            )
        elif requester_id is not None:
            result = self.repository.list_by_requester(
                requester_id=requester_id,
                status=status,
                page=page,
                page_size=page_size,
            )
        elif requester_type is not None:
            result = self.repository.list_by_requester_type(
                requester_type=requester_type,
                status=status,
                page=page,
                page_size=page_size,
            )
        elif status is not None:
            result = self.repository.list_by_status(
                status=status,
                page=page,
                page_size=page_size,
            )
        else:
            result = self.repository.list(
                page=page,
                page_size=page_size,
            )

        return self._format_paginated_result(result)

    def list_pending_requests(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List pending leave requests.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_pending(page=page, page_size=page_size)
        return self._format_paginated_result(result)

    def list_my_requests(
        self,
        requester_id: int,
        status: LeaveStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List leave requests for a specific user.

        Args:
            requester_id: The requester's user ID.
            status: Optional status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_by_requester(
            requester_id=requester_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return self._format_paginated_result(result)

    def get_pending_count(self) -> int:
        """Get count of pending leave requests.

        Returns:
            The count of pending leave requests.
        """
        return self.repository.get_pending_count()

    def _format_leave_request(self, leave_request: LeaveRequest) -> dict[str, Any]:
        """Format a leave request for API response.

        Args:
            leave_request: The leave request object.

        Returns:
            Dictionary representation of the leave request.
        """
        return {
            "id": leave_request.id,
            "requester_id": leave_request.requester_id,
            "requester_type": leave_request.requester_type.value,
            "from_date": leave_request.from_date.isoformat(),
            "to_date": leave_request.to_date.isoformat(),
            "reason": leave_request.reason,
            "status": leave_request.status.value,
            "approved_by": leave_request.approved_by,
            "requester": {
                "id": leave_request.requester.id,
                "email": leave_request.requester.email,
                "profile_data": leave_request.requester.profile_data,
            } if leave_request.requester else None,
            "approver": {
                "id": leave_request.approver.id,
                "email": leave_request.approver.email,
                "profile_data": leave_request.approver.profile_data,
            } if leave_request.approver else None,
            "created_at": leave_request.created_at.isoformat() if leave_request.created_at else None,
            "updated_at": leave_request.updated_at.isoformat() if leave_request.updated_at else None,
        }

    def _format_paginated_result(self, result) -> dict[str, Any]:
        """Format a paginated result for API response.

        Args:
            result: The PaginatedResult object.

        Returns:
            Dictionary with items and pagination metadata.
        """
        return {
            "items": [self._format_leave_request(lr) for lr in result.items],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
