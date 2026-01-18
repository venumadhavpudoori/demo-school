"""School schemas for request/response validation.

This module provides Pydantic schemas for class, section, and subject-related
API operations including creation, updates, and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Common Schemas
# ============================================================================


class TeacherInfo(BaseModel):
    """Schema for teacher information in responses."""

    id: int
    employee_id: str
    user: dict[str, Any] | None = None

    class Config:
        from_attributes = True


# ============================================================================
# Class Schemas
# ============================================================================


class ClassCreate(BaseModel):
    """Schema for creating a new class."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Class name",
    )
    grade_level: int = Field(
        ...,
        ge=1,
        le=12,
        description="Grade level (1-12)",
    )
    academic_year: str = Field(
        ...,
        min_length=4,
        max_length=20,
        description="Academic year (e.g., 2024-2025)",
    )
    class_teacher_id: int | None = Field(
        None,
        description="Class teacher ID",
    )


class ClassUpdate(BaseModel):
    """Schema for updating a class."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Class name",
    )
    grade_level: int | None = Field(
        None,
        ge=1,
        le=12,
        description="Grade level (1-12)",
    )
    academic_year: str | None = Field(
        None,
        min_length=4,
        max_length=20,
        description="Academic year",
    )
    class_teacher_id: int | None = Field(
        None,
        description="Class teacher ID",
    )


class ClassResponse(BaseModel):
    """Schema for class response."""

    id: int
    name: str
    grade_level: int
    academic_year: str
    class_teacher_id: int | None
    class_teacher: TeacherInfo | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ClassListItem(BaseModel):
    """Schema for class in list responses."""

    id: int
    name: str
    grade_level: int
    academic_year: str
    class_teacher_id: int | None
    class_teacher: TeacherInfo | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class ClassListResponse(BaseModel):
    """Schema for paginated class list response."""

    items: list[ClassListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


# ============================================================================
# Section Schemas
# ============================================================================


class SectionCreate(BaseModel):
    """Schema for creating a new section."""

    class_id: int = Field(
        ...,
        description="Class ID",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Section name (e.g., A, B, C)",
    )
    capacity: int = Field(
        40,
        ge=1,
        le=100,
        description="Section capacity",
    )


class SectionUpdate(BaseModel):
    """Schema for updating a section."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        description="Section name",
    )
    capacity: int | None = Field(
        None,
        ge=1,
        le=100,
        description="Section capacity",
    )


class SectionResponse(BaseModel):
    """Schema for section response."""

    id: int
    class_id: int
    class_name: str | None = None
    name: str
    capacity: int
    students_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SectionListItem(BaseModel):
    """Schema for section in list responses."""

    id: int
    class_id: int
    class_name: str | None = None
    name: str
    capacity: int
    students_count: int
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class SectionListResponse(BaseModel):
    """Schema for paginated section list response."""

    items: list[SectionListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SectionSummary(BaseModel):
    """Schema for section summary in class responses."""

    id: int
    name: str
    capacity: int
    students_count: int


# ============================================================================
# Subject Schemas
# ============================================================================


class SubjectCreate(BaseModel):
    """Schema for creating a new subject."""

    class_id: int = Field(
        ...,
        description="Class ID",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Subject name",
    )
    code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Subject code",
    )
    credits: int = Field(
        1,
        ge=1,
        le=10,
        description="Subject credits",
    )
    teacher_id: int | None = Field(
        None,
        description="Teacher ID",
    )


class SubjectUpdate(BaseModel):
    """Schema for updating a subject."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Subject name",
    )
    code: str | None = Field(
        None,
        min_length=1,
        max_length=20,
        description="Subject code",
    )
    credits: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Subject credits",
    )
    teacher_id: int | None = Field(
        None,
        description="Teacher ID",
    )


class SubjectResponse(BaseModel):
    """Schema for subject response."""

    id: int
    class_id: int
    class_name: str | None = None
    name: str
    code: str
    credits: int
    teacher_id: int | None
    teacher: TeacherInfo | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SubjectListItem(BaseModel):
    """Schema for subject in list responses."""

    id: int
    class_id: int
    class_name: str | None = None
    name: str
    code: str
    credits: int
    teacher_id: int | None
    teacher: TeacherInfo | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class SubjectListResponse(BaseModel):
    """Schema for paginated subject list response."""

    items: list[SubjectListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SubjectSummary(BaseModel):
    """Schema for subject summary in class responses."""

    id: int
    name: str
    code: str
    credits: int
    teacher_id: int | None
    teacher: TeacherInfo | None = None


# ============================================================================
# Enrolled Students Schema
# ============================================================================


class StudentUserInfo(BaseModel):
    """Schema for student user information."""

    id: int
    email: str
    profile_data: dict[str, Any]


class EnrolledStudentItem(BaseModel):
    """Schema for enrolled student in list responses."""

    id: int
    admission_number: str
    class_id: int | None
    section_id: int | None
    roll_number: int | None
    date_of_birth: str
    gender: str
    status: str
    user: StudentUserInfo | None = None


class EnrolledStudentsResponse(BaseModel):
    """Schema for paginated enrolled students response."""

    items: list[EnrolledStudentItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
