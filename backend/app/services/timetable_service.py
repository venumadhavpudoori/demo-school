"""Timetable service for business logic operations.

This module provides the TimetableService class that handles all business logic
related to timetable management including creation, conflict detection, and querying.
"""

from datetime import time
from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from app.models.timetable import Timetable
from app.repositories.timetable import TimetableRepository
from app.services.cache_service import CacheService


class TimetableServiceError(Exception):
    """Base exception for timetable service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class TimetableNotFoundError(TimetableServiceError):
    """Raised when a timetable entry is not found."""

    def __init__(self, timetable_id: int):
        super().__init__(
            message=f"Timetable entry with ID {timetable_id} not found",
            code="TIMETABLE_NOT_FOUND",
        )


class InvalidTimetableDataError(TimetableServiceError):
    """Raised when timetable data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_TIMETABLE_DATA",
        )


class TimetableConflictError(TimetableServiceError):
    """Raised when a timetable conflict is detected."""

    def __init__(self, conflict_type: str, details: str):
        super().__init__(
            message=f"Timetable conflict: {conflict_type} - {details}",
            code="TIMETABLE_CONFLICT",
        )
        self.conflict_type = conflict_type
        self.details = details


class TimetableService:
    """Service class for timetable business logic.

    Handles all business operations related to timetable including
    creation, updates, conflict detection, and querying.
    """

    # Cache TTL in seconds (5 minutes for timetable data)
    CACHE_TTL = 300
    # Cache entity names
    CACHE_ENTITY_TEACHER_TIMETABLE = "teacher_timetable"
    CACHE_ENTITY_CLASS_TIMETABLE = "class_timetable"

    def __init__(self, db: Session, tenant_id: int, redis: Redis | None = None):
        """Initialize the timetable service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
            redis: Optional Redis client for caching.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = TimetableRepository(db, tenant_id)
        self.redis = redis
        self.cache = CacheService(redis, tenant_id) if redis else None

    def create_timetable_entry(
        self,
        class_id: int,
        day_of_week: int,
        period_number: int,
        subject_id: int,
        start_time: time,
        end_time: time,
        teacher_id: int | None = None,
        section_id: int | None = None,
    ) -> Timetable:
        """Create a new timetable entry with conflict detection.

        Args:
            class_id: The class ID.
            day_of_week: Day of week (0=Monday, 6=Sunday).
            period_number: Period number.
            subject_id: The subject ID.
            start_time: Start time of the period.
            end_time: End time of the period.
            teacher_id: Optional teacher ID.
            section_id: Optional section ID.

        Returns:
            The created Timetable object.

        Raises:
            InvalidTimetableDataError: If timetable data is invalid.
            TimetableConflictError: If a conflict is detected.
        """
        # Validate day_of_week
        if day_of_week < 0 or day_of_week > 6:
            raise InvalidTimetableDataError(
                "day_of_week must be between 0 (Monday) and 6 (Sunday)"
            )

        # Validate period_number
        if period_number < 1:
            raise InvalidTimetableDataError("period_number must be at least 1")

        # Validate time range
        if end_time <= start_time:
            raise InvalidTimetableDataError("end_time must be after start_time")

        # Check for teacher conflict
        if teacher_id is not None:
            teacher_conflict = self.repository.check_teacher_conflict(
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                period_number=period_number,
                start_time=start_time,
                end_time=end_time,
            )
            if teacher_conflict:
                raise TimetableConflictError(
                    conflict_type="TEACHER_CONFLICT",
                    details=f"Teacher {teacher_id} is already assigned to another class "
                    f"on day {day_of_week}, period {period_number}",
                )

        # Check for class/section conflict
        class_conflict = self.repository.check_class_section_conflict(
            class_id=class_id,
            section_id=section_id,
            day_of_week=day_of_week,
            period_number=period_number,
            start_time=start_time,
            end_time=end_time,
        )
        if class_conflict:
            section_info = f" section {section_id}" if section_id else ""
            raise TimetableConflictError(
                conflict_type="CLASS_CONFLICT",
                details=f"Class {class_id}{section_info} already has a subject scheduled "
                f"on day {day_of_week}, period {period_number}",
            )

        # Create the timetable entry
        timetable = self.repository.create({
            "class_id": class_id,
            "section_id": section_id,
            "day_of_week": day_of_week,
            "period_number": period_number,
            "subject_id": subject_id,
            "teacher_id": teacher_id,
            "start_time": start_time,
            "end_time": end_time,
        })

        # Invalidate relevant caches
        self._invalidate_timetable_cache(class_id, section_id, teacher_id)

        return timetable

    def _invalidate_timetable_cache(
        self,
        class_id: int,
        section_id: int | None = None,
        teacher_id: int | None = None,
    ) -> None:
        """Invalidate timetable cache entries.

        Args:
            class_id: The class ID.
            section_id: Optional section ID.
            teacher_id: Optional teacher ID.
        """
        if self.cache:
            # Invalidate class timetable cache
            class_cache_key = self._get_class_timetable_cache_key(class_id, section_id)
            self.cache.invalidate(self.CACHE_ENTITY_CLASS_TIMETABLE, class_cache_key)

            # Also invalidate class timetable without section filter
            if section_id is not None:
                class_cache_key_no_section = self._get_class_timetable_cache_key(class_id, None)
                self.cache.invalidate(self.CACHE_ENTITY_CLASS_TIMETABLE, class_cache_key_no_section)

            # Invalidate teacher timetable cache
            if teacher_id is not None:
                self.cache.invalidate(self.CACHE_ENTITY_TEACHER_TIMETABLE, str(teacher_id))

    def _get_class_timetable_cache_key(
        self,
        class_id: int,
        section_id: int | None,
    ) -> str:
        """Generate cache key for class timetable.

        Args:
            class_id: The class ID.
            section_id: Optional section ID.

        Returns:
            Cache key string.
        """
        return f"{class_id}:{section_id or 'all'}"

    def get_timetable_entry(self, timetable_id: int) -> Timetable:
        """Get a timetable entry by ID.

        Args:
            timetable_id: The timetable entry ID.

        Returns:
            The Timetable object.

        Raises:
            TimetableNotFoundError: If timetable entry not found.
        """
        timetable = self.repository.get_by_id_with_relations(timetable_id)
        if timetable is None:
            raise TimetableNotFoundError(timetable_id)
        return timetable

    def update_timetable_entry(
        self,
        timetable_id: int,
        day_of_week: int | None = None,
        period_number: int | None = None,
        subject_id: int | None = None,
        teacher_id: int | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        section_id: int | None = None,
    ) -> Timetable:
        """Update a timetable entry with conflict detection.

        Args:
            timetable_id: The timetable entry ID.
            day_of_week: Optional new day of week.
            period_number: Optional new period number.
            subject_id: Optional new subject ID.
            teacher_id: Optional new teacher ID.
            start_time: Optional new start time.
            end_time: Optional new end time.
            section_id: Optional new section ID.

        Returns:
            The updated Timetable object.

        Raises:
            TimetableNotFoundError: If timetable entry not found.
            InvalidTimetableDataError: If timetable data is invalid.
            TimetableConflictError: If a conflict is detected.
        """
        timetable = self.repository.get_by_id(timetable_id)
        if timetable is None:
            raise TimetableNotFoundError(timetable_id)

        # Determine final values for conflict checking
        final_day = day_of_week if day_of_week is not None else timetable.day_of_week
        final_period = period_number if period_number is not None else timetable.period_number
        final_start = start_time if start_time is not None else timetable.start_time
        final_end = end_time if end_time is not None else timetable.end_time
        final_teacher = teacher_id if teacher_id is not None else timetable.teacher_id
        final_section = section_id if section_id is not None else timetable.section_id

        # Validate day_of_week
        if final_day < 0 or final_day > 6:
            raise InvalidTimetableDataError(
                "day_of_week must be between 0 (Monday) and 6 (Sunday)"
            )

        # Validate period_number
        if final_period < 1:
            raise InvalidTimetableDataError("period_number must be at least 1")

        # Validate time range
        if final_end <= final_start:
            raise InvalidTimetableDataError("end_time must be after start_time")

        # Check for teacher conflict (excluding current entry)
        if final_teacher is not None:
            teacher_conflict = self.repository.check_teacher_conflict(
                teacher_id=final_teacher,
                day_of_week=final_day,
                period_number=final_period,
                start_time=final_start,
                end_time=final_end,
                exclude_id=timetable_id,
            )
            if teacher_conflict:
                raise TimetableConflictError(
                    conflict_type="TEACHER_CONFLICT",
                    details=f"Teacher {final_teacher} is already assigned to another class "
                    f"on day {final_day}, period {final_period}",
                )

        # Check for class/section conflict (excluding current entry)
        class_conflict = self.repository.check_class_section_conflict(
            class_id=timetable.class_id,
            section_id=final_section,
            day_of_week=final_day,
            period_number=final_period,
            start_time=final_start,
            end_time=final_end,
            exclude_id=timetable_id,
        )
        if class_conflict:
            section_info = f" section {final_section}" if final_section else ""
            raise TimetableConflictError(
                conflict_type="CLASS_CONFLICT",
                details=f"Class {timetable.class_id}{section_info} already has a subject scheduled "
                f"on day {final_day}, period {final_period}",
            )

        # Update the timetable entry
        update_data: dict[str, Any] = {}
        if day_of_week is not None:
            update_data["day_of_week"] = day_of_week
        if period_number is not None:
            update_data["period_number"] = period_number
        if subject_id is not None:
            update_data["subject_id"] = subject_id
        if teacher_id is not None:
            update_data["teacher_id"] = teacher_id
        if start_time is not None:
            update_data["start_time"] = start_time
        if end_time is not None:
            update_data["end_time"] = end_time
        if section_id is not None:
            update_data["section_id"] = section_id

        if update_data:
            # Track old teacher_id for cache invalidation
            old_teacher_id = timetable.teacher_id

            for field, value in update_data.items():
                setattr(timetable, field, value)
            self.db.commit()
            self.db.refresh(timetable)

            # Invalidate caches for both old and new teacher
            self._invalidate_timetable_cache(
                timetable.class_id,
                timetable.section_id,
                timetable.teacher_id,
            )
            if old_teacher_id and old_teacher_id != timetable.teacher_id:
                if self.cache:
                    self.cache.invalidate(self.CACHE_ENTITY_TEACHER_TIMETABLE, str(old_teacher_id))

        return timetable

    def delete_timetable_entry(self, timetable_id: int) -> bool:
        """Delete a timetable entry.

        Args:
            timetable_id: The timetable entry ID.

        Returns:
            True if deleted successfully.

        Raises:
            TimetableNotFoundError: If timetable entry not found.
        """
        timetable = self.repository.get_by_id(timetable_id)
        if timetable is None:
            raise TimetableNotFoundError(timetable_id)

        # Store values for cache invalidation before delete
        class_id = timetable.class_id
        section_id = timetable.section_id
        teacher_id = timetable.teacher_id

        self.db.delete(timetable)
        self.db.commit()

        # Invalidate caches after delete
        self._invalidate_timetable_cache(class_id, section_id, teacher_id)

        return True

    def list_timetable(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        teacher_id: int | None = None,
        subject_id: int | None = None,
        day_of_week: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List timetable entries with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            teacher_id: Optional teacher ID filter.
            subject_id: Optional subject ID filter.
            day_of_week: Optional day of week filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_with_filters(
            class_id=class_id,
            section_id=section_id,
            teacher_id=teacher_id,
            subject_id=subject_id,
            day_of_week=day_of_week,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                self._timetable_to_dict(entry)
                for entry in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def get_class_timetable(
        self,
        class_id: int,
        section_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get complete timetable for a class.

        Args:
            class_id: The class ID.
            section_id: Optional section ID filter.

        Returns:
            List of timetable entry dictionaries.
        """
        # Try to get from cache first
        if self.cache:
            cache_key = self._get_class_timetable_cache_key(class_id, section_id)
            cached_result = self.cache.get(self.CACHE_ENTITY_CLASS_TIMETABLE, cache_key)
            if cached_result is not None:
                return cached_result

        entries = self.repository.get_by_class(class_id, section_id)
        result = [self._timetable_to_dict(entry) for entry in entries]

        # Cache the result
        if self.cache:
            cache_key = self._get_class_timetable_cache_key(class_id, section_id)
            self.cache.set(self.CACHE_ENTITY_CLASS_TIMETABLE, cache_key, result, self.CACHE_TTL)

        return result

    def get_teacher_timetable(self, teacher_id: int) -> list[dict[str, Any]]:
        """Get complete timetable for a teacher.

        Args:
            teacher_id: The teacher ID.

        Returns:
            List of timetable entry dictionaries.
        """
        # Try to get from cache first
        if self.cache:
            cached_result = self.cache.get(self.CACHE_ENTITY_TEACHER_TIMETABLE, str(teacher_id))
            if cached_result is not None:
                return cached_result

        entries = self.repository.get_by_teacher(teacher_id)
        result = [self._timetable_to_dict(entry) for entry in entries]

        # Cache the result
        if self.cache:
            self.cache.set(self.CACHE_ENTITY_TEACHER_TIMETABLE, str(teacher_id), result, self.CACHE_TTL)

        return result

    def get_day_timetable(
        self,
        day_of_week: int,
        class_id: int | None = None,
        teacher_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get timetable for a specific day.

        Args:
            day_of_week: Day of week (0=Monday, 6=Sunday).
            class_id: Optional class ID filter.
            teacher_id: Optional teacher ID filter.

        Returns:
            List of timetable entry dictionaries.
        """
        entries = self.repository.get_by_day(day_of_week, class_id, teacher_id)
        return [self._timetable_to_dict(entry) for entry in entries]

    def check_conflicts(
        self,
        class_id: int,
        day_of_week: int,
        period_number: int,
        start_time: time,
        end_time: time,
        teacher_id: int | None = None,
        section_id: int | None = None,
        exclude_id: int | None = None,
    ) -> dict[str, Any]:
        """Check for potential conflicts without creating an entry.

        Args:
            class_id: The class ID.
            day_of_week: Day of week (0=Monday, 6=Sunday).
            period_number: Period number.
            start_time: Start time of the period.
            end_time: End time of the period.
            teacher_id: Optional teacher ID.
            section_id: Optional section ID.
            exclude_id: Optional timetable ID to exclude (for updates).

        Returns:
            Dictionary with conflict information.
        """
        conflicts = {
            "has_conflicts": False,
            "teacher_conflict": None,
            "class_conflict": None,
        }

        # Check teacher conflict
        if teacher_id is not None:
            teacher_conflict = self.repository.check_teacher_conflict(
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                period_number=period_number,
                start_time=start_time,
                end_time=end_time,
                exclude_id=exclude_id,
            )
            if teacher_conflict:
                conflicts["has_conflicts"] = True
                conflicts["teacher_conflict"] = {
                    "id": teacher_conflict.id,
                    "class_id": teacher_conflict.class_id,
                    "subject_id": teacher_conflict.subject_id,
                    "day_of_week": teacher_conflict.day_of_week,
                    "period_number": teacher_conflict.period_number,
                }

        # Check class/section conflict
        class_conflict = self.repository.check_class_section_conflict(
            class_id=class_id,
            section_id=section_id,
            day_of_week=day_of_week,
            period_number=period_number,
            start_time=start_time,
            end_time=end_time,
            exclude_id=exclude_id,
        )
        if class_conflict:
            conflicts["has_conflicts"] = True
            conflicts["class_conflict"] = {
                "id": class_conflict.id,
                "subject_id": class_conflict.subject_id,
                "teacher_id": class_conflict.teacher_id,
                "day_of_week": class_conflict.day_of_week,
                "period_number": class_conflict.period_number,
            }

        return conflicts

    def _timetable_to_dict(self, entry: Timetable) -> dict[str, Any]:
        """Convert a Timetable object to a dictionary.

        Args:
            entry: The Timetable object.

        Returns:
            Dictionary representation of the timetable entry.
        """
        return {
            "id": entry.id,
            "class_id": entry.class_id,
            "class_name": entry.class_.name if entry.class_ else None,
            "section_id": entry.section_id,
            "section_name": entry.section.name if entry.section else None,
            "day_of_week": entry.day_of_week,
            "day_name": self._get_day_name(entry.day_of_week),
            "period_number": entry.period_number,
            "subject_id": entry.subject_id,
            "subject_name": entry.subject.name if entry.subject else None,
            "subject_code": entry.subject.code if entry.subject else None,
            "teacher_id": entry.teacher_id,
            "teacher_name": self._get_teacher_name(entry.teacher) if entry.teacher else None,
            "start_time": entry.start_time.isoformat() if entry.start_time else None,
            "end_time": entry.end_time.isoformat() if entry.end_time else None,
        }

    @staticmethod
    def _get_day_name(day_of_week: int) -> str:
        """Get the name of a day from its number.

        Args:
            day_of_week: Day number (0=Monday, 6=Sunday).

        Returns:
            Day name string.
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if 0 <= day_of_week <= 6:
            return days[day_of_week]
        return "Unknown"

    @staticmethod
    def _get_teacher_name(teacher) -> str | None:
        """Get the full name of a teacher.

        Args:
            teacher: The Teacher object.

        Returns:
            Full name string or None.
        """
        if teacher and teacher.user:
            profile = teacher.user.profile_data or {}
            first_name = profile.get("first_name", "")
            last_name = profile.get("last_name", "")
            return f"{first_name} {last_name}".strip() or None
        return None
