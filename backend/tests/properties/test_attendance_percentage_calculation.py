"""Property-based tests for attendance percentage calculation.

**Feature: school-erp-multi-tenancy, Property 10: Attendance Percentage Calculation**
**Validates: Design - Property 10**

Property 10: Attendance Percentage Calculation
*For any* student with attendance records, the calculated attendance percentage SHALL equal
(present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.attendance_service import AttendanceService


# Strategy for non-negative day counts
day_count_strategy = st.integers(min_value=0, max_value=1000)

# Strategy for positive total days (to avoid division by zero)
positive_total_days_strategy = st.integers(min_value=1, max_value=1000)


@st.composite
def valid_attendance_counts(draw):
    """Generate valid attendance counts where sum doesn't exceed total days."""
    total_days = draw(st.integers(min_value=1, max_value=1000))
    # Generate counts that sum to at most total_days
    present_days = draw(st.integers(min_value=0, max_value=total_days))
    remaining = total_days - present_days
    late_days = draw(st.integers(min_value=0, max_value=remaining))
    remaining = remaining - late_days
    half_days = draw(st.integers(min_value=0, max_value=remaining))
    return {
        "present_days": present_days,
        "late_days": late_days,
        "half_days": half_days,
        "total_days": total_days,
    }


class TestAttendancePercentageCalculation:
    """**Feature: school-erp-multi-tenancy, Property 10: Attendance Percentage Calculation**"""

    @given(attendance_data=valid_attendance_counts())
    @settings(max_examples=100)
    def test_attendance_percentage_formula(
        self,
        attendance_data: dict,
    ):
        """For any attendance counts, percentage SHALL equal the formula.

        Formula: (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100

        **Validates: Design - Property 10**
        """
        present_days = attendance_data["present_days"]
        late_days = attendance_data["late_days"]
        half_days = attendance_data["half_days"]
        total_days = attendance_data["total_days"]

        # Act: Calculate using the service method
        result = AttendanceService.calculate_attendance_percentage(
            present_days=present_days,
            late_days=late_days,
            half_days=half_days,
            total_days=total_days,
        )

        # Calculate expected value using the formula
        expected = (present_days + late_days * 0.5 + half_days * 0.5) / total_days * 100
        expected_rounded = round(expected, 2)

        # Assert: Result matches the formula
        assert result == expected_rounded, (
            f"Attendance percentage must equal formula result. "
            f"present={present_days}, late={late_days}, half={half_days}, total={total_days}. "
            f"Expected: {expected_rounded}, Got: {result}"
        )

    @given(
        present_days=day_count_strategy,
        late_days=day_count_strategy,
        half_days=day_count_strategy,
    )
    @settings(max_examples=100)
    def test_attendance_percentage_zero_total_days_returns_zero(
        self,
        present_days: int,
        late_days: int,
        half_days: int,
    ):
        """For any attendance counts with zero total days, percentage SHALL be 0.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with zero total days
        result = AttendanceService.calculate_attendance_percentage(
            present_days=present_days,
            late_days=late_days,
            half_days=half_days,
            total_days=0,
        )

        # Assert: Result is 0.0 for zero total days
        assert result == 0.0, (
            f"Attendance percentage must be 0.0 when total_days is 0. "
            f"Got: {result}"
        )

    @given(
        present_days=day_count_strategy,
        late_days=day_count_strategy,
        half_days=day_count_strategy,
        negative_total=st.integers(min_value=-1000, max_value=-1),
    )
    @settings(max_examples=100)
    def test_attendance_percentage_negative_total_days_returns_zero(
        self,
        present_days: int,
        late_days: int,
        half_days: int,
        negative_total: int,
    ):
        """For any attendance counts with negative total days, percentage SHALL be 0.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with negative total days
        result = AttendanceService.calculate_attendance_percentage(
            present_days=present_days,
            late_days=late_days,
            half_days=half_days,
            total_days=negative_total,
        )

        # Assert: Result is 0.0 for negative total days
        assert result == 0.0, (
            f"Attendance percentage must be 0.0 when total_days is negative. "
            f"Got: {result}"
        )

    @given(total_days=positive_total_days_strategy)
    @settings(max_examples=100)
    def test_attendance_percentage_all_present_equals_100(
        self,
        total_days: int,
    ):
        """For any total days where all days are present, percentage SHALL be 100.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with all present days
        result = AttendanceService.calculate_attendance_percentage(
            present_days=total_days,
            late_days=0,
            half_days=0,
            total_days=total_days,
        )

        # Assert: Result is 100.0
        assert result == 100.0, (
            f"Attendance percentage must be 100.0 when all days are present. "
            f"total_days={total_days}, Got: {result}"
        )

    @given(total_days=positive_total_days_strategy)
    @settings(max_examples=100)
    def test_attendance_percentage_all_late_equals_50(
        self,
        total_days: int,
    ):
        """For any total days where all days are late, percentage SHALL be 50.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with all late days
        result = AttendanceService.calculate_attendance_percentage(
            present_days=0,
            late_days=total_days,
            half_days=0,
            total_days=total_days,
        )

        # Assert: Result is 50.0
        assert result == 50.0, (
            f"Attendance percentage must be 50.0 when all days are late. "
            f"total_days={total_days}, Got: {result}"
        )

    @given(total_days=positive_total_days_strategy)
    @settings(max_examples=100)
    def test_attendance_percentage_all_half_day_equals_50(
        self,
        total_days: int,
    ):
        """For any total days where all days are half days, percentage SHALL be 50.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with all half days
        result = AttendanceService.calculate_attendance_percentage(
            present_days=0,
            late_days=0,
            half_days=total_days,
            total_days=total_days,
        )

        # Assert: Result is 50.0
        assert result == 50.0, (
            f"Attendance percentage must be 50.0 when all days are half days. "
            f"total_days={total_days}, Got: {result}"
        )

    @given(total_days=positive_total_days_strategy)
    @settings(max_examples=100)
    def test_attendance_percentage_no_attendance_equals_zero(
        self,
        total_days: int,
    ):
        """For any total days with no attendance, percentage SHALL be 0.0.

        **Validates: Design - Property 10**
        """
        # Act: Calculate with no attendance
        result = AttendanceService.calculate_attendance_percentage(
            present_days=0,
            late_days=0,
            half_days=0,
            total_days=total_days,
        )

        # Assert: Result is 0.0
        assert result == 0.0, (
            f"Attendance percentage must be 0.0 when no attendance. "
            f"total_days={total_days}, Got: {result}"
        )

    @given(attendance_data=valid_attendance_counts())
    @settings(max_examples=100)
    def test_attendance_percentage_is_bounded(
        self,
        attendance_data: dict,
    ):
        """For any valid attendance counts, percentage SHALL be between 0 and 100.

        **Validates: Design - Property 10**
        """
        present_days = attendance_data["present_days"]
        late_days = attendance_data["late_days"]
        half_days = attendance_data["half_days"]
        total_days = attendance_data["total_days"]

        # Act: Calculate percentage
        result = AttendanceService.calculate_attendance_percentage(
            present_days=present_days,
            late_days=late_days,
            half_days=half_days,
            total_days=total_days,
        )

        # Assert: Result is bounded between 0 and 100
        assert 0.0 <= result <= 100.0, (
            f"Attendance percentage must be between 0 and 100. "
            f"present={present_days}, late={late_days}, half={half_days}, total={total_days}. "
            f"Got: {result}"
        )

    @given(attendance_data=valid_attendance_counts())
    @settings(max_examples=100)
    def test_attendance_percentage_result_has_two_decimal_places(
        self,
        attendance_data: dict,
    ):
        """For any attendance calculation, result SHALL be rounded to 2 decimal places.

        **Validates: Design - Property 10**
        """
        present_days = attendance_data["present_days"]
        late_days = attendance_data["late_days"]
        half_days = attendance_data["half_days"]
        total_days = attendance_data["total_days"]

        # Act: Calculate percentage
        result = AttendanceService.calculate_attendance_percentage(
            present_days=present_days,
            late_days=late_days,
            half_days=half_days,
            total_days=total_days,
        )

        # Assert: Result is rounded to 2 decimal places
        assert result == round(result, 2), (
            f"Attendance percentage must be rounded to 2 decimal places. "
            f"Got: {result}"
        )
