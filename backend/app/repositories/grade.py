"""Grade repository for data access operations.

This module provides the GradeRepository class that handles all database
operations related to grade records with automatic tenant filtering.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Grade
from app.repositories.base import PaginatedResult, TenantAwareRepository


class GradeRepository(TenantAwareRepository[Grade]):
    """Repository for grade data access operations.

    Extends TenantAwareRepository to provide grade-specific
    query methods with automatic tenant filtering.
    """

    model = Grade

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the grade repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_by_id_with_relations(self, grade_id: int) -> Grade | None:
        """Get grade by ID with related entities loaded.

        Args:
            grade_id: The grade ID.

        Returns:
            The Grade object with relations or None if not found.
        """
        stmt = (
            self.get_base_query()
            .where(Grade.id == grade_id)
            .options(
                joinedload(Grade.student),
                joinedload(Grade.subject),
                joinedload(Grade.exam),
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_student_subject_exam(
        self, student_id: int, subject_id: int, exam_id: int
    ) -> Grade | None:
        """Get grade for a specific student, subject, and exam combination.

        Args:
            student_id: The student ID.
            subject_id: The subject ID.
            exam_id: The exam ID.

        Returns:
            The Grade object or None if not found.
        """
        stmt = self.get_base_query().where(
            and_(
                Grade.student_id == student_id,
                Grade.subject_id == subject_id,
                Grade.exam_id == exam_id,
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_student_grades(
        self,
        student_id: int,
        exam_id: int | None = None,
        subject_id: int | None = None,
    ) -> list[Grade]:
        """Get all grades for a student.

        Args:
            student_id: The student ID.
            exam_id: Optional exam ID filter.
            subject_id: Optional subject ID filter.

        Returns:
            List of Grade objects.
        """
        query = self.get_base_query().where(Grade.student_id == student_id)

        if exam_id is not None:
            query = query.where(Grade.exam_id == exam_id)
        if subject_id is not None:
            query = query.where(Grade.subject_id == subject_id)

        query = query.options(
            joinedload(Grade.subject),
            joinedload(Grade.exam),
        )

        result = self.db.execute(query)
        return list(result.scalars().unique().all())

    def get_exam_grades(self, exam_id: int, subject_id: int | None = None) -> list[Grade]:
        """Get all grades for an exam.

        Args:
            exam_id: The exam ID.
            subject_id: Optional subject ID filter.

        Returns:
            List of Grade objects.
        """
        query = self.get_base_query().where(Grade.exam_id == exam_id)

        if subject_id is not None:
            query = query.where(Grade.subject_id == subject_id)

        query = query.options(
            joinedload(Grade.student),
            joinedload(Grade.subject),
        )

        result = self.db.execute(query)
        return list(result.scalars().unique().all())

    def list_with_filters(
        self,
        student_id: int | None = None,
        subject_id: int | None = None,
        exam_id: int | None = None,
        class_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Grade]:
        """List grades with advanced filtering.

        Args:
            student_id: Optional student ID filter.
            subject_id: Optional subject ID filter.
            exam_id: Optional exam ID filter.
            class_id: Optional class ID filter (via exam).
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing grade records.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        if student_id is not None:
            query = query.where(Grade.student_id == student_id)
        if subject_id is not None:
            query = query.where(Grade.subject_id == subject_id)
        if exam_id is not None:
            query = query.where(Grade.exam_id == exam_id)

        # Handle class_id filter through exam relationship
        if class_id is not None:
            from app.models.exam import Exam
            query = query.join(Exam, Grade.exam_id == Exam.id).where(
                Exam.class_id == class_id
            )

        # Order by id descending
        query = query.order_by(Grade.id.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Grade.student),
            joinedload(Grade.subject),
            joinedload(Grade.exam),
        )

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def bulk_create(self, records: list[dict[str, Any]]) -> list[Grade]:
        """Create multiple grade records in bulk.

        Args:
            records: List of dictionaries with grade data.

        Returns:
            List of created Grade objects.
        """
        grade_records = []
        for record in records:
            record["tenant_id"] = self.tenant_id
            grade = Grade(**record)
            self.db.add(grade)
            grade_records.append(grade)

        self.db.commit()
        for record in grade_records:
            self.db.refresh(record)

        return grade_records

    def bulk_upsert(
        self,
        exam_id: int,
        subject_id: int,
        max_marks: Decimal,
        records: list[dict[str, Any]],
    ) -> list[Grade]:
        """Create or update grade records for an exam and subject.

        If a grade exists for a student in the given exam/subject, it will be updated.
        Otherwise, a new record will be created.

        Args:
            exam_id: The exam ID.
            subject_id: The subject ID.
            max_marks: The maximum marks for all entries.
            records: List of dicts with student_id, marks_obtained, and optional remarks.

        Returns:
            List of created/updated Grade objects.
        """
        result_records = []

        for record in records:
            student_id = record["student_id"]
            marks_obtained = record["marks_obtained"]
            remarks = record.get("remarks")
            grade_letter = record.get("grade")

            # Check if record exists
            existing = self.get_by_student_subject_exam(student_id, subject_id, exam_id)

            if existing:
                # Update existing record
                existing.marks_obtained = marks_obtained
                existing.max_marks = max_marks
                existing.grade = grade_letter
                existing.remarks = remarks
                result_records.append(existing)
            else:
                # Create new record
                grade = Grade(
                    tenant_id=self.tenant_id,
                    student_id=student_id,
                    subject_id=subject_id,
                    exam_id=exam_id,
                    marks_obtained=marks_obtained,
                    max_marks=max_marks,
                    grade=grade_letter,
                    remarks=remarks,
                )
                self.db.add(grade)
                result_records.append(grade)

        self.db.commit()
        for record in result_records:
            self.db.refresh(record)

        return result_records

    def get_subject_statistics(
        self, exam_id: int, subject_id: int
    ) -> dict[str, Any]:
        """Get statistics for a subject in an exam.

        Args:
            exam_id: The exam ID.
            subject_id: The subject ID.

        Returns:
            Dictionary with statistics.
        """
        grades = self.get_exam_grades(exam_id, subject_id)

        if not grades:
            return {
                "total_students": 0,
                "average_marks": 0.0,
                "average_percentage": 0.0,
                "highest_marks": 0.0,
                "lowest_marks": 0.0,
                "pass_count": 0,
                "fail_count": 0,
                "pass_percentage": 0.0,
                "grade_distribution": {},
            }

        marks_list = [float(g.marks_obtained) for g in grades]
        max_marks = float(grades[0].max_marks) if grades else 100.0
        percentages = [(m / max_marks * 100) if max_marks > 0 else 0 for m in marks_list]

        # Count grades
        grade_distribution: dict[str, int] = {}
        pass_count = 0
        fail_count = 0
        pass_threshold = 33.0  # Default pass percentage

        for grade in grades:
            grade_letter = grade.grade or "N/A"
            grade_distribution[grade_letter] = grade_distribution.get(grade_letter, 0) + 1

            percentage = (
                float(grade.marks_obtained) / float(grade.max_marks) * 100
                if float(grade.max_marks) > 0
                else 0
            )
            if percentage >= pass_threshold:
                pass_count += 1
            else:
                fail_count += 1

        total_students = len(grades)

        return {
            "total_students": total_students,
            "average_marks": round(sum(marks_list) / total_students, 2),
            "average_percentage": round(sum(percentages) / total_students, 2),
            "highest_marks": max(marks_list),
            "lowest_marks": min(marks_list),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_percentage": round(pass_count / total_students * 100, 2) if total_students > 0 else 0.0,
            "grade_distribution": grade_distribution,
        }
