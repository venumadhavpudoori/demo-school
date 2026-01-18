"""Announcement service for business logic operations.

This module provides the AnnouncementService class that handles all business logic
related to announcement management including CRUD operations and role-based filtering.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.announcement import Announcement, TargetAudience
from app.models.user import UserRole
from app.repositories.announcement import AnnouncementRepository


class AnnouncementServiceError(Exception):
    """Base exception for announcement service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class AnnouncementNotFoundError(AnnouncementServiceError):
    """Raised when an announcement is not found."""

    def __init__(self, announcement_id: int):
        super().__init__(
            message=f"Announcement with ID {announcement_id} not found",
            code="ANNOUNCEMENT_NOT_FOUND",
        )


class InvalidAnnouncementDataError(AnnouncementServiceError):
    """Raised when announcement data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_ANNOUNCEMENT_DATA",
        )


class AnnouncementService:
    """Service class for announcement business logic.

    Handles all business operations related to announcements including
    creation, updates, deletion, and role-based filtering.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the announcement service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = AnnouncementRepository(db, tenant_id)

    def create_announcement(
        self,
        title: str,
        content: str,
        created_by: int,
        target_audience: TargetAudience = TargetAudience.ALL,
    ) -> Announcement:
        """Create a new announcement.

        Args:
            title: The announcement title.
            content: The announcement content.
            created_by: The user ID of the author.
            target_audience: The target audience for the announcement.

        Returns:
            The created Announcement object.

        Raises:
            InvalidAnnouncementDataError: If the data is invalid.
        """
        # Validate title
        if not title or not title.strip():
            raise InvalidAnnouncementDataError("Title cannot be empty")

        # Validate content
        if not content or not content.strip():
            raise InvalidAnnouncementDataError("Content cannot be empty")

        # Create announcement
        announcement = self.repository.create({
            "title": title.strip(),
            "content": content.strip(),
            "created_by": created_by,
            "target_audience": target_audience,
        })

        return announcement

    def get_announcement(self, announcement_id: int) -> Announcement:
        """Get an announcement by ID.

        Args:
            announcement_id: The announcement ID.

        Returns:
            The Announcement object.

        Raises:
            AnnouncementNotFoundError: If announcement not found.
        """
        announcement = self.repository.get_by_id_with_author(announcement_id)
        if announcement is None:
            raise AnnouncementNotFoundError(announcement_id)
        return announcement

    def update_announcement(
        self,
        announcement_id: int,
        title: str | None = None,
        content: str | None = None,
        target_audience: TargetAudience | None = None,
    ) -> Announcement:
        """Update an announcement.

        Args:
            announcement_id: The announcement ID.
            title: Optional new title.
            content: Optional new content.
            target_audience: Optional new target audience.

        Returns:
            The updated Announcement object.

        Raises:
            AnnouncementNotFoundError: If announcement not found.
            InvalidAnnouncementDataError: If the data is invalid.
        """
        announcement = self.repository.get_by_id(announcement_id)
        if announcement is None:
            raise AnnouncementNotFoundError(announcement_id)

        # Validate and update title if provided
        if title is not None:
            if not title.strip():
                raise InvalidAnnouncementDataError("Title cannot be empty")
            announcement.title = title.strip()

        # Validate and update content if provided
        if content is not None:
            if not content.strip():
                raise InvalidAnnouncementDataError("Content cannot be empty")
            announcement.content = content.strip()

        # Update target audience if provided
        if target_audience is not None:
            announcement.target_audience = target_audience

        self.db.commit()
        self.db.refresh(announcement)

        return announcement

    def delete_announcement(self, announcement_id: int) -> bool:
        """Delete an announcement.

        Args:
            announcement_id: The announcement ID.

        Returns:
            True if deleted successfully.

        Raises:
            AnnouncementNotFoundError: If announcement not found.
        """
        announcement = self.repository.get_by_id(announcement_id)
        if announcement is None:
            raise AnnouncementNotFoundError(announcement_id)

        self.repository.hard_delete(announcement_id)
        return True

    def list_announcements(
        self,
        target_audience: TargetAudience | None = None,
        author_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List announcements with filtering and pagination.

        Args:
            target_audience: Optional target audience filter.
            author_id: Optional author ID filter.
            search: Optional search query.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        if search:
            result = self.repository.search(
                query=search,
                target_audience=target_audience,
                page=page,
                page_size=page_size,
            )
        else:
            filters: dict[str, Any] = {}
            if target_audience is not None:
                filters["target_audience"] = target_audience
            if author_id is not None:
                filters["created_by"] = author_id

            result = self.repository.list(
                filters=filters,
                page=page,
                page_size=page_size,
            )

        return self._format_paginated_result(result)

    def list_announcements_for_role(
        self,
        user_role: UserRole,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List announcements visible to a specific user role.

        Announcements are visible if target_audience is 'all' or matches the user's role.

        Args:
            user_role: The user's role.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_for_role(
            user_role=user_role,
            page=page,
            page_size=page_size,
        )

        return self._format_paginated_result(result)

    def get_recent_announcements(
        self,
        user_role: UserRole | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get recent announcements, optionally filtered by role.

        Args:
            user_role: Optional user role for filtering.
            limit: Maximum number of announcements to return.

        Returns:
            List of announcement dictionaries.
        """
        if user_role is not None:
            announcements = self.repository.get_recent_for_role(user_role, limit)
        else:
            announcements = self.repository.get_recent(limit)

        return [self._format_announcement(a) for a in announcements]

    def _format_announcement(self, announcement: Announcement) -> dict[str, Any]:
        """Format an announcement for API response.

        Args:
            announcement: The announcement object.

        Returns:
            Dictionary representation of the announcement.
        """
        return {
            "id": announcement.id,
            "title": announcement.title,
            "content": announcement.content,
            "target_audience": announcement.target_audience.value,
            "created_by": announcement.created_by,
            "author": {
                "id": announcement.author.id,
                "email": announcement.author.email,
                "profile_data": announcement.author.profile_data,
            } if announcement.author else None,
            "created_at": announcement.created_at.isoformat() if announcement.created_at else None,
            "updated_at": announcement.updated_at.isoformat() if announcement.updated_at else None,
        }

    def _format_paginated_result(self, result) -> dict[str, Any]:
        """Format a paginated result for API response.

        Args:
            result: The PaginatedResult object.

        Returns:
            Dictionary with items and pagination metadata.
        """
        return {
            "items": [self._format_announcement(a) for a in result.items],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
