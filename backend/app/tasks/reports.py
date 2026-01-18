"""Background tasks for report generation.

This module provides Celery tasks for generating PDF and CSV reports
asynchronously with progress tracking and tenant context isolation.
"""

import csv
import io
import logging
import os
from datetime import date, datetime
from typing import Any

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_db_session() -> Session:
    """Create a new database session for background tasks."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_reports_directory() -> str:
    """Get the directory for storing generated reports."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


class PDFReportGenerator:
    """PDF report generator using basic HTML to PDF conversion.

    In production, this would use libraries like ReportLab, WeasyPrint,
    or wkhtmltopdf for proper PDF generation.
    """

    def __init__(self, tenant_id: int):
        """Initialize PDF generator with tenant context.

        Args:
            tenant_id: The tenant ID for context.
        """
        self.tenant_id = tenant_id

    def generate_html_report(
        self,
        title: str,
        sections: list[dict[str, Any]],
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Generate HTML content for a report.

        Args:
            title: Report title.
            sections: List of report sections with data.
            filters: Optional filter parameters used.

        Returns:
            HTML string content.
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }",
            "h2 { color: #666; margin-top: 30px; }",
            "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f4f4f4; font-weight: bold; }",
            "tr:nth-child(even) { background-color: #f9f9f9; }",
            ".summary { background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }",
            ".summary-item { margin: 5px 0; }",
            ".filters { color: #888; font-size: 0.9em; margin-bottom: 20px; }",
            ".footer { margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; color: #888; font-size: 0.8em; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
            f"<p class='filters'>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>",
        ]

        # Add filters if provided
        if filters:
            filter_items = [
                f"{k}: {v}" for k, v in filters.items() if v is not None
            ]
            if filter_items:
                html_parts.append(
                    f"<p class='filters'>Filters: {', '.join(filter_items)}</p>"
                )

        # Add sections
        for section in sections:
            section_name = section.get("name", "Section")
            section_type = section.get("type", "table")

            html_parts.append(f"<h2>{section_name}</h2>")

            if section_type == "key_value":
                # Render as summary box
                html_parts.append("<div class='summary'>")
                data = section.get("data", {})
                for key, value in data.items():
                    formatted_key = key.replace("_", " ").title()
                    html_parts.append(
                        f"<div class='summary-item'><strong>{formatted_key}:</strong> {value}</div>"
                    )
                html_parts.append("</div>")

            elif section_type == "table":
                # Render as table
                headers = section.get("headers", [])
                rows = section.get("rows", [])

                html_parts.append("<table>")
                if headers:
                    html_parts.append("<thead><tr>")
                    for header in headers:
                        html_parts.append(f"<th>{header}</th>")
                    html_parts.append("</tr></thead>")

                html_parts.append("<tbody>")
                for row in rows:
                    html_parts.append("<tr>")
                    for cell in row:
                        html_parts.append(f"<td>{cell}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</tbody></table>")

        # Footer
        html_parts.extend([
            "<div class='footer'>",
            f"<p>Report generated by School ERP System - Tenant ID: {self.tenant_id}</p>",
            "</div>",
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

    def save_report(
        self,
        content: str,
        filename: str,
        format: str = "html",
    ) -> str:
        """Save report content to file.

        Args:
            content: Report content (HTML or CSV).
            filename: Base filename without extension.
            format: Output format (html, csv).

        Returns:
            Full path to saved file.
        """
        reports_dir = get_reports_directory()
        tenant_dir = os.path.join(reports_dir, f"tenant_{self.tenant_id}")
        os.makedirs(tenant_dir, exist_ok=True)

        extension = "html" if format == "html" else "csv"
        full_filename = f"{filename}.{extension}"
        filepath = os.path.join(tenant_dir, full_filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[Tenant {self.tenant_id}] Report saved: {filepath}")
        return filepath


@celery_app.task(
    bind=True,
    name="app.tasks.reports.generate_pdf_report",
    max_retries=3,
    default_retry_delay=60,
)
def generate_pdf_report(
    self,
    tenant_id: int,
    report_type: str,
    parameters: dict,
    user_id: int,
) -> dict:
    """Generate a PDF report asynchronously.

    This task generates various types of reports (attendance, grades, fees)
    based on the specified parameters and saves them to the file system.

    Args:
        tenant_id: The tenant ID.
        report_type: Type of report (attendance_summary, grade_analysis, fee_collection).
        parameters: Report parameters (date range, filters, etc.).
        user_id: ID of user requesting the report.

    Returns:
        dict with report generation status and file path.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting PDF report generation: "
        f"type={report_type}, user={user_id}"
    )

    try:
        # Update task state to show progress
        self.update_state(
            state="PROGRESS",
            meta={"progress": 10, "status": "Initializing..."},
        )

        db = get_db_session()
        generator = PDFReportGenerator(tenant_id)

        try:
            # Import report service
            from app.services.report_service import ReportService

            report_service = ReportService(db, tenant_id)

            self.update_state(
                state="PROGRESS",
                meta={"progress": 30, "status": "Fetching data..."},
            )

            # Generate report data based on type
            report_data: dict[str, Any] = {}
            title = ""

            if report_type == "attendance_summary":
                title = "Attendance Summary Report"
                report_data = report_service.get_attendance_summary(
                    class_id=parameters.get("class_id"),
                    section_id=parameters.get("section_id"),
                    start_date=_parse_date(parameters.get("start_date")),
                    end_date=_parse_date(parameters.get("end_date")),
                    academic_year=parameters.get("academic_year"),
                )

            elif report_type == "grade_analysis":
                title = "Grade Analysis Report"
                report_data = report_service.get_grade_analysis(
                    class_id=parameters.get("class_id"),
                    exam_id=parameters.get("exam_id"),
                    subject_id=parameters.get("subject_id"),
                    academic_year=parameters.get("academic_year"),
                )

            elif report_type == "fee_collection":
                title = "Fee Collection Report"
                report_data = report_service.get_fee_collection_report(
                    academic_year=parameters.get("academic_year"),
                    start_date=_parse_date(parameters.get("start_date")),
                    end_date=_parse_date(parameters.get("end_date")),
                    fee_type=parameters.get("fee_type"),
                )

            elif report_type == "comprehensive":
                title = "Comprehensive School Report"
                report_data = report_service.get_comprehensive_report(
                    class_id=parameters.get("class_id"),
                    academic_year=parameters.get("academic_year"),
                    start_date=_parse_date(parameters.get("start_date")),
                    end_date=_parse_date(parameters.get("end_date")),
                )

            else:
                return {
                    "status": "failed",
                    "tenant_id": tenant_id,
                    "report_type": report_type,
                    "error": f"Unknown report type: {report_type}",
                }

            self.update_state(
                state="PROGRESS",
                meta={"progress": 60, "status": "Generating report..."},
            )

            # Prepare PDF data structure
            pdf_data = report_service.export_to_pdf_data(report_type, report_data)

            self.update_state(
                state="PROGRESS",
                meta={"progress": 80, "status": "Saving report..."},
            )

            # Generate HTML report
            html_content = generator.generate_html_report(
                title=pdf_data.get("title", title),
                sections=pdf_data.get("sections", []),
                filters=report_data.get("filters"),
            )

            # Save report
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}"
            filepath = generator.save_report(html_content, filename, format="html")

            self.update_state(
                state="PROGRESS",
                meta={"progress": 100, "status": "Complete"},
            )

            logger.info(
                f"[Tenant {tenant_id}] PDF report generated successfully: {filepath}"
            )

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "report_type": report_type,
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "generated_at": datetime.utcnow().isoformat(),
                "requested_by": user_id,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error generating PDF report: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "report_type": report_type,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.reports.generate_report_card",
    max_retries=3,
    default_retry_delay=60,
)
def generate_report_card(
    self,
    tenant_id: int,
    student_id: int,
    academic_year: str,
    exam_ids: list[int] | None = None,
) -> dict:
    """Generate a student report card PDF.

    This task generates a comprehensive report card for a student
    including grades, attendance, and remarks.

    Args:
        tenant_id: The tenant ID.
        student_id: The student ID.
        academic_year: Academic year for the report card.
        exam_ids: Optional list of specific exam IDs to include.

    Returns:
        dict with report card generation status.
    """
    logger.info(
        f"[Tenant {tenant_id}] Generating report card for student {student_id}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 10, "status": "Fetching student data..."},
        )

        db = get_db_session()
        generator = PDFReportGenerator(tenant_id)

        try:
            from app.models.exam import Exam, Grade
            from app.models.school import Subject
            from app.models.student import Student
            from app.models.user import User
            from app.repositories.student import StudentRepository

            # Fetch student
            student_repo = StudentRepository(db, tenant_id)
            student = student_repo.get_by_id_with_relations(student_id)

            if not student:
                return {
                    "status": "failed",
                    "tenant_id": tenant_id,
                    "student_id": student_id,
                    "error": "Student not found",
                }

            self.update_state(
                state="PROGRESS",
                meta={"progress": 30, "status": "Fetching grades..."},
            )

            # Fetch grades
            grades_query = select(Grade).where(
                Grade.tenant_id == tenant_id,
                Grade.student_id == student_id,
            )

            if exam_ids:
                grades_query = grades_query.where(Grade.exam_id.in_(exam_ids))

            grades = db.execute(grades_query).scalars().all()

            # Fetch related exams and subjects
            exam_ids_found = list(set(g.exam_id for g in grades))
            subject_ids_found = list(set(g.subject_id for g in grades))

            exams = {}
            if exam_ids_found:
                exam_results = db.execute(
                    select(Exam).where(Exam.id.in_(exam_ids_found))
                ).scalars().all()
                exams = {e.id: e for e in exam_results}

            subjects = {}
            if subject_ids_found:
                subject_results = db.execute(
                    select(Subject).where(Subject.id.in_(subject_ids_found))
                ).scalars().all()
                subjects = {s.id: s for s in subject_results}

            self.update_state(
                state="PROGRESS",
                meta={"progress": 50, "status": "Fetching attendance..."},
            )

            # Get attendance summary
            attendance_summary = student_repo.get_attendance_summary(
                student_id, academic_year
            )

            self.update_state(
                state="PROGRESS",
                meta={"progress": 70, "status": "Generating report card..."},
            )

            # Prepare report card sections
            student_name = student.user.profile_data.get(
                "first_name", ""
            ) + " " + student.user.profile_data.get("last_name", "")

            sections = [
                {
                    "name": "Student Information",
                    "type": "key_value",
                    "data": {
                        "Name": student_name.strip() or student.user.email,
                        "Admission Number": student.admission_number,
                        "Class": student.class_.name if student.class_ else "N/A",
                        "Section": student.section.name if student.section else "N/A",
                        "Roll Number": student.roll_number or "N/A",
                        "Academic Year": academic_year,
                    },
                },
                {
                    "name": "Attendance Summary",
                    "type": "key_value",
                    "data": {
                        "Total Days": attendance_summary.get("total_days", 0),
                        "Present Days": attendance_summary.get("present_days", 0),
                        "Absent Days": attendance_summary.get("absent_days", 0),
                        "Late Days": attendance_summary.get("late_days", 0),
                        "Attendance Percentage": f"{attendance_summary.get('attendance_percentage', 0)}%",
                    },
                },
            ]

            # Group grades by exam
            grades_by_exam: dict[int, list[Grade]] = {}
            for grade in grades:
                if grade.exam_id not in grades_by_exam:
                    grades_by_exam[grade.exam_id] = []
                grades_by_exam[grade.exam_id].append(grade)

            # Add grade tables for each exam
            for exam_id, exam_grades in grades_by_exam.items():
                exam = exams.get(exam_id)
                exam_name = exam.name if exam else f"Exam {exam_id}"

                rows = []
                total_marks = 0
                total_max = 0

                for grade in exam_grades:
                    subject = subjects.get(grade.subject_id)
                    subject_name = subject.name if subject else f"Subject {grade.subject_id}"
                    percentage = (
                        float(grade.marks_obtained) / float(grade.max_marks) * 100
                        if grade.max_marks > 0
                        else 0
                    )
                    rows.append([
                        subject_name,
                        f"{grade.marks_obtained}",
                        f"{grade.max_marks}",
                        f"{percentage:.1f}%",
                        grade.grade or "N/A",
                    ])
                    total_marks += float(grade.marks_obtained)
                    total_max += float(grade.max_marks)

                # Add total row
                if total_max > 0:
                    total_percentage = total_marks / total_max * 100
                    rows.append([
                        "TOTAL",
                        f"{total_marks:.1f}",
                        f"{total_max:.1f}",
                        f"{total_percentage:.1f}%",
                        _calculate_grade_letter(total_percentage),
                    ])

                sections.append({
                    "name": f"Grades - {exam_name}",
                    "type": "table",
                    "headers": ["Subject", "Marks", "Max Marks", "Percentage", "Grade"],
                    "rows": rows,
                })

            self.update_state(
                state="PROGRESS",
                meta={"progress": 90, "status": "Saving report card..."},
            )

            # Generate HTML
            html_content = generator.generate_html_report(
                title=f"Report Card - {student_name.strip() or student.admission_number}",
                sections=sections,
                filters={"Academic Year": academic_year},
            )

            # Save report
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"report_card_{student_id}_{academic_year}_{timestamp}"
            filepath = generator.save_report(html_content, filename, format="html")

            logger.info(
                f"[Tenant {tenant_id}] Report card generated: {filepath}"
            )

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "student_id": student_id,
                "academic_year": academic_year,
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "generated_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error generating report card: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "student_id": student_id,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.reports.generate_bulk_report_cards",
    max_retries=3,
    default_retry_delay=60,
)
def generate_bulk_report_cards(
    self,
    tenant_id: int,
    class_id: int,
    section_id: int | None,
    academic_year: str,
) -> dict:
    """Generate report cards for all students in a class/section.

    This task iterates through all students in the specified class/section
    and generates individual report cards for each.

    Args:
        tenant_id: The tenant ID.
        class_id: The class ID.
        section_id: Optional section ID.
        academic_year: Academic year.

    Returns:
        dict with bulk generation status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting bulk report card generation: "
        f"class={class_id}, section={section_id}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "status": "Fetching students...", "generated": 0},
        )

        db = get_db_session()

        try:
            from app.models.student import Student, StudentStatus

            # Fetch students
            query = select(Student).where(
                Student.tenant_id == tenant_id,
                Student.class_id == class_id,
                Student.status == StudentStatus.ACTIVE,
            )

            if section_id:
                query = query.where(Student.section_id == section_id)

            students = db.execute(query).scalars().all()
            total_students = len(students)

            if total_students == 0:
                return {
                    "status": "completed",
                    "tenant_id": tenant_id,
                    "class_id": class_id,
                    "section_id": section_id,
                    "total_students": 0,
                    "generated": 0,
                    "failed": 0,
                    "message": "No students found",
                }

            generated = 0
            failed = 0
            failed_students: list[int] = []

            for i, student in enumerate(students):
                try:
                    # Generate report card for each student
                    result = generate_report_card(
                        tenant_id=tenant_id,
                        student_id=student.id,
                        academic_year=academic_year,
                    )

                    if result.get("status") == "completed":
                        generated += 1
                    else:
                        failed += 1
                        failed_students.append(student.id)

                except Exception as e:
                    logger.error(
                        f"[Tenant {tenant_id}] Failed to generate report card "
                        f"for student {student.id}: {e}"
                    )
                    failed += 1
                    failed_students.append(student.id)

                # Update progress
                progress = int((i + 1) / total_students * 100)
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "status": f"Generated {generated}/{total_students}",
                        "generated": generated,
                        "failed": failed,
                    },
                )

            logger.info(
                f"[Tenant {tenant_id}] Bulk report cards completed: "
                f"{generated} generated, {failed} failed"
            )

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "class_id": class_id,
                "section_id": section_id,
                "academic_year": academic_year,
                "total_students": total_students,
                "generated": generated,
                "failed": failed,
                "failed_students": failed_students[:50],  # Limit to first 50
                "generated_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error in bulk report card generation: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.reports.export_data_csv",
    max_retries=3,
    default_retry_delay=60,
)
def export_data_csv(
    self,
    tenant_id: int,
    export_type: str,
    parameters: dict,
    user_id: int,
) -> dict:
    """Export data to CSV format.

    This task exports various data types (students, attendance, grades, fees)
    to CSV format for download or further processing.

    Args:
        tenant_id: The tenant ID.
        export_type: Type of data to export (students, attendance, grades, fees).
        parameters: Export parameters (filters, date range, etc.).
        user_id: ID of user requesting the export.

    Returns:
        dict with export status and file path.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting CSV export: type={export_type}, user={user_id}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 10, "status": "Initializing..."},
        )

        db = get_db_session()
        generator = PDFReportGenerator(tenant_id)

        try:
            from app.services.report_service import ReportService

            report_service = ReportService(db, tenant_id)

            self.update_state(
                state="PROGRESS",
                meta={"progress": 30, "status": "Fetching data..."},
            )

            # Generate CSV content based on export type
            csv_content = ""

            if export_type == "attendance_summary":
                report_data = report_service.get_attendance_summary(
                    class_id=parameters.get("class_id"),
                    section_id=parameters.get("section_id"),
                    start_date=_parse_date(parameters.get("start_date")),
                    end_date=_parse_date(parameters.get("end_date")),
                )
                csv_content = report_service.export_to_csv(export_type, report_data)

            elif export_type == "grade_analysis":
                report_data = report_service.get_grade_analysis(
                    class_id=parameters.get("class_id"),
                    exam_id=parameters.get("exam_id"),
                    subject_id=parameters.get("subject_id"),
                )
                csv_content = report_service.export_to_csv(export_type, report_data)

            elif export_type == "fee_collection":
                report_data = report_service.get_fee_collection_report(
                    academic_year=parameters.get("academic_year"),
                    start_date=_parse_date(parameters.get("start_date")),
                    end_date=_parse_date(parameters.get("end_date")),
                )
                csv_content = report_service.export_to_csv(export_type, report_data)

            else:
                return {
                    "status": "failed",
                    "tenant_id": tenant_id,
                    "export_type": export_type,
                    "error": f"Unknown export type: {export_type}",
                }

            self.update_state(
                state="PROGRESS",
                meta={"progress": 80, "status": "Saving file..."},
            )

            # Save CSV file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_type}_{timestamp}"
            filepath = generator.save_report(csv_content, filename, format="csv")

            logger.info(f"[Tenant {tenant_id}] CSV export completed: {filepath}")

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "export_type": export_type,
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "generated_at": datetime.utcnow().isoformat(),
                "requested_by": user_id,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error exporting CSV: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "export_type": export_type,
            "error": str(e),
        }


def _parse_date(date_str: str | None) -> date | None:
    """Parse date string to date object.

    Args:
        date_str: Date string in ISO format (YYYY-MM-DD).

    Returns:
        date object or None if parsing fails.
    """
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _calculate_grade_letter(percentage: float) -> str:
    """Calculate grade letter from percentage.

    Args:
        percentage: Percentage score.

    Returns:
        Grade letter (A+, A, B+, B, C+, C, D, F).
    """
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B+"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C+"
    elif percentage >= 40:
        return "C"
    elif percentage >= 33:
        return "D"
    else:
        return "F"
