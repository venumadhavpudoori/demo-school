"""Announcement repository for data access operations.

This module provides the AnnouncementRepository class that extends TenantAwareRepository
with announcement-specific query methods.
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.announcement import Announcement, TargetAudience
from app.models.user import User, UserRole
from app.repositories.base import PaginatedResult, TenantAwareRepository


class AnnouncementRepository(TenantAwareRepository[Announcement]):
    """Repository for announcement data access operations.

    Extends TenantAwareRepository with announcement-specific methods for
    filtering by target audience and role-based access.
    """

    model = Announcement

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the announcement repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Announcement]]:
        """Return base query with eager loading of author relationship.

        Returns:
            A SQLAlchemy Select statement with author relationship loaded.
        """
        return (
            select(Announcement)
            .options(joinedload(Announcement.author))
            .where(Announcement.tenant_id == self.tenant_id)
        )

    def get_by_id_with_author(self, id: int) -> Announcement | None:
        """Get announcement by ID with author relationship loaded.

        Args:
            id: The announcement ID.

        Returns:
            The announcement with author if found, None otherwise.
        """
        stmt = self.get_base_query().where(Announcement.id == id)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def list_for_role(
        self,
        user_role: UserRole,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Announcement]:
        """List announcements visible to a specific user role.

        Announcements are visible if target_audience is 'all' or matches the user's role.

        Args:
            user_role: The user's role.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the announcements.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Map UserRole to TargetAudience
        role_to_audience = {
            UserRole.ADMIN: TargetAudience.ADMIN,
            UserRole.TEACHER: TargetAudience.TEACHER,
            UserRole.STUDENT: TargetAudience.STUDENT,
            UserRole.PARENT: TargetAudience.PARENT,
            UserRole.SUPER_ADMIN: TargetAudience.ADMIN,  # Super admin sees admin announcements
        }

        target_audience = role_to_audience.get(user_role, TargetAudience.ALL)

        # Build query - show announcements where target is 'all' or matches user's role
        query = self.get_base_query().where(
            or_(
                Announcement.target_audience == TargetAudience.ALL,
                Announcement.target_audience == target_audience,
            )
        )

        # Order by most recent first
        query = query.order_by(Announcement.created_at.desc())

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

    def list_by_target_audience(
        self,
        target_audience: TargetAudience,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Announcement]:
        """List announcements by specific target audience.

        Args:
            target_audience: The target audience to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the announcements.
        """
        return self.list(
            filters={"target_audience": target_audience},
            page=page,
            page_size=page_size,
        )

    def list_by_author(
        self,
        author_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Announcement]:
        """List announcements created by a specific author.

        Args:
            author_id: The author's user ID.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the announcements.
        """
        return self.list(
            filters={"created_by": author_id},
            page=page,
            page_size=page_size,
        )

    def search(
        self,
        query: str,
        target_audience: TargetAudience | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Announcement]:
        """Search announcements by title or content.

        Args:
            query: Search query string.
            target_audience: Optional target audience filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing matching announcements.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Build base query
        base_query = self.get_base_query()

        # Apply search filter
        search_pattern = f"%{query}%"
        base_query = base_query.where(
            or_(
                Announcement.title.ilike(search_pattern),
                Announcement.content.ilike(search_pattern),
            )
        )

        # Apply target audience filter if provided
        if target_audience is not None:
            base_query = base_query.where(
                Announcement.target_audience == target_audience
            )

        # Order by most recent first
        base_query = base_query.order_by(Announcement.created_at.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(base_query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_recent(self, limit: int = 5) -> list[Announcement]:
        """Get the most recent announcements.

        Args:
            limit: Maximum number of announcements to return.

        Returns:
            List of recent announcements.
        """
        stmt = (
            self.get_base_query()
            .order_by(Announcement.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.unique().scalars().all())

    def get_recent_for_role(
        self,
        user_role: UserRole,
        limit: int = 5,
    ) -> list[Announcement]:
        """Get the most recent announcements visible to a specific role.

        Args:
            user_role: The user's role.
            limit: Maximum number of announcements to return.

        Returns:
            List of recent announcements visible to the role.
        """
        # Map UserRole to TargetAudience
        role_to_audience = {
            UserRole.ADMIN: TargetAudience.ADMIN,
            UserRole.TEACHER: TargetAudience.TEACHER,
            UserRole.STUDENT: TargetAudience.STUDENT,
            UserRole.PARENT: TargetAudience.PARENT,
            UserRole.SUPER_ADMIN: TargetAudience.ADMIN,
        }

        target_audience = role_to_audience.get(user_role, TargetAudience.ALL)

        stmt = (
            self.get_base_query()
            .where(
                or_(
                    Announcement.target_audience == TargetAudience.ALL,
                    Announcement.target_audience == target_audience,
                )
            )
            .order_by(Announcement.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.unique().scalars().all())
