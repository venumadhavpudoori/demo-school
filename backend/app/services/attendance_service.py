"""Attendance service for business logic operations.

This module provides the AttendanceService class that handles all business logic
related to attendance management including marking, querying, and reporting.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.attendance import Attendance, AttendanceStatus
from app.repositories.attendance import AttendanceRepository


class AttendanceServiceError(Exception):
    """Base exception for attendance service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class AttendanceNotFoundError(AttendanceServiceError):
    """Raised when an attendance record is not found."""

    def __init__(self, attendance_id: int):
        super().__init__(
            message=f"Attendance record with ID {attendance_id} not found",
            code="ATTENDANCE_NOT_FOUND",
        )


class InvalidAttendanceDataError(AttendanceServiceError):
    """Raised when attendance data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_ATTENDANCE_DATA",
        )


class DuplicateAttendanceError(AttendanceServiceError):
    """Raised when attendance already exists for student on date."""

    def __init__(self, student_id: int, attendance_date: date):
        super().__init__(
            message=f"Attendance already marked for student {student_id} on {attendance_date}",
            code="DUPLICATE_ATTENDANCE",
        )


class AttendanceService:
    """Service class for attendance business logic.

    Handles all business operations related to attendance including
    marking, bulk operations, and reporting.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the attendance service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = AttendanceRepository(db, tenant_id)

    def mark_attendance(
        self,
        student_id: int,
        class_id: int,
        attendance_date: date,
        status: AttendanceStatus,
        marked_by: int | None = None,
        remarks: str | None = None,
    ) -> Attendance:
        """Mark attendance for a single student.

        Args:
            student_id: The student ID.
            class_id: The class ID.
            attendance_date: The date of attendance.
            status: The attendance status.
            marked_by: The teacher ID who marked the attendance.
            remarks: Optional remarks.

        Returns:
            The created Attendance object.

        Raises:
            DuplicateAttendanceError: If attendance already exists.
        """
        # Check for existing attendance
        existing = self.repository.get_by_student_and_date(student_id, attendance_date)
        if existing:
            raise DuplicateAttendanceError(student_id, attendance_date)

        attendance = self.repository.create({
            "student_id": student_id,
            "class_id": class_id,
            "date": attendance_date,
            "status": status,
            "marked_by": marked_by,
            "remarks": remarks,
        })

        return attendance

    def bulk_mark_attendance(
        self,
        class_id: int,
        section_id: int | None,
        attendance_date: date,
        records: list[dict[str, Any]],
        marked_by: int | None = None,
    ) -> dict[str, Any]:
        """Mark attendance for multiple students in bulk.

        This method uses upsert logic - if attendance exists for a student
        on the given date, it will be updated; otherwise, a new record is created.

        Args:
            class_id: The class ID.
            section_id: Optional section ID (for validation/filtering).
            attendance_date: The date of attendance.
            records: List of dicts with student_id, status, and optional remarks.
            marked_by: The teacher ID who marked the attendance.

        Returns:
            Dictionary with summary of the operation.

        Raises:
            InvalidAttendanceDataError: If records are empty or invalid.
        """
        if not records:
            raise InvalidAttendanceDataError("No attendance records provided")

        # Validate records
        for i, record in enumerate(records):
            if "student_id" not in record:
                raise InvalidAttendanceDataError(
                    f"Record {i}: missing student_id"
                )
            if "status" not in record:
                raise InvalidAttendanceDataError(
                    f"Record {i}: missing status"
                )

            # Convert status string to enum if needed
            if isinstance(record["status"], str):
                try:
                    record["status"] = AttendanceStatus(record["status"])
                except ValueError:
                    raise InvalidAttendanceDataError(
                        f"Record {i}: invalid status '{record['status']}'"
                    )

        # Perform bulk upsert
        attendance_records = self.repository.bulk_upsert(
            class_id=class_id,
            attendance_date=attendance_date,
            records=records,
            marked_by=marked_by,
        )

        # Count by status
        status_counts = {}
        for record in attendance_records:
            status_value = record.status.value
            status_counts[status_value] = status_counts.get(status_value, 0) + 1

        return {
            "total_marked": len(attendance_records),
            "date": attendance_date.isoformat(),
            "class_id": class_id,
            "section_id": section_id,
            "status_counts": status_counts,
            "records": [
                {
                    "id": r.id,
                    "student_id": r.student_id,
                    "status": r.status.value,
                    "remarks": r.remarks,
                }
                for r in attendance_records
            ],
        }

    def get_attendance(self, attendance_id: int) -> Attendance:
        """Get an attendance record by ID.

        Args:
            attendance_id: The attendance record ID.

        Returns:
            The Attendance object.

        Raises:
            AttendanceNotFoundError: If attendance not found.
        """
        attendance = self.repository.get_by_id_with_relations(attendance_id)
        if attendance is None:
            raise AttendanceNotFoundError(attendance_id)
        return attendance

    def update_attendance(
        self,
        attendance_id: int,
        status: AttendanceStatus | None = None,
        remarks: str | None = None,
        marked_by: int | None = None,
    ) -> Attendance:
        """Update an attendance record.

        Args:
            attendance_id: The attendance record ID.
            status: Optional new status.
            remarks: Optional new remarks.
            marked_by: Optional new marked_by teacher ID.

        Returns:
            The updated Attendance object.

        Raises:
            AttendanceNotFoundError: If attendance not found.
        """
        attendance = self.repository.get_by_id(attendance_id)
        if attendance is None:
            raise AttendanceNotFoundError(attendance_id)

        if status is not None:
            attendance.status = status
        if remarks is not None:
            attendance.remarks = remarks
        if marked_by is not None:
            attendance.marked_by = marked_by

        self.db.commit()
        self.db.refresh(attendance)

        return attendance

    def delete_attendance(self, attendance_id: int) -> bool:
        """Delete an attendance record.

        Args:
            attendance_id: The attendance record ID.

        Returns:
            True if deleted successfully.

        Raises:
            AttendanceNotFoundError: If attendance not found.
        """
        attendance = self.repository.get_by_id(attendance_id)
        if attendance is None:
            raise AttendanceNotFoundError(attendance_id)

        self.db.delete(attendance)
        self.db.commit()
        return True

    def list_attendance(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        student_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: AttendanceStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List attendance records with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            student_id: Optional student ID filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_with_filters(
            class_id=class_id,
            section_id=section_id,
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                {
                    "id": record.id,
                    "student_id": record.student_id,
                    "student_name": (
                        record.student.user.profile_data.get("first_name", "")
                        + " "
                        + record.student.user.profile_data.get("last_name", "")
                    ).strip() if record.student and record.student.user else None,
                    "class_id": record.class_id,
                    "class_name": record.class_.name if record.class_ else None,
                    "date": record.date.isoformat(),
                    "status": record.status.value,
                    "remarks": record.remarks,
                    "marked_by": record.marked_by,
                }
                for record in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def get_student_attendance_summary(
        self,
        student_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get attendance summary for a student.

        Args:
            student_id: The student ID.
            start_date: Optional start date for the summary period.
            end_date: Optional end date for the summary period.

        Returns:
            Dictionary with attendance counts and percentage.
        """
        return self.repository.get_student_attendance_summary(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_class_attendance_summary(
        self,
        class_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get attendance summary for a class.

        Args:
            class_id: The class ID.
            start_date: Optional start date for the summary period.
            end_date: Optional end date for the summary period.

        Returns:
            Dictionary with class-level attendance statistics.
        """
        return self.repository.get_class_attendance_summary(
            class_id=class_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_attendance_report(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Generate attendance report for a class or section.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            start_date: Optional start date for the report period.
            end_date: Optional end date for the report period.

        Returns:
            Dictionary with comprehensive attendance report data.
        """
        # Get class summary if class_id provided
        class_summary = None
        if class_id is not None:
            class_summary = self.repository.get_class_attendance_summary(
                class_id=class_id,
                start_date=start_date,
                end_date=end_date,
            )

        # Get all attendance records for the period
        result = self.repository.list_with_filters(
            class_id=class_id,
            section_id=section_id,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,  # Get all records for report
        )

        # Group by student for individual summaries
        student_summaries = {}
        for record in result.items:
            student_id = record.student_id
            if student_id not in student_summaries:
                student_summaries[student_id] = {
                    "student_id": student_id,
                    "student_name": (
                        record.student.user.profile_data.get("first_name", "")
                        + " "
                        + record.student.user.profile_data.get("last_name", "")
                    ).strip() if record.student and record.student.user else None,
                    "total_days": 0,
                    "present_days": 0,
                    "absent_days": 0,
                    "late_days": 0,
                    "half_days": 0,
                }

            summary = student_summaries[student_id]
            summary["total_days"] += 1

            if record.status == AttendanceStatus.PRESENT:
                summary["present_days"] += 1
            elif record.status == AttendanceStatus.ABSENT:
                summary["absent_days"] += 1
            elif record.status == AttendanceStatus.LATE:
                summary["late_days"] += 1
            elif record.status == AttendanceStatus.HALF_DAY:
                summary["half_days"] += 1

        # Calculate attendance percentage for each student
        for summary in student_summaries.values():
            if summary["total_days"] > 0:
                summary["attendance_percentage"] = round(
                    (
                        summary["present_days"]
                        + summary["late_days"] * 0.5
                        + summary["half_days"] * 0.5
                    )
                    / summary["total_days"]
                    * 100,
                    2,
                )
            else:
                summary["attendance_percentage"] = 0.0

        return {
            "class_id": class_id,
            "section_id": section_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "class_summary": class_summary,
            "student_summaries": list(student_summaries.values()),
            "total_students": len(student_summaries),
        }

    @staticmethod
    def calculate_attendance_percentage(
        present_days: int,
        late_days: int,
        half_days: int,
        total_days: int,
    ) -> float:
        """Calculate attendance percentage using the standard formula.

        Formula: (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100

        Args:
            present_days: Number of days present.
            late_days: Number of days late.
            half_days: Number of half days.
            total_days: Total number of days.

        Returns:
            Attendance percentage rounded to 2 decimal places.
        """
        if total_days <= 0:
            return 0.0

        percentage = (
            (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100
        )
        return round(percentage, 2)
