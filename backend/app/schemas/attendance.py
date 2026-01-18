"""Attendance schemas for request/response validation.

This module provides Pydantic schemas for attendance-related API operations
including marking, listing, and reporting.
"""

import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttendanceMarkItem(BaseModel):
    """Schema for a single attendance mark in bulk operations."""

    student_id: int = Field(..., description="Student ID")
    status: Literal["present", "absent", "late", "half_day", "excused"] = Field(
        ..., description="Attendance status"
    )
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")


class BulkAttendanceCreate(BaseModel):
    """Schema for bulk attendance marking."""

    class_id: int = Field(..., description="Class ID")
    section_id: int | None = Field(None, description="Section ID (optional)")
    attendance_date: datetime.date = Field(..., description="Date of attendance")
    records: list[AttendanceMarkItem] = Field(
        ..., min_length=1, description="List of attendance records"
    )


class AttendanceCreate(BaseModel):
    """Schema for creating a single attendance record."""

    student_id: int = Field(..., description="Student ID")
    class_id: int = Field(..., description="Class ID")
    attendance_date: datetime.date = Field(..., description="Date of attendance")
    status: Literal["present", "absent", "late", "half_day", "excused"] = Field(
        ..., description="Attendance status"
    )
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")


class AttendanceUpdate(BaseModel):
    """Schema for updating an attendance record."""

    status: Literal["present", "absent", "late", "half_day", "excused"] | None = Field(
        None, description="Attendance status"
    )
    remarks: str | None = Field(None, max_length=500, description="Optional remarks")


class AttendanceRecordResponse(BaseModel):
    """Schema for attendance record in bulk response."""

    id: int
    student_id: int
    status: str
    remarks: str | None


class BulkAttendanceResponse(BaseModel):
    """Schema for bulk attendance marking response."""

    total_marked: int
    date: str
    class_id: int
    section_id: int | None
    status_counts: dict[str, int]
    records: list[AttendanceRecordResponse]


class AttendanceResponse(BaseModel):
    """Schema for single attendance record response."""

    id: int
    student_id: int
    student_name: str | None
    class_id: int
    class_name: str | None
    date: str
    status: str
    remarks: str | None
    marked_by: int | None

    class Config:
        from_attributes = True


class AttendanceListItem(BaseModel):
    """Schema for attendance in list responses."""

    id: int
    student_id: int
    student_name: str | None
    class_id: int
    class_name: str | None
    date: str
    status: str
    remarks: str | None
    marked_by: int | None


class AttendanceListResponse(BaseModel):
    """Schema for paginated attendance list response."""

    items: list[AttendanceListItem]
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
    excused_days: int = 0
    attendance_percentage: float


class ClassAttendanceSummary(BaseModel):
    """Schema for class-level attendance summary."""

    total_days: int
    total_students: int
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    half_day_count: int
    average_attendance_percentage: float


class StudentAttendanceSummary(BaseModel):
    """Schema for student attendance in report."""

    student_id: int
    student_name: str | None
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    attendance_percentage: float


class AttendanceReportResponse(BaseModel):
    """Schema for attendance report response."""

    class_id: int | None
    section_id: int | None
    start_date: str | None
    end_date: str | None
    class_summary: ClassAttendanceSummary | None
    student_summaries: list[StudentAttendanceSummary]
    total_students: int


class DailyAttendanceRecord(BaseModel):
    """Schema for daily attendance record in report."""

    student_id: int
    student_name: str | None
    status: str
    remarks: str | None


class DailyAttendanceReport(BaseModel):
    """Schema for daily attendance report."""

    date: str
    class_id: int
    total_marked: int
    present_count: int
    absent_count: int
    late_count: int
    half_day_count: int
    excused_count: int
    records: list[DailyAttendanceRecord]
