"""Timetable schemas for request/response validation.

This module provides Pydantic schemas for timetable-related API operations
including creation, updates, and responses.
"""

from datetime import time

from pydantic import BaseModel, Field, field_validator


class TimetableCreate(BaseModel):
    """Schema for creating a new timetable entry."""

    class_id: int = Field(..., description="Class ID")
    section_id: int | None = Field(None, description="Optional section ID")
    day_of_week: int = Field(
        ..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)"
    )
    period_number: int = Field(..., ge=1, description="Period number")
    subject_id: int = Field(..., description="Subject ID")
    teacher_id: int | None = Field(None, description="Optional teacher ID")
    start_time: time = Field(..., description="Start time of the period")
    end_time: time = Field(..., description="End time of the period")

    @field_validator("end_time")
    @classmethod
    def end_time_after_start_time(cls, v: time, info) -> time:
        """Validate that end_time is after start_time."""
        start_time = info.data.get("start_time")
        if start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v


class TimetableUpdate(BaseModel):
    """Schema for updating a timetable entry."""

    section_id: int | None = Field(None, description="Optional section ID")
    day_of_week: int | None = Field(
        None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)"
    )
    period_number: int | None = Field(None, ge=1, description="Period number")
    subject_id: int | None = Field(None, description="Subject ID")
    teacher_id: int | None = Field(None, description="Optional teacher ID")
    start_time: time | None = Field(None, description="Start time of the period")
    end_time: time | None = Field(None, description="End time of the period")


class TimetableResponse(BaseModel):
    """Schema for timetable entry response."""

    id: int
    class_id: int
    class_name: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    day_of_week: int
    day_name: str
    period_number: int
    subject_id: int
    subject_name: str | None = None
    subject_code: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


class TimetableListItem(BaseModel):
    """Schema for timetable entry in list responses."""

    id: int
    class_id: int
    class_name: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    day_of_week: int
    day_name: str
    period_number: int
    subject_id: int
    subject_name: str | None = None
    subject_code: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    start_time: str
    end_time: str


class TimetableListResponse(BaseModel):
    """Schema for paginated timetable list response."""

    items: list[TimetableListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ConflictInfo(BaseModel):
    """Schema for conflict information."""

    id: int
    class_id: int | None = None
    subject_id: int | None = None
    teacher_id: int | None = None
    day_of_week: int
    period_number: int


class ConflictCheckResponse(BaseModel):
    """Schema for conflict check response."""

    has_conflicts: bool
    teacher_conflict: ConflictInfo | None = None
    class_conflict: ConflictInfo | None = None


class ClassTimetableResponse(BaseModel):
    """Schema for class timetable response."""

    class_id: int
    section_id: int | None = None
    entries: list[TimetableListItem]


class TeacherTimetableResponse(BaseModel):
    """Schema for teacher timetable response."""

    teacher_id: int
    entries: list[TimetableListItem]
