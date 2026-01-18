"""Base repository classes for data access layer.

This module provides the TenantAwareRepository base class that automatically
filters all queries by tenant_id for multi-tenancy support.
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.base import TenantAwareBase

T = TypeVar("T", bound=TenantAwareBase)


@dataclass
class PaginatedResult(Generic[T]):
    """Container for paginated query results."""

    items: list[T]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1


class TenantAwareRepository(Generic[T]):
    """Base repository class with automatic tenant_id filtering.

    All queries executed through this repository are automatically filtered
    by the tenant_id to ensure data isolation between tenants.

    Attributes:
        db: The database session.
        tenant_id: The current tenant's ID.
        model: The SQLAlchemy model class.
    """

    model: type[T]

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id

    def get_base_query(self) -> Select[tuple[T]]:
        """Return a query filtered by tenant_id.

        Returns:
            A SQLAlchemy Select statement filtered by tenant_id.
        """
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    def get_by_id(self, id: int) -> T | None:
        """Get entity by ID within tenant scope.

        Args:
            id: The entity ID.

        Returns:
            The entity if found within the tenant scope, None otherwise.
        """
        stmt = self.get_base_query().where(self.model.id == id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def list(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[T]:
        """List entities with filtering and pagination.

        Args:
            filters: Optional dictionary of field-value pairs to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the items and pagination metadata.
        """
        # Ensure valid pagination parameters
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Cap at 100 items per page

        # Build base query with tenant filter
        query = self.get_base_query()

        # Apply additional filters
        if filters:
            query = self._apply_filters(query, filters)

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def _apply_filters(
        self,
        query: Select[tuple[T]],
        filters: dict[str, Any],
    ) -> Select[tuple[T]]:
        """Apply filters to a query.

        Args:
            query: The base query.
            filters: Dictionary of field-value pairs to filter by.

        Returns:
            The query with filters applied.
        """
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                column = getattr(self.model, field)
                if isinstance(value, list):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)
        return query

    def create(self, data: dict[str, Any]) -> T:
        """Create entity with tenant_id.

        Args:
            data: Dictionary of field-value pairs for the new entity.

        Returns:
            The created entity.
        """
        # Ensure tenant_id is set
        data["tenant_id"] = self.tenant_id

        entity = self.model(**data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, id: int, data: dict[str, Any]) -> T | None:
        """Update entity within tenant scope.

        Args:
            id: The entity ID.
            data: Dictionary of field-value pairs to update.

        Returns:
            The updated entity if found, None otherwise.
        """
        entity = self.get_by_id(id)
        if entity is None:
            return None

        # Remove tenant_id from update data to prevent changing tenant
        data.pop("tenant_id", None)

        for field, value in data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def soft_delete(self, id: int) -> bool:
        """Soft delete entity by setting status to deleted.

        Args:
            id: The entity ID.

        Returns:
            True if the entity was deleted, False if not found.
        """
        entity = self.get_by_id(id)
        if entity is None:
            return False

        # Check if entity has a status field for soft delete
        if hasattr(entity, "status"):
            entity.status = "deleted"
            self.db.commit()
            return True

        return False

    def hard_delete(self, id: int) -> bool:
        """Permanently delete entity.

        Args:
            id: The entity ID.

        Returns:
            True if the entity was deleted, False if not found.
        """
        entity = self.get_by_id(id)
        if entity is None:
            return False

        self.db.delete(entity)
        self.db.commit()
        return True

    def exists(self, id: int) -> bool:
        """Check if entity exists within tenant scope.

        Args:
            id: The entity ID.

        Returns:
            True if the entity exists, False otherwise.
        """
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.tenant_id == self.tenant_id, self.model.id == id)
        )
        count = self.db.execute(stmt).scalar() or 0
        return count > 0

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching filters within tenant scope.

        Args:
            filters: Optional dictionary of field-value pairs to filter by.

        Returns:
            The count of matching entities.
        """
        query = self.get_base_query()

        if filters:
            query = self._apply_filters(query, filters)

        count_stmt = select(func.count()).select_from(query.subquery())
        return self.db.execute(count_stmt).scalar() or 0
