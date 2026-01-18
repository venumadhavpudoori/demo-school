"""Property-based tests for timetable conflict detection.

**Feature: school-erp-multi-tenancy, Property 13: Timetable Conflict Detection**
**Validates: Design - Property 13**

Property 13: Timetable Conflict Detection
*For any* timetable entry creation, if a teacher is already assigned to another class
at the same day/period/time, the creation SHALL be rejected with a conflict error.
"""

from datetime import time
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.timetable_service import (
    TimetableService,
    TimetableConflictError,
    InvalidTimetableDataError,
)


# Strategy for valid tenant IDs
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid class IDs
class_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid section IDs (optional)
section_id_strategy = st.one_of(st.none(), st.integers(min_value=1, max_value=1_000_000))

# Strategy for valid teacher IDs
teacher_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid subject IDs
subject_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for day of week (0=Monday, 6=Sunday)
day_of_week_strategy = st.integers(min_value=0, max_value=6)

# Strategy for period number (1-indexed)
period_number_strategy = st.integers(min_value=1, max_value=10)

# Strategy for valid time (hours and minutes)
def time_strategy():
    """Generate valid time objects."""
    return st.builds(
        time,
        hour=st.integers(min_value=6, max_value=18),
        minute=st.sampled_from([0, 15, 30, 45]),
    )


# Strategy for a valid time range (start_time < end_time)
@st.composite
def time_range_strategy(draw):
    """Generate a valid time range where start_time < end_time."""
    start_hour = draw(st.integers(min_value=6, max_value=16))
    start_minute = draw(st.sampled_from([0, 30]))
    
    # End time must be after start time - ensure at least 30 min gap
    end_hour = start_hour + 1
    end_minute = start_minute
    
    return time(start_hour, start_minute), time(end_hour, end_minute)


class MockTimetable:
    """Mock timetable model for testing."""
    
    _id_counter = 0
    
    def __init__(self, **kwargs):
        MockTimetable._id_counter += 1
        self.id = MockTimetable._id_counter
        self.tenant_id = kwargs.get("tenant_id")
        self.class_id = kwargs.get("class_id")
        self.section_id = kwargs.get("section_id")
        self.day_of_week = kwargs.get("day_of_week")
        self.period_number = kwargs.get("period_number")
        self.subject_id = kwargs.get("subject_id")
        self.teacher_id = kwargs.get("teacher_id")
        self.start_time = kwargs.get("start_time")
        self.end_time = kwargs.get("end_time")


class TestTimetableConflictDetection:
    """**Feature: school-erp-multi-tenancy, Property 13: Timetable Conflict Detection**"""

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id=teacher_id_strategy,
        class_id_1=class_id_strategy,
        class_id_2=class_id_strategy,
        subject_id_1=subject_id_strategy,
        subject_id_2=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_teacher_conflict_detected_same_day_period(
        self,
        tenant_id: int,
        teacher_id: int,
        class_id_1: int,
        class_id_2: int,
        subject_id_1: int,
        subject_id_2: int,
        day_of_week: int,
        period_number: int,
        time_range: tuple[time, time],
    ):
        """For any teacher already assigned to a class at day/period, creating another entry SHALL be rejected.

        **Validates: Design - Property 13**
        """
        # Ensure different classes for the conflict scenario
        assume(class_id_1 != class_id_2)
        
        start_time, end_time = time_range
        
        # Arrange: Create mock database and repository
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        # Create an existing timetable entry for the teacher
        existing_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id_1,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number,
            subject_id=subject_id_1,
            teacher_id=teacher_id,
            start_time=start_time,
            end_time=end_time,
        )
        
        # Mock the repository to return the existing entry as a conflict
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # Teacher conflict check returns the existing entry
            mock_repo_instance.check_teacher_conflict.return_value = existing_entry
            # Class conflict check returns None (no class conflict)
            mock_repo_instance.check_class_section_conflict.return_value = None
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act & Assert: Creating a new entry for the same teacher at same day/period should raise conflict
            with pytest.raises(TimetableConflictError) as exc_info:
                service.create_timetable_entry(
                    class_id=class_id_2,
                    day_of_week=day_of_week,
                    period_number=period_number,
                    subject_id=subject_id_2,
                    start_time=start_time,
                    end_time=end_time,
                    teacher_id=teacher_id,
                )
            
            # Verify the conflict type
            assert exc_info.value.conflict_type == "TEACHER_CONFLICT", (
                f"Expected TEACHER_CONFLICT, got {exc_info.value.conflict_type}"
            )

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id=teacher_id_strategy,
        class_id=class_id_strategy,
        subject_id_1=subject_id_strategy,
        subject_id_2=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_class_conflict_detected_same_day_period(
        self,
        tenant_id: int,
        teacher_id: int,
        class_id: int,
        subject_id_1: int,
        subject_id_2: int,
        day_of_week: int,
        period_number: int,
        time_range: tuple[time, time],
    ):
        """For any class already having a subject at day/period, creating another entry SHALL be rejected.

        **Validates: Design - Property 13**
        """
        # Ensure different subjects for the conflict scenario
        assume(subject_id_1 != subject_id_2)
        
        start_time, end_time = time_range
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        # Create an existing timetable entry for the class
        existing_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number,
            subject_id=subject_id_1,
            teacher_id=teacher_id,
            start_time=start_time,
            end_time=end_time,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # Teacher conflict check returns None (no teacher conflict)
            mock_repo_instance.check_teacher_conflict.return_value = None
            # Class conflict check returns the existing entry
            mock_repo_instance.check_class_section_conflict.return_value = existing_entry
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act & Assert
            with pytest.raises(TimetableConflictError) as exc_info:
                service.create_timetable_entry(
                    class_id=class_id,
                    day_of_week=day_of_week,
                    period_number=period_number,
                    subject_id=subject_id_2,
                    start_time=start_time,
                    end_time=end_time,
                    teacher_id=teacher_id,
                )
            
            assert exc_info.value.conflict_type == "CLASS_CONFLICT", (
                f"Expected CLASS_CONFLICT, got {exc_info.value.conflict_type}"
            )

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id=teacher_id_strategy,
        class_id=class_id_strategy,
        subject_id=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_no_conflict_when_no_existing_entries(
        self,
        tenant_id: int,
        teacher_id: int,
        class_id: int,
        subject_id: int,
        day_of_week: int,
        period_number: int,
        time_range: tuple[time, time],
    ):
        """For any timetable entry with no conflicts, creation SHALL succeed.

        **Validates: Design - Property 13**
        """
        start_time, end_time = time_range
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        created_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number,
            subject_id=subject_id,
            teacher_id=teacher_id,
            start_time=start_time,
            end_time=end_time,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # No conflicts
            mock_repo_instance.check_teacher_conflict.return_value = None
            mock_repo_instance.check_class_section_conflict.return_value = None
            mock_repo_instance.create.return_value = created_entry
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act: Should not raise any exception
            result = service.create_timetable_entry(
                class_id=class_id,
                day_of_week=day_of_week,
                period_number=period_number,
                subject_id=subject_id,
                start_time=start_time,
                end_time=end_time,
                teacher_id=teacher_id,
            )
            
            # Assert
            assert result is not None, "Entry should be created when no conflicts exist"
            assert result.class_id == class_id
            assert result.teacher_id == teacher_id
            assert result.day_of_week == day_of_week
            assert result.period_number == period_number

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id_1=teacher_id_strategy,
        teacher_id_2=teacher_id_strategy,
        class_id=class_id_strategy,
        subject_id=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number_1=period_number_strategy,
        period_number_2=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_no_conflict_different_periods(
        self,
        tenant_id: int,
        teacher_id_1: int,
        teacher_id_2: int,
        class_id: int,
        subject_id: int,
        day_of_week: int,
        period_number_1: int,
        period_number_2: int,
        time_range: tuple[time, time],
    ):
        """For any teacher at different periods on the same day, no conflict SHALL occur.

        **Validates: Design - Property 13**
        """
        # Ensure different periods
        assume(period_number_1 != period_number_2)
        
        start_time, end_time = time_range
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        created_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number_2,
            subject_id=subject_id,
            teacher_id=teacher_id_1,
            start_time=start_time,
            end_time=end_time,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # No conflicts for different periods
            mock_repo_instance.check_teacher_conflict.return_value = None
            mock_repo_instance.check_class_section_conflict.return_value = None
            mock_repo_instance.create.return_value = created_entry
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act: Should succeed
            result = service.create_timetable_entry(
                class_id=class_id,
                day_of_week=day_of_week,
                period_number=period_number_2,
                subject_id=subject_id,
                start_time=start_time,
                end_time=end_time,
                teacher_id=teacher_id_1,
            )
            
            # Assert
            assert result is not None, "Entry should be created for different periods"

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id=teacher_id_strategy,
        class_id=class_id_strategy,
        subject_id=subject_id_strategy,
        day_of_week_1=day_of_week_strategy,
        day_of_week_2=day_of_week_strategy,
        period_number=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_no_conflict_different_days(
        self,
        tenant_id: int,
        teacher_id: int,
        class_id: int,
        subject_id: int,
        day_of_week_1: int,
        day_of_week_2: int,
        period_number: int,
        time_range: tuple[time, time],
    ):
        """For any teacher at the same period on different days, no conflict SHALL occur.

        **Validates: Design - Property 13**
        """
        # Ensure different days
        assume(day_of_week_1 != day_of_week_2)
        
        start_time, end_time = time_range
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        created_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id,
            section_id=None,
            day_of_week=day_of_week_2,
            period_number=period_number,
            subject_id=subject_id,
            teacher_id=teacher_id,
            start_time=start_time,
            end_time=end_time,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # No conflicts for different days
            mock_repo_instance.check_teacher_conflict.return_value = None
            mock_repo_instance.check_class_section_conflict.return_value = None
            mock_repo_instance.create.return_value = created_entry
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act: Should succeed
            result = service.create_timetable_entry(
                class_id=class_id,
                day_of_week=day_of_week_2,
                period_number=period_number,
                subject_id=subject_id,
                start_time=start_time,
                end_time=end_time,
                teacher_id=teacher_id,
            )
            
            # Assert
            assert result is not None, "Entry should be created for different days"

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        subject_id=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number=period_number_strategy,
        time_range=time_range_strategy(),
    )
    @settings(max_examples=100)
    def test_no_teacher_conflict_when_teacher_is_none(
        self,
        tenant_id: int,
        class_id: int,
        subject_id: int,
        day_of_week: int,
        period_number: int,
        time_range: tuple[time, time],
    ):
        """For any timetable entry without a teacher, teacher conflict check SHALL be skipped.

        **Validates: Design - Property 13**
        """
        start_time, end_time = time_range
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        created_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number,
            subject_id=subject_id,
            teacher_id=None,
            start_time=start_time,
            end_time=end_time,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # No class conflict
            mock_repo_instance.check_class_section_conflict.return_value = None
            mock_repo_instance.create.return_value = created_entry
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act: Should succeed without checking teacher conflict
            result = service.create_timetable_entry(
                class_id=class_id,
                day_of_week=day_of_week,
                period_number=period_number,
                subject_id=subject_id,
                start_time=start_time,
                end_time=end_time,
                teacher_id=None,  # No teacher assigned
            )
            
            # Assert
            assert result is not None, "Entry should be created when no teacher is assigned"
            # Verify teacher conflict check was NOT called
            mock_repo_instance.check_teacher_conflict.assert_not_called()

    @given(
        tenant_id=tenant_id_strategy,
        teacher_id=teacher_id_strategy,
        class_id_1=class_id_strategy,
        class_id_2=class_id_strategy,
        subject_id_1=subject_id_strategy,
        subject_id_2=subject_id_strategy,
        day_of_week=day_of_week_strategy,
        period_number=period_number_strategy,
    )
    @settings(max_examples=100)
    def test_overlapping_time_slots_detected_as_conflict(
        self,
        tenant_id: int,
        teacher_id: int,
        class_id_1: int,
        class_id_2: int,
        subject_id_1: int,
        subject_id_2: int,
        day_of_week: int,
        period_number: int,
    ):
        """For any overlapping time slots for the same teacher, conflict SHALL be detected.

        **Validates: Design - Property 13**
        """
        assume(class_id_1 != class_id_2)
        
        # Create overlapping time slots
        # Existing: 9:00 - 10:00
        # New: 9:30 - 10:30 (overlaps)
        existing_start = time(9, 0)
        existing_end = time(10, 0)
        new_start = time(9, 30)
        new_end = time(10, 30)
        
        # Arrange
        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()
        
        existing_entry = MockTimetable(
            tenant_id=tenant_id,
            class_id=class_id_1,
            section_id=None,
            day_of_week=day_of_week,
            period_number=period_number,
            subject_id=subject_id_1,
            teacher_id=teacher_id,
            start_time=existing_start,
            end_time=existing_end,
        )
        
        with patch("app.services.timetable_service.TimetableRepository") as MockRepo:
            mock_repo_instance = MagicMock()
            MockRepo.return_value = mock_repo_instance
            
            # Teacher conflict due to overlapping time
            mock_repo_instance.check_teacher_conflict.return_value = existing_entry
            mock_repo_instance.check_class_section_conflict.return_value = None
            
            service = TimetableService(db=mock_db, tenant_id=tenant_id)
            
            # Act & Assert
            with pytest.raises(TimetableConflictError) as exc_info:
                service.create_timetable_entry(
                    class_id=class_id_2,
                    day_of_week=day_of_week,
                    period_number=period_number + 1,  # Different period but overlapping time
                    subject_id=subject_id_2,
                    start_time=new_start,
                    end_time=new_end,
                    teacher_id=teacher_id,
                )
            
            assert exc_info.value.conflict_type == "TEACHER_CONFLICT"

