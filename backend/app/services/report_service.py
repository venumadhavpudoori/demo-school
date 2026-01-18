"""Report service for aggregating report data.

This module provides the ReportService class that handles all business logic
related to generating comprehensive reports across attendance, grades, and fees.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.attendance import AttendanceRepository
from app.repositories.fee import FeeRepository
from app.repositories.grade import GradeRepository
from app.repositories.exam import ExamRepository
from app.services.attendance_service import AttendanceService
from app.services.fee_service import FeeService
from app.services.grade_service import GradeService


class ReportServiceError(Exception):
    """Base exception for report service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidReportParametersError(ReportServiceError):
    """Raised when report parameters are invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_REPORT_PARAMETERS",
        )


class ReportService:
    """Service class for generating comprehensive reports.

    Aggregates data from attendance, grades, and fees services
    to generate various reports for the school ERP system.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the report service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.attendance_service = AttendanceService(db, tenant_id)
        self.grade_service = GradeService(db, tenant_id)
        self.fee_service = FeeService(db, tenant_id)
        self.attendance_repository = AttendanceRepository(db, tenant_id)
        self.grade_repository = GradeRepository(db, tenant_id)
        self.fee_repository = FeeRepository(db, tenant_id)
        self.exam_repository = ExamRepository(db, tenant_id)

    def get_attendance_summary(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        academic_year: str | None = None,
    ) -> dict[str, Any]:
        """Generate attendance summary report.

        Provides comprehensive attendance statistics including class-level
        and student-level summaries with attendance percentages.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            start_date: Optional start date for the report period.
            end_date: Optional end date for the report period.
            academic_year: Optional academic year filter.

        Returns:
            Dictionary with attendance summary data.
        """
        # Get attendance report from service
        report = self.attendance_service.get_attendance_report(
            class_id=class_id,
            section_id=section_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Calculate overall statistics
        student_summaries = report.get("student_summaries", [])
        total_students = len(student_summaries)

        if total_students > 0:
            avg_attendance = sum(
                s.get("attendance_percentage", 0) for s in student_summaries
            ) / total_students

            # Count students by attendance category
            excellent_count = sum(
                1 for s in student_summaries
                if s.get("attendance_percentage", 0) >= 90
            )
            good_count = sum(
                1 for s in student_summaries
                if 75 <= s.get("attendance_percentage", 0) < 90
            )
            average_count = sum(
                1 for s in student_summaries
                if 60 <= s.get("attendance_percentage", 0) < 75
            )
            poor_count = sum(
                1 for s in student_summaries
                if s.get("attendance_percentage", 0) < 60
            )
        else:
            avg_attendance = 0.0
            excellent_count = good_count = average_count = poor_count = 0

        # Get class summary if available
        class_summary = report.get("class_summary") or {}

        return {
            "report_type": "attendance_summary",
            "filters": {
                "class_id": class_id,
                "section_id": section_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "academic_year": academic_year,
            },
            "summary": {
                "total_students": total_students,
                "average_attendance_percentage": round(avg_attendance, 2),
                "total_days": class_summary.get("total_days", 0),
                "total_records": class_summary.get("total_records", 0),
                "present_count": class_summary.get("present_count", 0),
                "absent_count": class_summary.get("absent_count", 0),
                "late_count": class_summary.get("late_count", 0),
                "half_day_count": class_summary.get("half_day_count", 0),
            },
            "attendance_distribution": {
                "excellent": {
                    "count": excellent_count,
                    "percentage": round(excellent_count / total_students * 100, 2) if total_students > 0 else 0,
                    "criteria": ">=90%",
                },
                "good": {
                    "count": good_count,
                    "percentage": round(good_count / total_students * 100, 2) if total_students > 0 else 0,
                    "criteria": "75-89%",
                },
                "average": {
                    "count": average_count,
                    "percentage": round(average_count / total_students * 100, 2) if total_students > 0 else 0,
                    "criteria": "60-74%",
                },
                "poor": {
                    "count": poor_count,
                    "percentage": round(poor_count / total_students * 100, 2) if total_students > 0 else 0,
                    "criteria": "<60%",
                },
            },
            "student_details": student_summaries,
        }

    def get_grade_analysis(
        self,
        class_id: int | None = None,
        exam_id: int | None = None,
        subject_id: int | None = None,
        academic_year: str | None = None,
    ) -> dict[str, Any]:
        """Generate grade analysis report.

        Provides comprehensive grade statistics including class-level
        analytics, subject-wise breakdown, and student rankings.

        Args:
            class_id: Optional class ID filter.
            exam_id: Optional exam ID filter.
            subject_id: Optional subject ID filter.
            academic_year: Optional academic year filter.

        Returns:
            Dictionary with grade analysis data.
        """
        # If both class_id and exam_id provided, use grade analytics
        if class_id is not None and exam_id is not None:
            analytics = self.grade_service.get_grade_analytics(
                class_id=class_id,
                exam_id=exam_id,
            )

            class_analytics = analytics.get("class_analytics", {})
            student_rankings = analytics.get("student_rankings", [])

            return {
                "report_type": "grade_analysis",
                "filters": {
                    "class_id": class_id,
                    "exam_id": exam_id,
                    "subject_id": subject_id,
                    "academic_year": academic_year,
                },
                "summary": {
                    "class_id": class_analytics.get("class_id"),
                    "class_name": class_analytics.get("class_name"),
                    "exam_id": class_analytics.get("exam_id"),
                    "exam_name": class_analytics.get("exam_name"),
                    "total_students": class_analytics.get("total_students", 0),
                    "average_percentage": class_analytics.get("average_percentage", 0),
                    "highest_percentage": class_analytics.get("highest_percentage", 0),
                    "lowest_percentage": class_analytics.get("lowest_percentage", 0),
                    "pass_count": class_analytics.get("pass_count", 0),
                    "fail_count": class_analytics.get("fail_count", 0),
                    "pass_percentage": class_analytics.get("pass_percentage", 0),
                },
                "grade_distribution": class_analytics.get("grade_distribution", {}),
                "subject_analytics": class_analytics.get("subject_analytics", []),
                "student_rankings": student_rankings,
            }

        # Otherwise, get grades with filters and compute basic statistics
        grades_result = self.grade_service.list_grades(
            class_id=class_id,
            exam_id=exam_id,
            subject_id=subject_id,
            page=1,
            page_size=10000,  # Get all for analysis
        )

        grades = grades_result.get("items", [])
        total_grades = len(grades)

        if total_grades > 0:
            percentages = [g.get("percentage", 0) for g in grades]
            avg_percentage = sum(percentages) / total_grades
            highest = max(percentages)
            lowest = min(percentages)

            # Count by grade letter
            grade_distribution: dict[str, int] = {}
            pass_count = 0
            fail_count = 0

            for g in grades:
                grade_letter = g.get("grade", "N/A")
                grade_distribution[grade_letter] = grade_distribution.get(grade_letter, 0) + 1
                if g.get("percentage", 0) >= 33:
                    pass_count += 1
                else:
                    fail_count += 1
        else:
            avg_percentage = highest = lowest = 0.0
            grade_distribution = {}
            pass_count = fail_count = 0

        return {
            "report_type": "grade_analysis",
            "filters": {
                "class_id": class_id,
                "exam_id": exam_id,
                "subject_id": subject_id,
                "academic_year": academic_year,
            },
            "summary": {
                "total_grades": total_grades,
                "average_percentage": round(avg_percentage, 2),
                "highest_percentage": round(highest, 2),
                "lowest_percentage": round(lowest, 2),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "pass_percentage": round(pass_count / total_grades * 100, 2) if total_grades > 0 else 0,
            },
            "grade_distribution": grade_distribution,
            "grades": grades[:100],  # Limit to first 100 for response size
        }

    def get_fee_collection_report(
        self,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        fee_type: str | None = None,
    ) -> dict[str, Any]:
        """Generate fee collection report.

        Provides comprehensive fee collection statistics including
        total amounts, collection rates, and breakdowns by fee type and status.

        Args:
            academic_year: Optional academic year filter.
            start_date: Optional start date for the report period.
            end_date: Optional end date for the report period.
            fee_type: Optional fee type filter.

        Returns:
            Dictionary with fee collection report data.
        """
        # Get fee collection summary from service
        summary = self.fee_service.get_fee_collection_report(
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
        )

        # Get pending fees for additional context
        pending_result = self.fee_service.get_pending_fees(
            academic_year=academic_year,
            page=1,
            page_size=10000,
        )

        pending_fees = pending_result.get("items", [])
        total_pending_amount = pending_result.get("total_pending_amount", 0)

        # Group pending fees by student for defaulters list
        student_pending: dict[int, dict[str, Any]] = {}
        for fee in pending_fees:
            student_id = fee.get("student_id")
            if student_id not in student_pending:
                student_pending[student_id] = {
                    "student_id": student_id,
                    "student_name": fee.get("student_name"),
                    "total_pending": 0,
                    "fee_count": 0,
                }
            student_pending[student_id]["total_pending"] += fee.get("remaining", 0)
            student_pending[student_id]["fee_count"] += 1

        # Sort defaulters by pending amount
        defaulters = sorted(
            student_pending.values(),
            key=lambda x: x["total_pending"],
            reverse=True,
        )

        return {
            "report_type": "fee_collection",
            "filters": {
                "academic_year": academic_year,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "fee_type": fee_type,
            },
            "summary": {
                "total_fees": summary.get("total_fees", 0),
                "total_amount": summary.get("total_amount", 0),
                "total_collected": summary.get("total_collected", 0),
                "total_pending": summary.get("total_pending", 0),
                "collection_percentage": summary.get("collection_percentage", 0),
            },
            "status_breakdown": summary.get("status_counts", {}),
            "fee_type_breakdown": summary.get("fee_type_summary", {}),
            "defaulters": {
                "count": len(defaulters),
                "total_pending_amount": total_pending_amount,
                "students": defaulters[:50],  # Top 50 defaulters
            },
        }

    def get_comprehensive_report(
        self,
        class_id: int | None = None,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Generate a comprehensive report combining attendance, grades, and fees.

        Args:
            class_id: Optional class ID filter.
            academic_year: Optional academic year filter.
            start_date: Optional start date for the report period.
            end_date: Optional end date for the report period.

        Returns:
            Dictionary with comprehensive report data.
        """
        attendance_summary = self.get_attendance_summary(
            class_id=class_id,
            start_date=start_date,
            end_date=end_date,
            academic_year=academic_year,
        )

        grade_analysis = self.get_grade_analysis(
            class_id=class_id,
            academic_year=academic_year,
        )

        fee_collection = self.get_fee_collection_report(
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "report_type": "comprehensive",
            "filters": {
                "class_id": class_id,
                "academic_year": academic_year,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "attendance": attendance_summary.get("summary", {}),
            "grades": grade_analysis.get("summary", {}),
            "fees": fee_collection.get("summary", {}),
        }

    def export_to_csv(
        self,
        report_type: str,
        data: dict[str, Any],
    ) -> str:
        """Export report data to CSV format.

        Args:
            report_type: Type of report (attendance_summary, grade_analysis, fee_collection).
            data: Report data dictionary.

        Returns:
            CSV formatted string.
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "attendance_summary":
            # Write header
            writer.writerow([
                "Student ID", "Student Name", "Total Days", "Present Days",
                "Absent Days", "Late Days", "Half Days", "Attendance %"
            ])
            # Write data
            for student in data.get("student_details", []):
                writer.writerow([
                    student.get("student_id", ""),
                    student.get("student_name", ""),
                    student.get("total_days", 0),
                    student.get("present_days", 0),
                    student.get("absent_days", 0),
                    student.get("late_days", 0),
                    student.get("half_days", 0),
                    student.get("attendance_percentage", 0),
                ])

        elif report_type == "grade_analysis":
            # Write header
            writer.writerow([
                "Rank", "Student ID", "Student Name", "Total Marks",
                "Max Marks", "Percentage", "Grade"
            ])
            # Write data
            for student in data.get("student_rankings", []):
                writer.writerow([
                    student.get("rank", ""),
                    student.get("student_id", ""),
                    student.get("student_name", ""),
                    student.get("total_marks", 0),
                    student.get("total_max_marks", 0),
                    student.get("percentage", 0),
                    student.get("grade", ""),
                ])

        elif report_type == "fee_collection":
            # Write header
            writer.writerow([
                "Student ID", "Student Name", "Total Pending", "Fee Count"
            ])
            # Write data
            for student in data.get("defaulters", {}).get("students", []):
                writer.writerow([
                    student.get("student_id", ""),
                    student.get("student_name", ""),
                    student.get("total_pending", 0),
                    student.get("fee_count", 0),
                ])

        return output.getvalue()

    def export_to_pdf_data(
        self,
        report_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare report data for PDF generation.

        This method structures the data in a format suitable for PDF generation.
        The actual PDF generation would be handled by a PDF library like ReportLab
        or WeasyPrint.

        Args:
            report_type: Type of report.
            data: Report data dictionary.

        Returns:
            Dictionary with structured data for PDF generation.
        """
        pdf_data = {
            "title": "",
            "generated_at": date.today().isoformat(),
            "filters": data.get("filters", {}),
            "sections": [],
        }

        if report_type == "attendance_summary":
            pdf_data["title"] = "Attendance Summary Report"
            pdf_data["sections"] = [
                {
                    "name": "Summary",
                    "type": "key_value",
                    "data": data.get("summary", {}),
                },
                {
                    "name": "Attendance Distribution",
                    "type": "table",
                    "headers": ["Category", "Count", "Percentage", "Criteria"],
                    "rows": [
                        [k, v["count"], f"{v['percentage']}%", v["criteria"]]
                        for k, v in data.get("attendance_distribution", {}).items()
                    ],
                },
                {
                    "name": "Student Details",
                    "type": "table",
                    "headers": ["Student ID", "Name", "Present", "Absent", "Late", "Attendance %"],
                    "rows": [
                        [
                            s.get("student_id"),
                            s.get("student_name"),
                            s.get("present_days"),
                            s.get("absent_days"),
                            s.get("late_days"),
                            f"{s.get('attendance_percentage')}%",
                        ]
                        for s in data.get("student_details", [])
                    ],
                },
            ]

        elif report_type == "grade_analysis":
            pdf_data["title"] = "Grade Analysis Report"
            pdf_data["sections"] = [
                {
                    "name": "Summary",
                    "type": "key_value",
                    "data": data.get("summary", {}),
                },
                {
                    "name": "Grade Distribution",
                    "type": "table",
                    "headers": ["Grade", "Count"],
                    "rows": [
                        [grade, count]
                        for grade, count in data.get("grade_distribution", {}).items()
                    ],
                },
                {
                    "name": "Student Rankings",
                    "type": "table",
                    "headers": ["Rank", "Student", "Marks", "Percentage", "Grade"],
                    "rows": [
                        [
                            s.get("rank"),
                            s.get("student_name"),
                            f"{s.get('total_marks')}/{s.get('total_max_marks')}",
                            f"{s.get('percentage')}%",
                            s.get("grade"),
                        ]
                        for s in data.get("student_rankings", [])
                    ],
                },
            ]

        elif report_type == "fee_collection":
            pdf_data["title"] = "Fee Collection Report"
            pdf_data["sections"] = [
                {
                    "name": "Summary",
                    "type": "key_value",
                    "data": data.get("summary", {}),
                },
                {
                    "name": "Status Breakdown",
                    "type": "table",
                    "headers": ["Status", "Count"],
                    "rows": [
                        [status, count]
                        for status, count in data.get("status_breakdown", {}).items()
                    ],
                },
                {
                    "name": "Top Defaulters",
                    "type": "table",
                    "headers": ["Student ID", "Name", "Pending Amount", "Fee Count"],
                    "rows": [
                        [
                            s.get("student_id"),
                            s.get("student_name"),
                            f"${s.get('total_pending', 0):.2f}",
                            s.get("fee_count"),
                        ]
                        for s in data.get("defaulters", {}).get("students", [])[:20]
                    ],
                },
            ]

        return pdf_data
