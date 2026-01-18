"""Report schemas for request/response validation.

This module provides Pydantic schemas for report-related API operations
including attendance summary, grade analysis, and fee collection reports.
"""

from typing import Any

from pydantic import BaseModel, Field


# Attendance Summary Report Schemas

class AttendanceDistributionItem(BaseModel):
    """Schema for attendance distribution category."""

    count: int
    percentage: float
    criteria: str


class AttendanceDistribution(BaseModel):
    """Schema for attendance distribution breakdown."""

    excellent: AttendanceDistributionItem
    good: AttendanceDistributionItem
    average: AttendanceDistributionItem
    poor: AttendanceDistributionItem


class AttendanceSummaryStats(BaseModel):
    """Schema for attendance summary statistics."""

    total_students: int
    average_attendance_percentage: float
    total_days: int
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    half_day_count: int


class StudentAttendanceDetail(BaseModel):
    """Schema for individual student attendance details."""

    student_id: int
    student_name: str | None
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    attendance_percentage: float


class ReportFilters(BaseModel):
    """Schema for report filter parameters."""

    class_id: int | None = None
    section_id: int | None = None
    exam_id: int | None = None
    subject_id: int | None = None
    academic_year: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    fee_type: str | None = None


class AttendanceSummaryResponse(BaseModel):
    """Schema for attendance summary report response."""

    report_type: str = "attendance_summary"
    filters: ReportFilters
    summary: AttendanceSummaryStats
    attendance_distribution: AttendanceDistribution
    student_details: list[StudentAttendanceDetail]


# Grade Analysis Report Schemas

class GradeAnalysisSummary(BaseModel):
    """Schema for grade analysis summary statistics."""

    class_id: int | None = None
    class_name: str | None = None
    exam_id: int | None = None
    exam_name: str | None = None
    total_students: int = 0
    total_grades: int | None = None
    average_percentage: float
    highest_percentage: float
    lowest_percentage: float
    pass_count: int
    fail_count: int
    pass_percentage: float


class SubjectAnalytics(BaseModel):
    """Schema for subject-level analytics."""

    subject_id: int
    subject_name: str
    total_students: int
    average_marks: float
    average_percentage: float
    highest_marks: float
    lowest_marks: float
    pass_count: int
    fail_count: int
    pass_percentage: float
    grade_distribution: dict[str, int]


class StudentRanking(BaseModel):
    """Schema for student ranking in grade analysis."""

    rank: int | None = None
    student_id: int
    student_name: str | None
    total_marks: float
    total_max_marks: float | None = None
    percentage: float
    grade: str


class GradeItem(BaseModel):
    """Schema for individual grade item."""

    id: int
    student_id: int
    student_name: str | None
    subject_id: int
    subject_name: str | None
    exam_id: int
    exam_name: str | None
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str
    remarks: str | None


class GradeAnalysisResponse(BaseModel):
    """Schema for grade analysis report response."""

    report_type: str = "grade_analysis"
    filters: ReportFilters
    summary: GradeAnalysisSummary
    grade_distribution: dict[str, int]
    subject_analytics: list[SubjectAnalytics] | None = None
    student_rankings: list[StudentRanking] | None = None
    grades: list[GradeItem] | None = None


# Fee Collection Report Schemas

class FeeCollectionSummary(BaseModel):
    """Schema for fee collection summary statistics."""

    total_fees: int
    total_amount: float
    total_collected: float
    total_pending: float
    collection_percentage: float


class FeeTypeBreakdown(BaseModel):
    """Schema for fee type breakdown."""

    count: int
    total_amount: float
    collected: float
    pending: float


class DefaulterStudent(BaseModel):
    """Schema for defaulter student information."""

    student_id: int
    student_name: str | None
    total_pending: float
    fee_count: int


class DefaultersInfo(BaseModel):
    """Schema for defaulters information."""

    count: int
    total_pending_amount: float
    students: list[DefaulterStudent]


class FeeCollectionResponse(BaseModel):
    """Schema for fee collection report response."""

    report_type: str = "fee_collection"
    filters: ReportFilters
    summary: FeeCollectionSummary
    status_breakdown: dict[str, int]
    fee_type_breakdown: dict[str, FeeTypeBreakdown]
    defaulters: DefaultersInfo


# Comprehensive Report Schema

class ComprehensiveReportResponse(BaseModel):
    """Schema for comprehensive report combining all report types."""

    report_type: str = "comprehensive"
    filters: ReportFilters
    attendance: AttendanceSummaryStats
    grades: GradeAnalysisSummary
    fees: FeeCollectionSummary


# Export Schemas

class PDFSection(BaseModel):
    """Schema for PDF report section."""

    name: str
    type: str  # key_value, table
    data: dict[str, Any] | None = None
    headers: list[str] | None = None
    rows: list[list[Any]] | None = None


class PDFExportData(BaseModel):
    """Schema for PDF export data structure."""

    title: str
    generated_at: str
    filters: ReportFilters
    sections: list[PDFSection]


class ExportRequest(BaseModel):
    """Schema for export request."""

    report_type: str = Field(
        ...,
        description="Type of report to export",
        pattern="^(attendance_summary|grade_analysis|fee_collection)$",
    )
    format: str = Field(
        ...,
        description="Export format",
        pattern="^(csv|pdf)$",
    )
    class_id: int | None = Field(None, description="Class ID filter")
    section_id: int | None = Field(None, description="Section ID filter")
    exam_id: int | None = Field(None, description="Exam ID filter")
    subject_id: int | None = Field(None, description="Subject ID filter")
    academic_year: str | None = Field(None, description="Academic year filter")
    start_date: str | None = Field(None, description="Start date filter (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date filter (YYYY-MM-DD)")
    fee_type: str | None = Field(None, description="Fee type filter")
