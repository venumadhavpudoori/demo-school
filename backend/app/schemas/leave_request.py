"""Leave request schemas for request/response validation.

This module provides Pydantic schemas for leave request-related API operations
including creation, updates, approval workflow, and responses.
"""

from datetime import date as date_type, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """Schema for user information in leave request responses."""

    id: int
    email: str
    profile_data: dict[str, Any]

    class Config:
        from_attributes = True


class LeaveRequestCreate(BaseModel):
    """Schema for creating a new leave request."""

    requester_type: Literal["teacher", "student"] = Field(
        ...,
        description="Type of requester",
    )
    from_date: date_type = Field(
        ...,
        description="Start date of the leave",
    )
    to_date: date_type = Field(
        ...,
        description="End date of the leave",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Reason for the leave",
    )


class LeaveRequestUpdate(BaseModel):
    """Schema for updating a leave request."""

    from_date: date_type | None = Field(
        None,
        description="Start date of the leave",
    )
    to_date: date_type | None = Field(
        None,
        description="End date of the leave",
    )
    reason: str | None = Field(
        None,
        min_length=1,
        max_length=1000,
        description="Reason for the leave",
    )


class LeaveRequestResponse(BaseModel):
    """Schema for leave request response."""

    id: int
    requester_id: int
    requester_type: str
    from_date: date_type
    to_date: date_type
    reason: str
    status: str
    approved_by: int | None
    requester: UserInfo | None
    approver: UserInfo | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class LeaveRequestListItem(BaseModel):
    """Schema for leave request in list responses."""

    id: int
    requester_id: int
    requester_type: str
    from_date: date_type
    to_date: date_type
    reason: str
    status: str
    approved_by: int | None
    requester: UserInfo | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class LeaveRequestListResponse(BaseModel):
    """Schema for paginated leave request list response."""

    items: list[LeaveRequestListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ApprovalAction(BaseModel):
    """Schema for approval/rejection action."""

    action: Literal["approve", "reject"] = Field(
        ...,
        description="Action to perform on the leave request",
    )


class PendingCountResponse(BaseModel):
    """Schema for pending count response."""

    pending_count: int
