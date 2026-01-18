"""Timetable repository for data access operations.

This module provides the TimetableRepository class that handles all database
operations related to timetable entries with automatic tenant filtering.
"""

from datetime import time
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.timetable import Timetable
from app.repositories.base import PaginatedResult, TenantAwareRepository


class TimetableRepository(TenantAwareRepository[Timetable]):
    """Repository for timetable data access operations.

    Extends TenantAwareRepository to provide timetable-specific
    query methods with automatic tenant filtering.
    """

    model = Timetable

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the timetable repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_by_id_with_relations(self, timetable_id: int) -> Timetable | None:
        """Get timetable entry by ID with related entities loaded.

        Args:
            timetable_id: The timetable entry ID.

        Returns:
            The Timetable object with relations or None if not found.
        """
        stmt = (
            self.get_base_query()
            .where(Timetable.id == timetable_id)
            .options(
                joinedload(Timetable.class_),
                joinedload(Timetable.section),
                joinedload(Timetable.subject),
                joinedload(Timetable.teacher),
            )
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def check_teacher_conflict(
        self,
        teacher_id: int,
        day_of_week: int,
        period_number: int,
        start_time: time,
        end_time: time,
        exclude_id: int | None = None,
    ) -> Timetable | None:
        """Check if a teacher has a conflicting timetable entry.

        A conflict exists if the teacher is already assigned to another
        class at the same day/period/time.

        Args:
            teacher_id: The teacher ID.
            day_of_week: Day of week (0=Monday, 6=Sunday).
            period_number: Period number.
            start_time: Start time of the period.
            end_time: End time of the period.
            exclude_id: Optional timetable ID to exclude (for updates).

        Returns:
            The conflicting Timetable entry if found, None otherwise.
        """
        stmt = self.get_base_query().where(
            and_(
                Timetable.teacher_id == teacher_id,
                Timetable.day_of_week == day_of_week,
                or_(
                    # Same period number
                    Timetable.period_number == period_number,
                    # Or overlapping time slots
                    and_(
                        Timetable.start_time < end_time,
                        Timetable.end_time > start_time,
                    ),
                ),
            )
        )

        if exclude_id is not None:
            stmt = stmt.where(Timetable.id != exclude_id)

        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def check_class_section_conflict(
        self,
        class_id: int,
        section_id: int | None,
        day_of_week: int,
        period_number: int,
        start_time: time,
        end_time: time,
        exclude_id: int | None = None,
    ) -> Timetable | None:
        """Check if a class/section has a conflicting timetable entry.

        A conflict exists if the class/section already has a subject
        scheduled at the same day/period/time.

        Args:
            class_id: The class ID.
            section_id: Optional section ID.
            day_of_week: Day of week (0=Monday, 6=Sunday).
            period_number: Period number.
            start_time: Start time of the period.
            end_time: End time of the period.
            exclude_id: Optional timetable ID to exclude (for updates).

        Returns:
            The conflicting Timetable entry if found, None otherwise.
        """
        conditions = [
            Timetable.class_id == class_id,
            Timetable.day_of_week == day_of_week,
            or_(
                # Same period number
                Timetable.period_number == period_number,
                # Or overlapping time slots
                and_(
                    Timetable.start_time < end_time,
                    Timetable.end_time > start_time,
                ),
            ),
        ]

        # Handle section_id matching
        if section_id is not None:
            conditions.append(Timetable.section_id == section_id)
        else:
            conditions.append(Timetable.section_id.is_(None))

        stmt = self.get_base_query().where(and_(*conditions))

        if exclude_id is not None:
            stmt = stmt.where(Timetable.id != exclude_id)

        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_class(
        self,
        class_id: int,
        section_id: int | None = None,
    ) -> list[Timetable]:
        """Get all timetable entries for a class.

        Args:
            class_id: The class ID.
            section_id: Optional section ID filter.

        Returns:
            List of Timetable objects.
        """
        stmt = (
            self.get_base_query()
            .where(Timetable.class_id == class_id)
            .options(
                joinedload(Timetable.subject),
                joinedload(Timetable.teacher),
            )
            .order_by(Timetable.day_of_week, Timetable.period_number)
        )

        if section_id is not None:
            stmt = stmt.where(Timetable.section_id == section_id)

        result = self.db.execute(stmt)
        return list(result.scalars().unique().all())

    def get_by_teacher(self, teacher_id: int) -> list[Timetable]:
        """Get all timetable entries for a teacher.

        Args:
            teacher_id: The teacher ID.

        Returns:
            List of Timetable objects.
        """
        stmt = (
            self.get_base_query()
            .where(Timetable.teacher_id == teacher_id)
            .options(
                joinedload(Timetable.class_),
                joinedload(Timetable.section),
                joinedload(Timetable.subject),
            )
            .order_by(Timetable.day_of_week, Timetable.period_number)
        )

        result = self.db.execute(stmt)
        return list(result.scalars().unique().all())

    def get_by_day(
        self,
        day_of_week: int,
        class_id: int | None = None,
        teacher_id: int | None = None,
    ) -> list[Timetable]:
        """Get all timetable entries for a specific day.

        Args:
            day_of_week: Day of week (0=Monday, 6=Sunday).
            class_id: Optional class ID filter.
            teacher_id: Optional teacher ID filter.

        Returns:
            List of Timetable objects.
        """
        stmt = (
            self.get_base_query()
            .where(Timetable.day_of_week == day_of_week)
            .options(
                joinedload(Timetable.class_),
                joinedload(Timetable.section),
                joinedload(Timetable.subject),
                joinedload(Timetable.teacher),
            )
            .order_by(Timetable.period_number)
        )

        if class_id is not None:
            stmt = stmt.where(Timetable.class_id == class_id)
        if teacher_id is not None:
            stmt = stmt.where(Timetable.teacher_id == teacher_id)

        result = self.db.execute(stmt)
        return list(result.scalars().unique().all())

    def list_with_filters(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        teacher_id: int | None = None,
        subject_id: int | None = None,
        day_of_week: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResult[Timetable]:
        """List timetable entries with advanced filtering.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            teacher_id: Optional teacher ID filter.
            subject_id: Optional subject ID filter.
            day_of_week: Optional day of week filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing timetable entries.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        if class_id is not None:
            query = query.where(Timetable.class_id == class_id)
        if section_id is not None:
            query = query.where(Timetable.section_id == section_id)
        if teacher_id is not None:
            query = query.where(Timetable.teacher_id == teacher_id)
        if subject_id is not None:
            query = query.where(Timetable.subject_id == subject_id)
        if day_of_week is not None:
            query = query.where(Timetable.day_of_week == day_of_week)

        # Order by day and period
        query = query.order_by(Timetable.day_of_week, Timetable.period_number)

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(
            joinedload(Timetable.class_),
            joinedload(Timetable.section),
            joinedload(Timetable.subject),
            joinedload(Timetable.teacher),
        )

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def delete_by_class(self, class_id: int) -> int:
        """Delete all timetable entries for a class.

        Args:
            class_id: The class ID.

        Returns:
            Number of deleted entries.
        """
        entries = self.get_by_class(class_id)
        count = len(entries)

        for entry in entries:
            self.db.delete(entry)

        self.db.commit()
        return count
