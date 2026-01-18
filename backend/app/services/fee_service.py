"""Fee service for business logic operations.

This module provides the FeeService class that handles all business logic
related to fee management including creation, payments, and reporting.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.fee import Fee, FeeStatus
from app.repositories.fee import FeeRepository


class FeeServiceError(Exception):
    """Base exception for fee service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class FeeNotFoundError(FeeServiceError):
    """Raised when a fee record is not found."""

    def __init__(self, fee_id: int):
        super().__init__(
            message=f"Fee record with ID {fee_id} not found",
            code="FEE_NOT_FOUND",
        )


class InvalidPaymentError(FeeServiceError):
    """Raised when payment data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_PAYMENT",
        )


class InvalidFeeDataError(FeeServiceError):
    """Raised when fee data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_FEE_DATA",
        )


class FeeService:
    """Service class for fee business logic.

    Handles all business operations related to fees including
    creation, payments, and reporting.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the fee service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = FeeRepository(db, tenant_id)

    def create_fee(
        self,
        student_id: int,
        fee_type: str,
        amount: Decimal,
        due_date: date,
        academic_year: str,
    ) -> Fee:
        """Create a new fee record.

        Args:
            student_id: The student ID.
            fee_type: Type of fee (e.g., "tuition", "transport", "library").
            amount: The fee amount.
            due_date: The due date for payment.
            academic_year: The academic year (e.g., "2024-2025").

        Returns:
            The created Fee object.

        Raises:
            InvalidFeeDataError: If fee data is invalid.
        """
        if amount <= Decimal("0.00"):
            raise InvalidFeeDataError("Fee amount must be greater than zero")

        if not fee_type or not fee_type.strip():
            raise InvalidFeeDataError("Fee type is required")

        if not academic_year or not academic_year.strip():
            raise InvalidFeeDataError("Academic year is required")

        fee = self.repository.create({
            "student_id": student_id,
            "fee_type": fee_type.strip(),
            "amount": amount,
            "due_date": due_date,
            "paid_amount": Decimal("0.00"),
            "status": FeeStatus.PENDING,
            "academic_year": academic_year.strip(),
        })

        return fee

    def get_fee(self, fee_id: int) -> Fee:
        """Get a fee record by ID.

        Args:
            fee_id: The fee record ID.

        Returns:
            The Fee object.

        Raises:
            FeeNotFoundError: If fee not found.
        """
        fee = self.repository.get_by_id_with_relations(fee_id)
        if fee is None:
            raise FeeNotFoundError(fee_id)
        return fee

    def update_fee(
        self,
        fee_id: int,
        fee_type: str | None = None,
        amount: Decimal | None = None,
        due_date: date | None = None,
        academic_year: str | None = None,
        status: FeeStatus | None = None,
    ) -> Fee:
        """Update a fee record.

        Args:
            fee_id: The fee record ID.
            fee_type: Optional new fee type.
            amount: Optional new amount.
            due_date: Optional new due date.
            academic_year: Optional new academic year.
            status: Optional new status.

        Returns:
            The updated Fee object.

        Raises:
            FeeNotFoundError: If fee not found.
            InvalidFeeDataError: If update data is invalid.
        """
        fee = self.repository.get_by_id(fee_id)
        if fee is None:
            raise FeeNotFoundError(fee_id)

        if amount is not None:
            if amount <= Decimal("0.00"):
                raise InvalidFeeDataError("Fee amount must be greater than zero")
            fee.amount = amount
            # Recalculate status if amount changed
            fee.status = self._calculate_fee_status(fee.paid_amount, fee.amount)

        if fee_type is not None:
            if not fee_type.strip():
                raise InvalidFeeDataError("Fee type cannot be empty")
            fee.fee_type = fee_type.strip()

        if due_date is not None:
            fee.due_date = due_date

        if academic_year is not None:
            if not academic_year.strip():
                raise InvalidFeeDataError("Academic year cannot be empty")
            fee.academic_year = academic_year.strip()

        if status is not None:
            fee.status = status

        self.db.commit()
        self.db.refresh(fee)

        return fee

    def delete_fee(self, fee_id: int) -> bool:
        """Delete a fee record.

        Args:
            fee_id: The fee record ID.

        Returns:
            True if deleted successfully.

        Raises:
            FeeNotFoundError: If fee not found.
        """
        fee = self.repository.get_by_id(fee_id)
        if fee is None:
            raise FeeNotFoundError(fee_id)

        self.db.delete(fee)
        self.db.commit()
        return True

    def record_payment(
        self,
        fee_id: int,
        amount: Decimal,
        payment_method: str | None = None,
        transaction_id: str | None = None,
        payment_date: date | None = None,
    ) -> dict[str, Any]:
        """Record a payment for a fee.

        Updates the fee status based on the payment amount:
        - 'paid' if paid_amount >= amount
        - 'partial' if 0 < paid_amount < amount
        - 'pending' if paid_amount = 0

        Args:
            fee_id: The fee ID.
            amount: The payment amount.
            payment_method: Optional payment method description.
            transaction_id: Optional transaction reference ID.
            payment_date: Optional payment date (defaults to today).

        Returns:
            Dictionary with payment details and updated fee info.

        Raises:
            FeeNotFoundError: If fee not found.
            InvalidPaymentError: If payment data is invalid.
        """
        fee = self.repository.get_by_id(fee_id)
        if fee is None:
            raise FeeNotFoundError(fee_id)

        if amount <= Decimal("0.00"):
            raise InvalidPaymentError("Payment amount must be greater than zero")

        # Check if payment would exceed total amount
        remaining = fee.amount - fee.paid_amount
        if amount > remaining:
            raise InvalidPaymentError(
                f"Payment amount ({amount}) exceeds remaining balance ({remaining})"
            )

        if payment_date is None:
            payment_date = date.today()

        # Record the payment
        previous_status = fee.status
        previous_paid = fee.paid_amount

        updated_fee = self.repository.record_payment(
            fee_id=fee_id,
            payment_amount=amount,
            payment_date=payment_date,
        )

        if updated_fee is None:
            raise FeeNotFoundError(fee_id)

        return {
            "fee_id": updated_fee.id,
            "student_id": updated_fee.student_id,
            "fee_type": updated_fee.fee_type,
            "total_amount": float(updated_fee.amount),
            "previous_paid": float(previous_paid),
            "payment_amount": float(amount),
            "new_paid_amount": float(updated_fee.paid_amount),
            "remaining_balance": float(updated_fee.amount - updated_fee.paid_amount),
            "previous_status": previous_status.value,
            "new_status": updated_fee.status.value,
            "payment_date": payment_date.isoformat(),
            "payment_method": payment_method,
            "transaction_id": transaction_id,
        }

    def list_fees(
        self,
        student_id: int | None = None,
        status: FeeStatus | list[FeeStatus] | None = None,
        fee_type: str | None = None,
        academic_year: str | None = None,
        due_date_start: date | None = None,
        due_date_end: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List fee records with filtering and pagination.

        Args:
            student_id: Optional student ID filter.
            status: Optional status filter (single or list).
            fee_type: Optional fee type filter.
            academic_year: Optional academic year filter.
            due_date_start: Optional start date filter for due date.
            due_date_end: Optional end date filter for due date.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_with_filters(
            student_id=student_id,
            status=status,
            fee_type=fee_type,
            academic_year=academic_year,
            due_date_start=due_date_start,
            due_date_end=due_date_end,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                {
                    "id": fee.id,
                    "student_id": fee.student_id,
                    "student_name": self._get_student_name(fee),
                    "fee_type": fee.fee_type,
                    "amount": float(fee.amount),
                    "paid_amount": float(fee.paid_amount),
                    "remaining": float(fee.amount - fee.paid_amount),
                    "due_date": fee.due_date.isoformat(),
                    "payment_date": fee.payment_date.isoformat() if fee.payment_date else None,
                    "status": fee.status.value,
                    "academic_year": fee.academic_year,
                }
                for fee in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def get_pending_fees(
        self,
        student_id: int | None = None,
        academic_year: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get all pending, partial, and overdue fees.

        Args:
            student_id: Optional student ID filter.
            academic_year: Optional academic year filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with pending fees and pagination metadata.
        """
        result = self.repository.get_pending_fees(
            student_id=student_id,
            academic_year=academic_year,
            page=page,
            page_size=page_size,
        )

        # Calculate totals
        total_pending_amount = Decimal("0.00")
        for fee in result.items:
            total_pending_amount += (fee.amount - fee.paid_amount)

        return {
            "items": [
                {
                    "id": fee.id,
                    "student_id": fee.student_id,
                    "student_name": self._get_student_name(fee),
                    "fee_type": fee.fee_type,
                    "amount": float(fee.amount),
                    "paid_amount": float(fee.paid_amount),
                    "remaining": float(fee.amount - fee.paid_amount),
                    "due_date": fee.due_date.isoformat(),
                    "status": fee.status.value,
                    "academic_year": fee.academic_year,
                }
                for fee in result.items
            ],
            "total_pending_amount": float(total_pending_amount),
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def get_fee_collection_report(
        self,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Generate fee collection report.

        Args:
            academic_year: Optional academic year filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            Dictionary with comprehensive fee collection statistics.
        """
        summary = self.repository.get_fee_collection_summary(
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "academic_year": academic_year,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            **summary,
        }

    def get_student_fee_summary(self, student_id: int) -> dict[str, Any]:
        """Get fee summary for a specific student.

        Args:
            student_id: The student ID.

        Returns:
            Dictionary with student fee statistics.
        """
        return self.repository.get_student_fee_summary(student_id)

    def mark_overdue_fees(self, as_of_date: date | None = None) -> int:
        """Mark all past-due pending fees as overdue.

        Args:
            as_of_date: Date to check against (defaults to today).

        Returns:
            Number of fees marked as overdue.
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get all pending/partial fees that are past due
        result = self.repository.get_overdue_fees(
            as_of_date=as_of_date,
            page=1,
            page_size=10000,  # Get all
        )

        count = 0
        for fee in result.items:
            if fee.status in [FeeStatus.PENDING, FeeStatus.PARTIAL]:
                fee.status = FeeStatus.OVERDUE
                count += 1

        if count > 0:
            self.db.commit()

        return count

    def waive_fee(self, fee_id: int, reason: str | None = None) -> Fee:
        """Waive a fee (mark as waived).

        Args:
            fee_id: The fee ID.
            reason: Optional reason for waiving.

        Returns:
            The updated Fee object.

        Raises:
            FeeNotFoundError: If fee not found.
        """
        fee = self.repository.get_by_id(fee_id)
        if fee is None:
            raise FeeNotFoundError(fee_id)

        fee.status = FeeStatus.WAIVED
        self.db.commit()
        self.db.refresh(fee)

        return fee

    @staticmethod
    def _calculate_fee_status(paid_amount: Decimal, total_amount: Decimal) -> FeeStatus:
        """Calculate fee status based on paid amount.

        Args:
            paid_amount: Amount paid so far.
            total_amount: Total fee amount.

        Returns:
            The appropriate FeeStatus.
        """
        if paid_amount >= total_amount:
            return FeeStatus.PAID
        elif paid_amount > Decimal("0.00"):
            return FeeStatus.PARTIAL
        else:
            return FeeStatus.PENDING

    @staticmethod
    def _get_student_name(fee: Fee) -> str | None:
        """Get student name from fee record.

        Args:
            fee: The Fee object with student relation.

        Returns:
            Student name or None if not available.
        """
        if fee.student and fee.student.user:
            first_name = fee.student.user.profile_data.get("first_name", "")
            last_name = fee.student.user.profile_data.get("last_name", "")
            return f"{first_name} {last_name}".strip() or None
        return None
