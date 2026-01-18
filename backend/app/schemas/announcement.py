"""Announcement schemas for request/response validation.

This module provides Pydantic schemas for announcement-related API operations
including creation, updates, and responses.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AuthorResponse(BaseModel):
    """Schema for author information in announcement responses."""

    id: int
    email: str
    profile_data: dict[str, Any]

    class Config:
        from_attributes = True


class AnnouncementCreate(BaseModel):
    """Schema for creating a new announcement."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Announcement title",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Announcement content",
    )
    target_audience: Literal["all", "admin", "teacher", "student", "parent"] = Field(
        default="all",
        description="Target audience for the announcement",
    )


class AnnouncementUpdate(BaseModel):
    """Schema for updating an announcement."""

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Announcement title",
    )
    content: str | None = Field(
        None,
        min_length=1,
        description="Announcement content",
    )
    target_audience: Literal["all", "admin", "teacher", "student", "parent"] | None = Field(
        None,
        description="Target audience for the announcement",
    )


class AnnouncementResponse(BaseModel):
    """Schema for announcement response."""

    id: int
    title: str
    content: str
    target_audience: str
    created_by: int | None
    author: AuthorResponse | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AnnouncementListItem(BaseModel):
    """Schema for announcement in list responses."""

    id: int
    title: str
    content: str
    target_audience: str
    created_by: int | None
    author: AuthorResponse | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    """Schema for paginated announcement list response."""

    items: list[AnnouncementListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
