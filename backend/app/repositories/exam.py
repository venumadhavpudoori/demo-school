"""Exam repository for data access operations.

This module provides the ExamRepository class that handles all database
operations related to exam records with automatic tenant filtering.
"""

from datetime import date
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Exam, ExamType
from app.repositories.base import PaginatedResult, TenantAwareRepository


class ExamRepository(TenantAwareRepository[Exam]):
    """Repository for exam data access operations.

    Extends TenantAwareRepository to provide exam-specific
    query methods with automatic tenant filtering.
    """

    model = Exam

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the exam repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_by_id_with_relations(self, exam_id: int) -> Exam | None:
        """Get exam by ID with related entities loaded.

        Args:
            exam_id: The exam ID.

        Returns:
            The Exam object with relations or None if not found.
        """
        stmt = (
            self.get_base_query()
            .where(Exam.id == exam_id)
            .options(joinedload(Exam.class_))
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_class_and_type(
        self, class_id: int, exam_type: ExamType, academic_year: str | None = None
    ) -> list[Exam]:
        """Get exams for a class by type.

        Args:
            class_id: The class ID.
            exam_type: The exam type.
            academic_year: Optional academic year filter.

        Returns:
            List of Exam objects.
        """
        stmt = self.get_base_query().where(
            and_(
                Exam.class_id == class_id,
                Exam.exam_type == exam_type,
            )
        )
        if academic_year:
            stmt = stmt.where(Exam.academic_year == academic_year)

        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def list_with_filters(
        self,
        class_id: int | None = None,
        exam_type: ExamType | None = None,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Exam]:
        """List exams with advanced filtering.

        Args:
            class_id: Optional class ID filter.
            exam_type: Optional exam type filter.
            academic_year: Optional academic year filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing exam records.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        if class_id is not None:
            query = query.where(Exam.class_id == class_id)
        if exam_type is not None:
            query = query.where(Exam.exam_type == exam_type)
        if academic_year is not None:
            query = query.where(Exam.academic_year == academic_year)
        if start_date is not None:
            query = query.where(Exam.start_date >= start_date)
        if end_date is not None:
            query = query.where(Exam.end_date <= end_date)

        # Order by start_date descending
        query = query.order_by(Exam.start_date.desc(), Exam.id.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(joinedload(Exam.class_))

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_exams_for_academic_year(
        self, academic_year: str, class_id: int | None = None
    ) -> list[Exam]:
        """Get all exams for an academic year.

        Args:
            academic_year: The academic year.
            class_id: Optional class ID filter.

        Returns:
            List of Exam objects.
        """
        query = self.get_base_query().where(Exam.academic_year == academic_year)

        if class_id is not None:
            query = query.where(Exam.class_id == class_id)

        query = query.order_by(Exam.start_date.asc())
        query = query.options(joinedload(Exam.class_))

        result = self.db.execute(query)
        return list(result.scalars().unique().all())

    def check_date_overlap(
        self,
        class_id: int,
        start_date: date,
        end_date: date,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if there's an overlapping exam for the class.

        Args:
            class_id: The class ID.
            start_date: The exam start date.
            end_date: The exam end date.
            exclude_id: Optional exam ID to exclude from check.

        Returns:
            True if there's an overlap, False otherwise.
        """
        query = self.get_base_query().where(
            and_(
                Exam.class_id == class_id,
                Exam.start_date <= end_date,
                Exam.end_date >= start_date,
            )
        )

        if exclude_id is not None:
            query = query.where(Exam.id != exclude_id)

        count_stmt = select(func.count()).select_from(query.subquery())
        count = self.db.execute(count_stmt).scalar() or 0
        return count > 0
