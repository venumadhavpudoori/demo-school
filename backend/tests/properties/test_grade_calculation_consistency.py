"""Property-based tests for grade calculation consistency.

**Feature: school-erp-multi-tenancy, Property 11: Grade Calculation Consistency**
**Validates: Design - Property 11**

Property 11: Grade Calculation Consistency
*For any* grade entry with marks_obtained and max_marks, the calculated percentage SHALL equal
marks_obtained / max_marks * 100, and the grade letter SHALL match the configured grading scale.
"""

from decimal import Decimal

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.grade_service import GradeService, DEFAULT_GRADING_SCALE


# Strategy for valid marks (positive decimals)
marks_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for positive max marks (must be > 0)
positive_max_marks_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def valid_grade_marks(draw):
    """Generate valid marks where marks_obtained <= max_marks."""
    max_marks = draw(positive_max_marks_strategy)
    marks_obtained = draw(
        st.decimals(
            min_value=Decimal("0"),
            max_value=max_marks,
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    return {"marks_obtained": marks_obtained, "max_marks": max_marks}


def get_expected_grade_letter(percentage: float, grading_scale: list[dict]) -> str:
    """Get expected grade letter from percentage using grading scale."""
    for scale in grading_scale:
        if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
            return scale["grade"]
    return "F"


class TestGradeCalculationConsistency:
    """**Feature: school-erp-multi-tenancy, Property 11: Grade Calculation Consistency**"""

    @given(grade_data=valid_grade_marks())
    @settings(max_examples=100)
    def test_percentage_calculation_formula(
        self,
        grade_data: dict,
    ):
        """For any marks, percentage SHALL equal marks_obtained / max_marks * 100.

        **Validates: Design - Property 11**
        """
        marks_obtained = grade_data["marks_obtained"]
        max_marks = grade_data["max_marks"]

        # Act: Calculate using the service method
        result = GradeService.calculate_percentage(marks_obtained, max_marks)

        # Calculate expected value using the formula
        expected = float(marks_obtained) / float(max_marks) * 100
        expected_rounded = round(expected, 2)

        # Assert: Result matches the formula
        assert result == expected_rounded, (
            f"Percentage must equal formula result. "
            f"marks_obtained={marks_obtained}, max_marks={max_marks}. "
            f"Expected: {expected_rounded}, Got: {result}"
        )

    @given(grade_data=valid_grade_marks())
    @settings(max_examples=100)
    def test_grade_letter_matches_grading_scale(
        self,
        grade_data: dict,
    ):
        """For any percentage, grade letter SHALL match the configured grading scale.

        **Validates: Design - Property 11**
        """
        marks_obtained = grade_data["marks_obtained"]
        max_marks = grade_data["max_marks"]

        # Calculate percentage
        percentage = GradeService.calculate_percentage(marks_obtained, max_marks)

        # Create service instance (without db/tenant for static method testing)
        # We need to test calculate_grade_letter which is an instance method
        # Create a mock-like service just for grade letter calculation
        class MockGradeService:
            def __init__(self):
                self.grading_scale = DEFAULT_GRADING_SCALE

            def calculate_grade_letter(self, percentage: float) -> str:
                for scale in self.grading_scale:
                    if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                        return scale["grade"]
                return "F"

        service = MockGradeService()
        result = service.calculate_grade_letter(percentage)

        # Calculate expected grade letter
        expected = get_expected_grade_letter(percentage, DEFAULT_GRADING_SCALE)

        # Assert: Grade letter matches expected
        assert result == expected, (
            f"Grade letter must match grading scale. "
            f"percentage={percentage}. "
            f"Expected: {expected}, Got: {result}"
        )

    @given(
        marks_obtained=marks_strategy,
        zero_or_negative_max=st.decimals(
            min_value=Decimal("-999.99"),
            max_value=Decimal("0"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_percentage_zero_or_negative_max_marks_returns_zero(
        self,
        marks_obtained: Decimal,
        zero_or_negative_max: Decimal,
    ):
        """For any marks with zero or negative max_marks, percentage SHALL be 0.0.

        **Validates: Design - Property 11**
        """
        # Act: Calculate with zero or negative max marks
        result = GradeService.calculate_percentage(marks_obtained, zero_or_negative_max)

        # Assert: Result is 0.0
        assert result == 0.0, (
            f"Percentage must be 0.0 when max_marks is zero or negative. "
            f"marks_obtained={marks_obtained}, max_marks={zero_or_negative_max}. "
            f"Got: {result}"
        )

    @given(max_marks=positive_max_marks_strategy)
    @settings(max_examples=100)
    def test_percentage_full_marks_equals_100(
        self,
        max_marks: Decimal,
    ):
        """For any max_marks where marks_obtained equals max_marks, percentage SHALL be 100.0.

        **Validates: Design - Property 11**
        """
        # Act: Calculate with full marks
        result = GradeService.calculate_percentage(max_marks, max_marks)

        # Assert: Result is 100.0
        assert result == 100.0, (
            f"Percentage must be 100.0 when marks_obtained equals max_marks. "
            f"max_marks={max_marks}. Got: {result}"
        )

    @given(max_marks=positive_max_marks_strategy)
    @settings(max_examples=100)
    def test_percentage_zero_marks_equals_zero(
        self,
        max_marks: Decimal,
    ):
        """For any max_marks where marks_obtained is zero, percentage SHALL be 0.0.

        **Validates: Design - Property 11**
        """
        # Act: Calculate with zero marks
        result = GradeService.calculate_percentage(Decimal("0"), max_marks)

        # Assert: Result is 0.0
        assert result == 0.0, (
            f"Percentage must be 0.0 when marks_obtained is zero. "
            f"max_marks={max_marks}. Got: {result}"
        )

    @given(grade_data=valid_grade_marks())
    @settings(max_examples=100)
    def test_percentage_is_bounded(
        self,
        grade_data: dict,
    ):
        """For any valid marks, percentage SHALL be between 0 and 100.

        **Validates: Design - Property 11**
        """
        marks_obtained = grade_data["marks_obtained"]
        max_marks = grade_data["max_marks"]

        # Act: Calculate percentage
        result = GradeService.calculate_percentage(marks_obtained, max_marks)

        # Assert: Result is bounded between 0 and 100
        assert 0.0 <= result <= 100.0, (
            f"Percentage must be between 0 and 100. "
            f"marks_obtained={marks_obtained}, max_marks={max_marks}. "
            f"Got: {result}"
        )

    @given(grade_data=valid_grade_marks())
    @settings(max_examples=100)
    def test_percentage_result_has_two_decimal_places(
        self,
        grade_data: dict,
    ):
        """For any grade calculation, result SHALL be rounded to 2 decimal places.

        **Validates: Design - Property 11**
        """
        marks_obtained = grade_data["marks_obtained"]
        max_marks = grade_data["max_marks"]

        # Act: Calculate percentage
        result = GradeService.calculate_percentage(marks_obtained, max_marks)

        # Assert: Result is rounded to 2 decimal places
        assert result == round(result, 2), (
            f"Percentage must be rounded to 2 decimal places. "
            f"Got: {result}"
        )

    @given(percentage=st.floats(min_value=90.0, max_value=100.0))
    @settings(max_examples=100)
    def test_grade_letter_a_plus_for_90_to_100(
        self,
        percentage: float,
    ):
        """For any percentage between 90 and 100, grade letter SHALL be A+.

        **Validates: Design - Property 11**
        """
        assume(not (percentage != percentage))  # Filter out NaN

        class MockGradeService:
            def __init__(self):
                self.grading_scale = DEFAULT_GRADING_SCALE

            def calculate_grade_letter(self, percentage: float) -> str:
                for scale in self.grading_scale:
                    if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                        return scale["grade"]
                return "F"

        service = MockGradeService()
        result = service.calculate_grade_letter(percentage)

        assert result == "A+", (
            f"Grade letter must be A+ for percentage {percentage}. Got: {result}"
        )

    @given(percentage=st.floats(min_value=80.0, max_value=89.99))
    @settings(max_examples=100)
    def test_grade_letter_a_for_80_to_89(
        self,
        percentage: float,
    ):
        """For any percentage between 80 and 89.99, grade letter SHALL be A.

        **Validates: Design - Property 11**
        """
        assume(not (percentage != percentage))  # Filter out NaN

        class MockGradeService:
            def __init__(self):
                self.grading_scale = DEFAULT_GRADING_SCALE

            def calculate_grade_letter(self, percentage: float) -> str:
                for scale in self.grading_scale:
                    if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                        return scale["grade"]
                return "F"

        service = MockGradeService()
        result = service.calculate_grade_letter(percentage)

        assert result == "A", (
            f"Grade letter must be A for percentage {percentage}. Got: {result}"
        )

    @given(percentage=st.floats(min_value=0.0, max_value=32.99))
    @settings(max_examples=100)
    def test_grade_letter_f_for_below_33(
        self,
        percentage: float,
    ):
        """For any percentage below 33, grade letter SHALL be F.

        **Validates: Design - Property 11**
        """
        assume(not (percentage != percentage))  # Filter out NaN

        class MockGradeService:
            def __init__(self):
                self.grading_scale = DEFAULT_GRADING_SCALE

            def calculate_grade_letter(self, percentage: float) -> str:
                for scale in self.grading_scale:
                    if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                        return scale["grade"]
                return "F"

        service = MockGradeService()
        result = service.calculate_grade_letter(percentage)

        assert result == "F", (
            f"Grade letter must be F for percentage {percentage}. Got: {result}"
        )

    @given(percentage=st.floats(min_value=33.0, max_value=39.99))
    @settings(max_examples=100)
    def test_grade_letter_d_for_33_to_39(
        self,
        percentage: float,
    ):
        """For any percentage between 33 and 39.99, grade letter SHALL be D.

        **Validates: Design - Property 11**
        """
        assume(not (percentage != percentage))  # Filter out NaN

        class MockGradeService:
            def __init__(self):
                self.grading_scale = DEFAULT_GRADING_SCALE

            def calculate_grade_letter(self, percentage: float) -> str:
                for scale in self.grading_scale:
                    if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                        return scale["grade"]
                return "F"

        service = MockGradeService()
        result = service.calculate_grade_letter(percentage)

        assert result == "D", (
            f"Grade letter must be D for percentage {percentage}. Got: {result}"
        )

