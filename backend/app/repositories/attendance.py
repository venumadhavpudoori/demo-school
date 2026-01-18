"""Attendance repository for data access operations.

This module provides the AttendanceRepository class that handles all database
operations related to attendance records with automatic tenant filtering.
"""

from datetime import date
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance, AttendanceStatus
from app.repositories.base import PaginatedResult, TenantAwareRepository


class AttendanceRepository(TenantAwareRepository[Attendance]):
    """Repository for attendance data access operations.

    Extends TenantAwareRepository to provide attendance-specific
    query methods with automatic tenant filtering.
    """

    model = Attendance

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the attendance repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_by_id_with_relations(self, attendance_id: int) -> Attendance | None:
        """Get attendance record by ID with related entities loaded.

        Args:
            attendance_id: The attendance record ID.

        Returns:
            The Attendance object with relations or None if not found.
        """
        stmt = (
            self.get_base_query()
            .where(Attendance.id == attendance_id)
            .options(
                joinedload(Attendance.student),
                joinedload(Attendance.class_),
                joinedload(Attendance.marked_by_user),
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_student_and_date(
        self, student_id: int, attendance_date: date
    ) -> Attendance | None:
        """Get attendance record for a specific student and date.

        Args:
            student_id: The student ID.
            attendance_date: The date of attendance.

        Returns:
            The Attendance object or None if not found.
        """
        stmt = self.get_base_query().where(
            and_(
                Attendance.student_id == student_id,
                Attendance.date == attendance_date,
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_class_and_date(
        self, class_id: int, attendance_date: date
    ) -> list[Attendance]:
        """Get all attendance records for a class on a specific date.

        Args:
            class_id: The class ID.
            attendance_date: The date of attendance.

        Returns:
            List of Attendance objects.
        """
        stmt = (
            self.get_base_query()
            .where(
                and_(
                    Attendance.class_id == class_id,
                    Attendance.date == attendance_date,
                )
            )
            .options(joinedload(Attendance.student))
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def list_with_filters(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        student_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: AttendanceStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Attendance]:
        """List attendance records with advanced filtering.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter (via student).
            student_id: Optional student ID filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional attendance status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing attendance records.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        if class_id is not None:
            query = query.where(Attendance.class_id == class_id)
        if student_id is not None:
            query = query.where(Attendance.student_id == student_id)
        if start_date is not None:
            query = query.where(Attendance.date >= start_date)
        if end_date is not None:
            query = query.where(Attendance.date <= end_date)
        if status is not None:
            query = query.where(Attendance.status == status)

        # Handle section_id filter through student relationship
        if section_id is not None:
            from app.models.student import Student
            query = query.join(Student, Attendance.student_id == Student.id).where(
                Student.section_id == section_id
            )

        # Order by date descending
        query = query.order_by(Attendance.date.desc(), Attendance.id.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Attendance.student),
            joinedload(Attendance.class_),
        )

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def bulk_create(self, records: list[dict[str, Any]]) -> list[Attendance]:
        """Create multiple attendance records in bulk.

        Args:
            records: List of dictionaries with attendance data.

        Returns:
            List of created Attendance objects.
        """
        attendance_records = []
        for record in records:
            record["tenant_id"] = self.tenant_id
            attendance = Attendance(**record)
            self.db.add(attendance)
            attendance_records.append(attendance)

        self.db.commit()
        for record in attendance_records:
            self.db.refresh(record)

        return attendance_records

    def bulk_upsert(
        self,
        class_id: int,
        attendance_date: date,
        records: list[dict[str, Any]],
        marked_by: int | None = None,
    ) -> list[Attendance]:
        """Create or update attendance records for a class on a date.

        If a record exists for a student on the given date, it will be updated.
        Otherwise, a new record will be created.

        Args:
            class_id: The class ID.
            attendance_date: The date of attendance.
            records: List of dicts with student_id, status, and optional remarks.
            marked_by: The teacher ID who marked the attendance.

        Returns:
            List of created/updated Attendance objects.
        """
        result_records = []

        for record in records:
            student_id = record["student_id"]
            status = record["status"]
            remarks = record.get("remarks")

            # Check if record exists
            existing = self.get_by_student_and_date(student_id, attendance_date)

            if existing:
                # Update existing record
                existing.status = status
                existing.remarks = remarks
                if marked_by is not None:
                    existing.marked_by = marked_by
                result_records.append(existing)
            else:
                # Create new record
                attendance = Attendance(
                    tenant_id=self.tenant_id,
                    student_id=student_id,
                    class_id=class_id,
                    date=attendance_date,
                    status=status,
                    marked_by=marked_by,
                    remarks=remarks,
                )
                self.db.add(attendance)
                result_records.append(attendance)

        self.db.commit()
        for record in result_records:
            self.db.refresh(record)

        return result_records

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
        query = self.get_base_query().where(Attendance.student_id == student_id)

        if start_date is not None:
            query = query.where(Attendance.date >= start_date)
        if end_date is not None:
            query = query.where(Attendance.date <= end_date)

        result = self.db.execute(query)
        records = list(result.scalars().all())

        total_days = len(records)
        present_days = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent_days = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        late_days = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        half_days = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
        excused_days = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)

        # Calculate attendance percentage using the formula from design:
        # (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100
        if total_days > 0:
            attendance_percentage = (
                (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100
            )
        else:
            attendance_percentage = 0.0

        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "half_days": half_days,
            "excused_days": excused_days,
            "attendance_percentage": round(attendance_percentage, 2),
        }

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
        query = self.get_base_query().where(Attendance.class_id == class_id)

        if start_date is not None:
            query = query.where(Attendance.date >= start_date)
        if end_date is not None:
            query = query.where(Attendance.date <= end_date)

        result = self.db.execute(query)
        records = list(result.scalars().all())

        total_records = len(records)
        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        half_day_count = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)

        # Get unique dates
        unique_dates = set(r.date for r in records)
        total_days = len(unique_dates)

        # Get unique students
        unique_students = set(r.student_id for r in records)
        total_students = len(unique_students)

        # Calculate average attendance percentage
        if total_records > 0:
            avg_attendance = (
                (present_count + late_count * 0.5 + half_day_count * 0.5)
                / total_records
                * 100
            )
        else:
            avg_attendance = 0.0

        return {
            "total_days": total_days,
            "total_students": total_students,
            "total_records": total_records,
            "present_count": present_count,
            "absent_count": absent_count,
            "late_count": late_count,
            "half_day_count": half_day_count,
            "average_attendance_percentage": round(avg_attendance, 2),
        }

    def get_daily_attendance_report(
        self,
        class_id: int,
        attendance_date: date,
    ) -> dict[str, Any]:
        """Get detailed attendance report for a class on a specific date.

        Args:
            class_id: The class ID.
            attendance_date: The date for the report.

        Returns:
            Dictionary with daily attendance details.
        """
        records = self.get_by_class_and_date(class_id, attendance_date)

        present = [r for r in records if r.status == AttendanceStatus.PRESENT]
        absent = [r for r in records if r.status == AttendanceStatus.ABSENT]
        late = [r for r in records if r.status == AttendanceStatus.LATE]
        half_day = [r for r in records if r.status == AttendanceStatus.HALF_DAY]
        excused = [r for r in records if r.status == AttendanceStatus.EXCUSED]

        return {
            "date": attendance_date.isoformat(),
            "class_id": class_id,
            "total_marked": len(records),
            "present_count": len(present),
            "absent_count": len(absent),
            "late_count": len(late),
            "half_day_count": len(half_day),
            "excused_count": len(excused),
            "records": [
                {
                    "student_id": r.student_id,
                    "student_name": (
                        r.student.user.profile_data.get("first_name", "")
                        + " "
                        + r.student.user.profile_data.get("last_name", "")
                    ).strip() if r.student and r.student.user else None,
                    "status": r.status.value,
                    "remarks": r.remarks,
                }
                for r in records
            ],
        }
