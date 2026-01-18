"""Repository for AuditLog data access."""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog
from app.repositories.base import PaginatedResult, TenantAwareRepository


class AuditLogRepository(TenantAwareRepository[AuditLog]):
    """Repository for AuditLog operations.
    
    Provides methods for creating and querying audit log entries
    within a tenant scope.
    """

    model = AuditLog

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def create_log(
        self,
        user_id: int | None,
        action: AuditAction,
        entity_type: str,
        entity_id: int | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create a new audit log entry.

        Args:
            user_id: The ID of the user who performed the action.
            action: The type of action performed.
            entity_type: The type of entity affected (e.g., 'student', 'teacher').
            entity_id: The ID of the affected entity.
            old_values: The previous values before the change.
            new_values: The new values after the change.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        data = {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "additional_info": additional_info,
        }
        return self.create(data)

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[AuditLog]:
        """Get audit logs for a specific entity.

        Args:
            entity_type: The type of entity.
            entity_id: The ID of the entity.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the audit logs.
        """
        return self.list(
            filters={"entity_type": entity_type, "entity_id": entity_id},
            page=page,
            page_size=page_size,
        )

    def get_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[AuditLog]:
        """Get audit logs for a specific user.

        Args:
            user_id: The ID of the user.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the audit logs.
        """
        return self.list(
            filters={"user_id": user_id},
            page=page,
            page_size=page_size,
        )

    def get_by_action(
        self,
        action: AuditAction,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[AuditLog]:
        """Get audit logs for a specific action type.

        Args:
            action: The type of action.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the audit logs.
        """
        return self.list(
            filters={"action": action},
            page=page,
            page_size=page_size,
        )

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[AuditLog]:
        """Get audit logs within a date range.

        Args:
            start_date: The start of the date range.
            end_date: The end of the date range.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the audit logs.
        """
        # Ensure valid pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query().where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        )

        # Get total count
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        result = self.db.execute(query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def search(
        self,
        user_id: int | None = None,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[AuditLog]:
        """Search audit logs with multiple filters.

        Args:
            user_id: Filter by user ID.
            action: Filter by action type.
            entity_type: Filter by entity type.
            entity_id: Filter by entity ID.
            start_date: Filter by start date.
            end_date: Filter by end date.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the matching audit logs.
        """
        # Ensure valid pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        conditions = []
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(AuditLog.entity_id == entity_id)
        if start_date is not None:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date is not None:
            conditions.append(AuditLog.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        result = self.db.execute(query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )
