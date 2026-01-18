"""Exam and Grade schemas for request/response validation.

This module provides Pydantic schemas for exam and grade-related API operations
including creation, updates, and responses.
"""

from datetime import date as date_type
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ExamCreate(BaseModel):
    """Schema for creating a new exam."""

    name: str = Field(..., min_length=1, max_length=200, description="Exam name")
    exam_type: Literal[
        "unit_test", "midterm", "final", "quarterly", "half_yearly", "annual"
    ] = Field(..., description="Type of examination")
    class_id: int = Field(..., description="Class ID for the exam")
    start_date: date_type = Field(..., description="Exam start date")
    end_date: date_type = Field(..., description="Exam end date")
    academic_year: str = Field(
        ..., min_length=1, max_length=20, description="Academic year (e.g., 2024-2025)"
    )

    @field_validator("end_date")
    @classmethod
    def end_date_after_start_date(cls, v: date_type, info) -> date_type:
        """Validate that end_date is not before start_date."""
        start_date = info.data.get("start_date")
        if start_date and v < start_date:
            raise ValueError("end_date must be on or after start_date")
        return v


class ExamUpdate(BaseModel):
    """Schema for updating an exam."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Exam name")
    exam_type: Literal[
        "unit_test", "midterm", "final", "quarterly", "half_yearly", "annual"
    ] | None = Field(None, description="Type of examination")
    start_date: date_type | None = Field(None, description="Exam start date")
    end_date: date_type | None = Field(None, description="Exam end date")
    academic_year: str | None = Field(
        None, min_length=1, max_length=20, description="Academic year"
    )


class ExamResponse(BaseModel):
    """Schema for exam response."""

    id: int
    name: str
    exam_type: str
    class_id: int
    class_name: str | None = None
    start_date: date_type
    end_date: date_type
    academic_year: str

    class Config:
        from_attributes = True


class ExamListItem(BaseModel):
    """Schema for exam in list responses."""

    id: int
    name: str
    exam_type: str
    class_id: int
    class_name: str | None = None
    start_date: date_type
    end_date: date_type
    academic_year: str


class ExamListResponse(BaseModel):
    """Schema for paginated exam list response."""

    items: list[ExamListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool



# Grade Schemas

class GradeCreate(BaseModel):
    """Schema for creating a new grade entry."""

    student_id: int = Field(..., description="Student ID")
    subject_id: int = Field(..., description="Subject ID")
    exam_id: int = Field(..., description="Exam ID")
    marks_obtained: Decimal = Field(
        ..., ge=0, description="Marks obtained by the student"
    )
    max_marks: Decimal = Field(..., gt=0, description="Maximum marks for the exam")
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")

    @field_validator("marks_obtained")
    @classmethod
    def marks_not_exceed_max(cls, v: Decimal, info) -> Decimal:
        """Validate that marks_obtained does not exceed max_marks."""
        max_marks = info.data.get("max_marks")
        if max_marks and v > max_marks:
            raise ValueError("marks_obtained cannot exceed max_marks")
        return v


class GradeUpdate(BaseModel):
    """Schema for updating a grade entry."""

    marks_obtained: Decimal | None = Field(
        None, ge=0, description="Marks obtained by the student"
    )
    max_marks: Decimal | None = Field(None, gt=0, description="Maximum marks")
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")


class BulkGradeItem(BaseModel):
    """Schema for a single grade in bulk operations."""

    student_id: int = Field(..., description="Student ID")
    marks_obtained: Decimal = Field(
        ..., ge=0, description="Marks obtained by the student"
    )
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")


class BulkGradeCreate(BaseModel):
    """Schema for bulk grade entry."""

    subject_id: int = Field(..., description="Subject ID")
    exam_id: int = Field(..., description="Exam ID")
    max_marks: Decimal = Field(..., gt=0, description="Maximum marks for all entries")
    grades: list[BulkGradeItem] = Field(
        ..., min_length=1, description="List of grade entries"
    )


class GradeResponse(BaseModel):
    """Schema for grade response."""

    id: int
    student_id: int
    student_name: str | None = None
    subject_id: int
    subject_name: str | None = None
    exam_id: int
    exam_name: str | None = None
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str | None
    remarks: str | None

    class Config:
        from_attributes = True


class GradeListItem(BaseModel):
    """Schema for grade in list responses."""

    id: int
    student_id: int
    student_name: str | None = None
    subject_id: int
    subject_name: str | None = None
    exam_id: int
    exam_name: str | None = None
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str | None
    remarks: str | None


class GradeListResponse(BaseModel):
    """Schema for paginated grade list response."""

    items: list[GradeListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class BulkGradeResponse(BaseModel):
    """Schema for bulk grade entry response."""

    total_created: int
    subject_id: int
    exam_id: int
    grades: list[GradeResponse]


# Report Card Schemas

class SubjectGrade(BaseModel):
    """Schema for a subject grade in report card."""

    subject_id: int
    subject_name: str
    subject_code: str | None = None
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str | None
    remarks: str | None


class ExamResult(BaseModel):
    """Schema for exam results in report card."""

    exam_id: int
    exam_name: str
    exam_type: str
    subject_grades: list[SubjectGrade]
    total_marks_obtained: float
    total_max_marks: float
    overall_percentage: float
    overall_grade: str | None


class ReportCardResponse(BaseModel):
    """Schema for student report card."""

    student_id: int
    student_name: str
    admission_number: str
    class_id: int
    class_name: str
    section_id: int | None = None
    section_name: str | None = None
    academic_year: str
    exam_results: list[ExamResult]
    cumulative_percentage: float | None = None
    cumulative_grade: str | None = None


# Analytics Schemas

class SubjectAnalytics(BaseModel):
    """Schema for subject-level analytics."""

    subject_id: int
    subject_name: str
    average_marks: float
    average_percentage: float
    highest_marks: float
    lowest_marks: float
    pass_count: int
    fail_count: int
    pass_percentage: float
    grade_distribution: dict[str, int]


class ClassAnalytics(BaseModel):
    """Schema for class-level grade analytics."""

    class_id: int
    class_name: str
    exam_id: int
    exam_name: str
    total_students: int
    average_percentage: float
    highest_percentage: float
    lowest_percentage: float
    pass_count: int
    fail_count: int
    pass_percentage: float
    subject_analytics: list[SubjectAnalytics]
    grade_distribution: dict[str, int]


class GradeAnalyticsResponse(BaseModel):
    """Schema for grade analytics response."""

    class_analytics: ClassAnalytics | None = None
    student_rankings: list[dict] | None = None
