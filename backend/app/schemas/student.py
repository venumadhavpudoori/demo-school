"""Student schemas for request/response validation.

This module provides Pydantic schemas for student-related API operations
including creation, updates, and responses.
"""

from datetime import date as date_type, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class UserProfileData(BaseModel):
    """Schema for user profile data."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class UserResponse(BaseModel):
    """Schema for user information in student responses."""

    id: int
    email: str
    profile_data: dict[str, Any]
    is_active: bool = True

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    """Schema for creating a new student."""

    admission_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique admission number",
    )
    email: EmailStr = Field(..., description="Student's email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Password for the student account",
    )
    date_of_birth: date_type = Field(..., description="Student's date of birth")
    gender: Literal["male", "female", "other"] = Field(
        ..., description="Student's gender"
    )
    admission_date: date_type = Field(..., description="Date of admission")
    class_id: int | None = Field(None, description="Class ID")
    section_id: int | None = Field(None, description="Section ID")
    roll_number: int | None = Field(None, ge=1, description="Roll number in class")
    address: str | None = Field(None, max_length=500, description="Student's address")
    parent_ids: list[int] | None = Field(
        None, description="List of parent user IDs"
    )
    profile_data: UserProfileData | None = Field(
        None, description="Additional profile information"
    )


class StudentUpdate(BaseModel):
    """Schema for updating a student."""

    admission_number: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Unique admission number",
    )
    class_id: int | None = Field(None, description="Class ID")
    section_id: int | None = Field(None, description="Section ID")
    roll_number: int | None = Field(None, ge=1, description="Roll number in class")
    address: str | None = Field(None, max_length=500, description="Student's address")
    parent_ids: list[int] | None = Field(
        None, description="List of parent user IDs"
    )
    status: Literal["active", "inactive", "graduated", "transferred", "deleted"] | None = Field(
        None, description="Student status"
    )
    profile_data: UserProfileData | None = Field(
        None, description="Additional profile information"
    )


class StudentResponse(BaseModel):
    """Schema for student response."""

    id: int
    admission_number: str
    class_id: int | None
    section_id: int | None
    roll_number: int | None
    date_of_birth: date_type
    gender: str
    address: str | None
    admission_date: date_type
    status: str
    user: UserResponse | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class StudentListItem(BaseModel):
    """Schema for student in list responses."""

    id: int
    admission_number: str
    class_id: int | None
    section_id: int | None
    roll_number: int | None
    date_of_birth: date_type
    gender: str
    status: str
    user: UserResponse | None

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """Schema for paginated student list response."""

    items: list[StudentListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class AttendanceSummary(BaseModel):
    """Schema for attendance summary."""

    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    attendance_percentage: float


class GradeItem(BaseModel):
    """Schema for a grade item."""

    id: int
    subject_name: str | None
    exam_name: str | None
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str | None
    remarks: str | None


class FeeItem(BaseModel):
    """Schema for a fee item."""

    id: int
    fee_type: str
    amount: float
    paid_amount: float
    due_date: date_type
    status: str


class FeesSummary(BaseModel):
    """Schema for fees summary."""

    total_amount: float
    total_paid: float
    balance: float
    pending_count: int
    recent_fees: list[FeeItem]


class StudentInfo(BaseModel):
    """Schema for student info in profile."""

    id: int
    admission_number: str
    class_id: int | None
    class_name: str | None
    section_id: int | None
    section_name: str | None
    roll_number: int | None
    date_of_birth: date_type
    gender: str
    address: str | None
    admission_date: date_type
    status: str
    user: UserResponse


class StudentProfileResponse(BaseModel):
    """Schema for complete student profile with aggregated data."""

    student: StudentInfo
    attendance: AttendanceSummary
    grades: list[GradeItem]
    fees: FeesSummary
