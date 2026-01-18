"""Property-based tests for fee payment status update.

**Feature: school-erp-multi-tenancy, Property 12: Fee Payment Status Update**
**Validates: Design - Property 12**

Property 12: Fee Payment Status Update
*For any* fee record, after recording a payment, the fee status SHALL be 'paid' if
paid_amount >= amount, 'partial' if 0 < paid_amount < amount, or 'pending' if paid_amount = 0.
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.fee import FeeStatus
from app.repositories.fee import FeeRepository
from app.services.fee_service import FeeService


# Strategy for positive fee amounts
positive_amount_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("99999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for non-negative paid amounts
non_negative_amount_strategy = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("99999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def valid_fee_payment_scenario(draw):
    """Generate valid fee payment scenarios with total amount and paid amount."""
    total_amount = draw(positive_amount_strategy)
    # Paid amount can be 0 to total_amount (or slightly more for edge cases)
    paid_amount = draw(
        st.decimals(
            min_value=Decimal("0.00"),
            max_value=total_amount + Decimal("100.00"),  # Allow overpayment scenarios
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    return {"total_amount": total_amount, "paid_amount": paid_amount}


@st.composite
def paid_in_full_scenario(draw):
    """Generate scenarios where paid_amount >= total_amount."""
    total_amount = draw(positive_amount_strategy)
    # Paid amount is at least total_amount
    extra = draw(
        st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("100.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    paid_amount = total_amount + extra
    return {"total_amount": total_amount, "paid_amount": paid_amount}


@st.composite
def partial_payment_scenario(draw):
    """Generate scenarios where 0 < paid_amount < total_amount."""
    total_amount = draw(
        st.decimals(
            min_value=Decimal("1.00"),  # Ensure room for partial payment
            max_value=Decimal("99999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    # Paid amount is between 0.01 and total_amount - 0.01
    paid_amount = draw(
        st.decimals(
            min_value=Decimal("0.01"),
            max_value=total_amount - Decimal("0.01"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    return {"total_amount": total_amount, "paid_amount": paid_amount}


class TestFeePaymentStatusUpdate:
    """**Feature: school-erp-multi-tenancy, Property 12: Fee Payment Status Update**"""

    @given(scenario=paid_in_full_scenario())
    @settings(max_examples=100)
    def test_fee_status_paid_when_paid_amount_equals_total(
        self,
        scenario: dict,
    ):
        """For any fee where paid_amount >= total_amount, status SHALL be 'paid'.

        **Validates: Design - Property 12**
        """
        total_amount = scenario["total_amount"]
        paid_amount = scenario["paid_amount"]

        # Act: Calculate status using repository method
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PAID
        assert result == FeeStatus.PAID, (
            f"Fee status must be 'paid' when paid_amount >= total_amount. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PAID}, Got: {result}"
        )

    @given(scenario=partial_payment_scenario())
    @settings(max_examples=100)
    def test_fee_status_partial_when_paid_amount_between_zero_and_total(
        self,
        scenario: dict,
    ):
        """For any fee where 0 < paid_amount < total_amount, status SHALL be 'partial'.

        **Validates: Design - Property 12**
        """
        total_amount = scenario["total_amount"]
        paid_amount = scenario["paid_amount"]

        # Act: Calculate status using repository method
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PARTIAL
        assert result == FeeStatus.PARTIAL, (
            f"Fee status must be 'partial' when 0 < paid_amount < total_amount. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PARTIAL}, Got: {result}"
        )

    @given(total_amount=positive_amount_strategy)
    @settings(max_examples=100)
    def test_fee_status_pending_when_paid_amount_is_zero(
        self,
        total_amount: Decimal,
    ):
        """For any fee where paid_amount = 0, status SHALL be 'pending'.

        **Validates: Design - Property 12**
        """
        paid_amount = Decimal("0.00")

        # Act: Calculate status using repository method
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PENDING
        assert result == FeeStatus.PENDING, (
            f"Fee status must be 'pending' when paid_amount = 0. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PENDING}, Got: {result}"
        )

    @given(scenario=valid_fee_payment_scenario())
    @settings(max_examples=100)
    def test_fee_service_status_calculation_matches_repository(
        self,
        scenario: dict,
    ):
        """For any fee, FeeService and FeeRepository status calculations SHALL match.

        **Validates: Design - Property 12**
        """
        total_amount = scenario["total_amount"]
        paid_amount = scenario["paid_amount"]

        # Act: Calculate status using both methods
        repo_result = FeeRepository._calculate_fee_status(paid_amount, total_amount)
        service_result = FeeService._calculate_fee_status(paid_amount, total_amount)

        # Assert: Both methods return the same status
        assert repo_result == service_result, (
            f"FeeService and FeeRepository status calculations must match. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Repository: {repo_result}, Service: {service_result}"
        )

    @given(total_amount=positive_amount_strategy)
    @settings(max_examples=100)
    def test_fee_status_paid_when_exact_payment(
        self,
        total_amount: Decimal,
    ):
        """For any fee where paid_amount exactly equals total_amount, status SHALL be 'paid'.

        **Validates: Design - Property 12**
        """
        paid_amount = total_amount

        # Act: Calculate status
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PAID
        assert result == FeeStatus.PAID, (
            f"Fee status must be 'paid' when paid_amount exactly equals total_amount. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PAID}, Got: {result}"
        )

    @given(
        total_amount=positive_amount_strategy,
        overpayment=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("1000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_fee_status_paid_when_overpayment(
        self,
        total_amount: Decimal,
        overpayment: Decimal,
    ):
        """For any fee where paid_amount > total_amount, status SHALL be 'paid'.

        **Validates: Design - Property 12**
        """
        paid_amount = total_amount + overpayment

        # Act: Calculate status
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PAID
        assert result == FeeStatus.PAID, (
            f"Fee status must be 'paid' when paid_amount > total_amount. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PAID}, Got: {result}"
        )

    @given(scenario=valid_fee_payment_scenario())
    @settings(max_examples=100)
    def test_fee_status_is_valid_enum_value(
        self,
        scenario: dict,
    ):
        """For any fee payment scenario, status SHALL be a valid FeeStatus enum value.

        **Validates: Design - Property 12**
        """
        total_amount = scenario["total_amount"]
        paid_amount = scenario["paid_amount"]

        # Act: Calculate status
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Result is a valid FeeStatus
        assert isinstance(result, FeeStatus), (
            f"Fee status must be a FeeStatus enum value. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Got type: {type(result)}"
        )
        assert result in [FeeStatus.PENDING, FeeStatus.PARTIAL, FeeStatus.PAID], (
            f"Fee status must be one of PENDING, PARTIAL, or PAID. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Got: {result}"
        )

    @given(scenario=partial_payment_scenario())
    @settings(max_examples=100)
    def test_fee_status_partial_for_percentage_payments(
        self,
        scenario: dict,
    ):
        """For any partial payment (between 0 and total), status SHALL be 'partial'.

        **Validates: Design - Property 12**
        """
        total_amount = scenario["total_amount"]
        paid_amount = scenario["paid_amount"]

        # Act: Calculate status
        result = FeeRepository._calculate_fee_status(paid_amount, total_amount)

        # Assert: Status is PARTIAL
        assert result == FeeStatus.PARTIAL, (
            f"Fee status must be 'partial' for partial payments. "
            f"paid_amount={paid_amount}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PARTIAL}, Got: {result}"
        )

    @given(
        total_amount=st.decimals(
            min_value=Decimal("1.00"),
            max_value=Decimal("99999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        small_payment=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("0.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_fee_status_partial_for_small_payments(
        self,
        total_amount: Decimal,
        small_payment: Decimal,
    ):
        """For any small payment (less than $1), status SHALL be 'partial' if total > payment.

        **Validates: Design - Property 12**
        """
        # total_amount is always >= 1.00, small_payment is always <= 0.99
        # So total_amount > small_payment is always true

        # Act: Calculate status
        result = FeeRepository._calculate_fee_status(small_payment, total_amount)

        # Assert: Status is PARTIAL
        assert result == FeeStatus.PARTIAL, (
            f"Fee status must be 'partial' for small payments. "
            f"paid_amount={small_payment}, total_amount={total_amount}. "
            f"Expected: {FeeStatus.PARTIAL}, Got: {result}"
        )

