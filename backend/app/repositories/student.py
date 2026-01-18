"""Student repository for data access operations.

This module provides the StudentRepository class that extends TenantAwareRepository
with student-specific query methods.
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance, AttendanceStatus
from app.models.exam import Grade
from app.models.fee import Fee, FeeStatus
from app.models.student import Student, StudentStatus
from app.models.user import User
from app.repositories.base import PaginatedResult, TenantAwareRepository


class StudentRepository(TenantAwareRepository[Student]):
    """Repository for student data access operations.

    Extends TenantAwareRepository with student-specific methods for
    searching, filtering, and aggregating student data.
    """

    model = Student

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the student repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Student]]:
        """Return base query with eager loading of user relationship.

        Returns:
            A SQLAlchemy Select statement with user relationship loaded.
        """
        return (
            select(Student)
            .options(joinedload(Student.user))
            .where(Student.tenant_id == self.tenant_id)
        )

    def get_by_id_with_relations(self, id: int) -> Student | None:
        """Get student by ID with all relationships loaded.

        Args:
            id: The student ID.

        Returns:
            The student with relationships if found, None otherwise.
        """
        stmt = (
            select(Student)
            .options(
                joinedload(Student.user),
                joinedload(Student.class_),
                joinedload(Student.section),
            )
            .where(
                Student.tenant_id == self.tenant_id,
                Student.id == id,
            )
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_admission_number(self, admission_number: str) -> Student | None:
        """Get student by admission number within tenant scope.

        Args:
            admission_number: The student's admission number.

        Returns:
            The student if found, None otherwise.
        """
        stmt = self.get_base_query().where(
            Student.admission_number == admission_number
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Student | None:
        """Get student by user ID within tenant scope.

        Args:
            user_id: The associated user's ID.

        Returns:
            The student if found, None otherwise.
        """
        stmt = self.get_base_query().where(Student.user_id == user_id)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def list_by_class(
        self,
        class_id: int,
        section_id: int | None = None,
        include_inactive: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Student]:
        """List students by class and optionally section.

        Args:
            class_id: The class ID to filter by.
            section_id: Optional section ID to filter by.
            include_inactive: Whether to include inactive students.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the students.
        """
        filters: dict[str, Any] = {"class_id": class_id}
        if section_id is not None:
            filters["section_id"] = section_id
        if not include_inactive:
            filters["status"] = StudentStatus.ACTIVE

        return self.list(filters=filters, page=page, page_size=page_size)

    def search(
        self,
        query: str,
        class_id: int | None = None,
        section_id: int | None = None,
        status: StudentStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Student]:
        """Search students by name, email, or admission number.

        Args:
            query: Search query string.
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            status: Optional status filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing matching students.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Build base query with join to User for name/email search
        base_query = (
            select(Student)
            .join(User, Student.user_id == User.id)
            .options(joinedload(Student.user))
            .where(Student.tenant_id == self.tenant_id)
        )

        # Apply search filter
        search_pattern = f"%{query}%"
        base_query = base_query.where(
            or_(
                Student.admission_number.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.profile_data["first_name"].astext.ilike(search_pattern),
                User.profile_data["last_name"].astext.ilike(search_pattern),
            )
        )

        # Apply additional filters
        if class_id is not None:
            base_query = base_query.where(Student.class_id == class_id)
        if section_id is not None:
            base_query = base_query.where(Student.section_id == section_id)
        if status is not None:
            base_query = base_query.where(Student.status == status)

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(base_query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_attendance_summary(
        self,
        student_id: int,
        academic_year: str | None = None,
    ) -> dict[str, Any]:
        """Get attendance summary for a student.

        Args:
            student_id: The student ID.
            academic_year: Optional academic year filter.

        Returns:
            Dictionary with attendance statistics.
        """
        base_query = select(Attendance).where(
            Attendance.tenant_id == self.tenant_id,
            Attendance.student_id == student_id,
        )

        # Get counts by status
        total_query = select(func.count()).select_from(base_query.subquery())
        total_days = self.db.execute(total_query).scalar() or 0

        present_query = select(func.count()).select_from(
            base_query.where(Attendance.status == AttendanceStatus.PRESENT).subquery()
        )
        present_days = self.db.execute(present_query).scalar() or 0

        absent_query = select(func.count()).select_from(
            base_query.where(Attendance.status == AttendanceStatus.ABSENT).subquery()
        )
        absent_days = self.db.execute(absent_query).scalar() or 0

        late_query = select(func.count()).select_from(
            base_query.where(Attendance.status == AttendanceStatus.LATE).subquery()
        )
        late_days = self.db.execute(late_query).scalar() or 0

        half_day_query = select(func.count()).select_from(
            base_query.where(Attendance.status == AttendanceStatus.HALF_DAY).subquery()
        )
        half_days = self.db.execute(half_day_query).scalar() or 0

        # Calculate percentage
        if total_days > 0:
            effective_present = present_days + (late_days * 0.5) + (half_days * 0.5)
            percentage = (effective_present / total_days) * 100
        else:
            percentage = 0.0

        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "half_days": half_days,
            "attendance_percentage": round(percentage, 2),
        }

    def get_grades_summary(self, student_id: int) -> list[dict[str, Any]]:
        """Get grades summary for a student.

        Args:
            student_id: The student ID.

        Returns:
            List of grade records with subject and exam info.
        """
        stmt = (
            select(Grade)
            .options(
                joinedload(Grade.subject),
                joinedload(Grade.exam),
            )
            .where(
                Grade.tenant_id == self.tenant_id,
                Grade.student_id == student_id,
            )
            .order_by(Grade.created_at.desc())
        )
        result = self.db.execute(stmt)
        grades = result.unique().scalars().all()

        return [
            {
                "id": grade.id,
                "subject_name": grade.subject.name if grade.subject else None,
                "exam_name": grade.exam.name if grade.exam else None,
                "marks_obtained": float(grade.marks_obtained),
                "max_marks": float(grade.max_marks),
                "percentage": round(
                    float(grade.marks_obtained) / float(grade.max_marks) * 100, 2
                )
                if grade.max_marks > 0
                else 0,
                "grade": grade.grade,
                "remarks": grade.remarks,
            }
            for grade in grades
        ]

    def get_fees_summary(self, student_id: int) -> dict[str, Any]:
        """Get fees summary for a student.

        Args:
            student_id: The student ID.

        Returns:
            Dictionary with fee statistics and recent fees.
        """
        base_query = select(Fee).where(
            Fee.tenant_id == self.tenant_id,
            Fee.student_id == student_id,
        )

        # Get total amounts
        total_amount_query = select(func.sum(Fee.amount)).select_from(
            base_query.subquery()
        )
        total_amount = self.db.execute(total_amount_query).scalar() or 0

        paid_amount_query = select(func.sum(Fee.paid_amount)).select_from(
            base_query.subquery()
        )
        total_paid = self.db.execute(paid_amount_query).scalar() or 0

        # Get pending fees count
        pending_query = select(func.count()).select_from(
            base_query.where(Fee.status.in_([FeeStatus.PENDING, FeeStatus.PARTIAL])).subquery()
        )
        pending_count = self.db.execute(pending_query).scalar() or 0

        # Get recent fees
        recent_fees_stmt = (
            base_query.order_by(Fee.due_date.desc()).limit(5)
        )
        result = self.db.execute(recent_fees_stmt)
        recent_fees = result.scalars().all()

        return {
            "total_amount": float(total_amount),
            "total_paid": float(total_paid),
            "balance": float(total_amount - total_paid),
            "pending_count": pending_count,
            "recent_fees": [
                {
                    "id": fee.id,
                    "fee_type": fee.fee_type,
                    "amount": float(fee.amount),
                    "paid_amount": float(fee.paid_amount),
                    "due_date": fee.due_date.isoformat(),
                    "status": fee.status.value,
                }
                for fee in recent_fees
            ],
        }

    def admission_number_exists(self, admission_number: str, exclude_id: int | None = None) -> bool:
        """Check if admission number already exists within tenant.

        Args:
            admission_number: The admission number to check.
            exclude_id: Optional student ID to exclude from check (for updates).

        Returns:
            True if admission number exists, False otherwise.
        """
        query = select(func.count()).where(
            Student.tenant_id == self.tenant_id,
            Student.admission_number == admission_number,
        )
        if exclude_id is not None:
            query = query.where(Student.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0
