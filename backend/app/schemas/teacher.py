"""Teacher schemas for request/response validation.

This module provides Pydantic schemas for teacher-related API operations
including creation, updates, and responses.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class UserProfileData(BaseModel):
    """Schema for user profile data."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class UserResponse(BaseModel):
    """Schema for user information in teacher responses."""

    id: int
    email: str
    profile_data: dict[str, Any]
    is_active: bool = True

    class Config:
        from_attributes = True


class TeacherCreate(BaseModel):
    """Schema for creating a new teacher."""

    employee_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique employee ID",
    )
    email: EmailStr = Field(..., description="Teacher's email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Password for the teacher account",
    )
    joining_date: date = Field(..., description="Date of joining")
    subjects: list[str] | None = Field(
        None, description="List of subjects taught"
    )
    classes_assigned: list[int] | None = Field(
        None, description="List of assigned class IDs"
    )
    qualifications: str | None = Field(
        None, max_length=1000, description="Teacher's qualifications"
    )
    profile_data: UserProfileData | None = Field(
        None, description="Additional profile information"
    )


class TeacherUpdate(BaseModel):
    """Schema for updating a teacher."""

    employee_id: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Unique employee ID",
    )
    subjects: list[str] | None = Field(
        None, description="List of subjects taught"
    )
    classes_assigned: list[int] | None = Field(
        None, description="List of assigned class IDs"
    )
    qualifications: str | None = Field(
        None, max_length=1000, description="Teacher's qualifications"
    )
    status: Literal["active", "inactive", "on_leave", "resigned"] | None = Field(
        None, description="Teacher status"
    )
    profile_data: UserProfileData | None = Field(
        None, description="Additional profile information"
    )


class TeacherResponse(BaseModel):
    """Schema for teacher response."""

    id: int
    employee_id: str
    subjects: list[str] | None
    classes_assigned: list[int] | None
    qualifications: str | None
    joining_date: date
    status: str
    user: UserResponse | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TeacherListItem(BaseModel):
    """Schema for teacher in list responses."""

    id: int
    employee_id: str
    subjects: list[str] | None
    classes_assigned: list[int] | None
    qualifications: str | None
    joining_date: date
    status: str
    user: UserResponse | None

    class Config:
        from_attributes = True


class TeacherListResponse(BaseModel):
    """Schema for paginated teacher list response."""

    items: list[TeacherListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ClassInfo(BaseModel):
    """Schema for class information."""

    id: int
    name: str
    grade_level: int
    academic_year: str
    is_class_teacher: bool = False


class TeacherClassesResponse(BaseModel):
    """Schema for teacher's assigned classes response."""

    teacher_id: int
    assigned_classes: list[ClassInfo]
    class_teacher_of: list[ClassInfo]
