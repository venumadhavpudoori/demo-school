"""Leave request repository for data access operations.

This module provides the LeaveRequestRepository class that extends TenantAwareRepository
with leave request-specific query methods.
"""

from datetime import date
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.leave_request import LeaveRequest, LeaveStatus, RequesterType
from app.repositories.base import PaginatedResult, TenantAwareRepository


class LeaveRequestRepository(TenantAwareRepository[LeaveRequest]):
    """Repository for leave request data access operations.

    Extends TenantAwareRepository with leave request-specific methods for
    filtering by status, requester, and date ranges.
    """

    model = LeaveRequest

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the leave request repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[LeaveRequest]]:
        """Return base query with eager loading of relationships.

        Returns:
            A SQLAlchemy Select statement with relationships loaded.
        """
        return (
            select(LeaveRequest)
            .options(
                joinedload(LeaveRequest.requester),
                joinedload(LeaveRequest.approver),
            )
            .where(LeaveRequest.tenant_id == self.tenant_id)
        )

    def get_by_id_with_relations(self, id: int) -> LeaveRequest | None:
        """Get leave request by ID with relationships loaded.

        Args:
            id: The leave request ID.

        Returns:
            The leave request with relationships if found, None otherwise.
        """
        stmt = self.get_base_query().where(LeaveRequest.id == id)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()


    def list_by_status(
        self,
        status: LeaveStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[LeaveRequest]:
        """List leave requests by status.

        Args:
            status: The leave status to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the leave requests.
        """
        return self.list(
            filters={"status": status},
            page=page,
            page_size=page_size,
        )

    def list_by_requester(
        self,
        requester_id: int,
        status: LeaveStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[LeaveRequest]:
        """List leave requests by requester.

        Args:
            requester_id: The requester's user ID.
            status: Optional status filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the leave requests.
        """
        filters: dict[str, Any] = {"requester_id": requester_id}
        if status is not None:
            filters["status"] = status
        return self.list(filters=filters, page=page, page_size=page_size)

    def list_by_requester_type(
        self,
        requester_type: RequesterType,
        status: LeaveStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[LeaveRequest]:
        """List leave requests by requester type.

        Args:
            requester_type: The type of requester (teacher/student).
            status: Optional status filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the leave requests.
        """
        filters: dict[str, Any] = {"requester_type": requester_type}
        if status is not None:
            filters["status"] = status
        return self.list(filters=filters, page=page, page_size=page_size)

    def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[LeaveRequest]:
        """List pending leave requests.

        Args:
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing pending leave requests.
        """
        return self.list_by_status(LeaveStatus.PENDING, page, page_size)

    def list_by_date_range(
        self,
        start_date: date,
        end_date: date,
        status: LeaveStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[LeaveRequest]:
        """List leave requests within a date range.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
            status: Optional status filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing leave requests in the date range.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Build query - find requests that overlap with the date range
        query = self.get_base_query().where(
            LeaveRequest.from_date <= end_date,
            LeaveRequest.to_date >= start_date,
        )

        if status is not None:
            query = query.where(LeaveRequest.status == status)

        # Order by from_date
        query = query.order_by(LeaveRequest.from_date.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def has_overlapping_request(
        self,
        requester_id: int,
        from_date: date,
        to_date: date,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if there's an overlapping leave request.

        Args:
            requester_id: The requester's user ID.
            from_date: Start date of the leave.
            to_date: End date of the leave.
            exclude_id: Optional ID to exclude from check (for updates).

        Returns:
            True if there's an overlapping request, False otherwise.
        """
        query = (
            select(func.count())
            .select_from(LeaveRequest)
            .where(
                LeaveRequest.tenant_id == self.tenant_id,
                LeaveRequest.requester_id == requester_id,
                LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
                LeaveRequest.from_date <= to_date,
                LeaveRequest.to_date >= from_date,
            )
        )

        if exclude_id is not None:
            query = query.where(LeaveRequest.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0

    def count_by_status(self, status: LeaveStatus) -> int:
        """Count leave requests by status.

        Args:
            status: The leave status to count.

        Returns:
            The count of leave requests with the given status.
        """
        return self.count(filters={"status": status})

    def get_pending_count(self) -> int:
        """Get count of pending leave requests.

        Returns:
            The count of pending leave requests.
        """
        return self.count_by_status(LeaveStatus.PENDING)
