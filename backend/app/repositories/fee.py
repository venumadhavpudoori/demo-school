"""Fee repository for data access operations.

This module provides the FeeRepository class that handles all database
operations related to fee records with automatic tenant filtering.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.fee import Fee, FeeStatus
from app.repositories.base import PaginatedResult, TenantAwareRepository


class FeeRepository(TenantAwareRepository[Fee]):
    """Repository for fee data access operations.

    Extends TenantAwareRepository to provide fee-specific
    query methods with automatic tenant filtering.
    """

    model = Fee

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the fee repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_by_id_with_relations(self, fee_id: int) -> Fee | None:
        """Get fee record by ID with related entities loaded.

        Args:
            fee_id: The fee record ID.

        Returns:
            The Fee object with relations or None if not found.
        """
        stmt = (
            self.get_base_query()
            .where(Fee.id == fee_id)
            .options(joinedload(Fee.student))
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_student(
        self,
        student_id: int,
        status: FeeStatus | None = None,
        academic_year: str | None = None,
    ) -> list[Fee]:
        """Get all fee records for a specific student.

        Args:
            student_id: The student ID.
            status: Optional status filter.
            academic_year: Optional academic year filter.

        Returns:
            List of Fee objects.
        """
        query = self.get_base_query().where(Fee.student_id == student_id)

        if status is not None:
            query = query.where(Fee.status == status)
        if academic_year is not None:
            query = query.where(Fee.academic_year == academic_year)

        query = query.order_by(Fee.due_date.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def list_with_filters(
        self,
        student_id: int | None = None,
        status: FeeStatus | list[FeeStatus] | None = None,
        fee_type: str | None = None,
        academic_year: str | None = None,
        due_date_start: date | None = None,
        due_date_end: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Fee]:
        """List fee records with advanced filtering.

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
            PaginatedResult containing fee records.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query()

        # Apply filters
        if student_id is not None:
            query = query.where(Fee.student_id == student_id)
        if status is not None:
            if isinstance(status, list):
                query = query.where(Fee.status.in_(status))
            else:
                query = query.where(Fee.status == status)
        if fee_type is not None:
            query = query.where(Fee.fee_type == fee_type)
        if academic_year is not None:
            query = query.where(Fee.academic_year == academic_year)
        if due_date_start is not None:
            query = query.where(Fee.due_date >= due_date_start)
        if due_date_end is not None:
            query = query.where(Fee.due_date <= due_date_end)

        # Order by due date descending
        query = query.order_by(Fee.due_date.desc(), Fee.id.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(joinedload(Fee.student))

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_pending_fees(
        self,
        student_id: int | None = None,
        academic_year: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Fee]:
        """Get all pending and partial fees.

        Args:
            student_id: Optional student ID filter.
            academic_year: Optional academic year filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing pending fee records.
        """
        return self.list_with_filters(
            student_id=student_id,
            status=[FeeStatus.PENDING, FeeStatus.PARTIAL, FeeStatus.OVERDUE],
            academic_year=academic_year,
            page=page,
            page_size=page_size,
        )

    def get_overdue_fees(
        self,
        as_of_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Fee]:
        """Get all overdue fees.

        Args:
            as_of_date: Date to check overdue against (defaults to today).
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResult containing overdue fee records.
        """
        if as_of_date is None:
            as_of_date = date.today()

        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = self.get_base_query().where(
            and_(
                Fee.due_date < as_of_date,
                Fee.status.in_([FeeStatus.PENDING, FeeStatus.PARTIAL]),
            )
        )

        query = query.order_by(Fee.due_date.asc())

        # Get total count
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Load relations
        query = query.options(joinedload(Fee.student))

        result = self.db.execute(query)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_fee_collection_summary(
        self,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get fee collection summary statistics.

        Args:
            academic_year: Optional academic year filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            Dictionary with fee collection statistics.
        """
        query = self.get_base_query()

        if academic_year is not None:
            query = query.where(Fee.academic_year == academic_year)
        if start_date is not None:
            query = query.where(Fee.due_date >= start_date)
        if end_date is not None:
            query = query.where(Fee.due_date <= end_date)

        result = self.db.execute(query)
        fees = list(result.scalars().all())

        total_amount = sum(fee.amount for fee in fees)
        total_collected = sum(fee.paid_amount for fee in fees)
        total_pending = total_amount - total_collected

        # Count by status
        status_counts = {}
        for fee in fees:
            status_value = fee.status.value
            status_counts[status_value] = status_counts.get(status_value, 0) + 1

        # Count by fee type
        fee_type_summary = {}
        for fee in fees:
            if fee.fee_type not in fee_type_summary:
                fee_type_summary[fee.fee_type] = {
                    "count": 0,
                    "total_amount": Decimal("0.00"),
                    "collected": Decimal("0.00"),
                }
            fee_type_summary[fee.fee_type]["count"] += 1
            fee_type_summary[fee.fee_type]["total_amount"] += fee.amount
            fee_type_summary[fee.fee_type]["collected"] += fee.paid_amount

        return {
            "total_fees": len(fees),
            "total_amount": float(total_amount),
            "total_collected": float(total_collected),
            "total_pending": float(total_pending),
            "collection_percentage": round(
                float(total_collected) / float(total_amount) * 100, 2
            ) if total_amount > 0 else 0.0,
            "status_counts": status_counts,
            "fee_type_summary": {
                fee_type: {
                    "count": data["count"],
                    "total_amount": float(data["total_amount"]),
                    "collected": float(data["collected"]),
                    "pending": float(data["total_amount"] - data["collected"]),
                }
                for fee_type, data in fee_type_summary.items()
            },
        }

    def get_student_fee_summary(self, student_id: int) -> dict[str, Any]:
        """Get fee summary for a specific student.

        Args:
            student_id: The student ID.

        Returns:
            Dictionary with student fee statistics.
        """
        fees = self.get_by_student(student_id)

        total_amount = sum(fee.amount for fee in fees)
        total_paid = sum(fee.paid_amount for fee in fees)
        total_pending = total_amount - total_paid

        pending_count = sum(
            1 for fee in fees
            if fee.status in [FeeStatus.PENDING, FeeStatus.PARTIAL, FeeStatus.OVERDUE]
        )

        return {
            "total_fees": len(fees),
            "total_amount": float(total_amount),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "pending_count": pending_count,
        }

    def record_payment(
        self,
        fee_id: int,
        payment_amount: Decimal,
        payment_date: date | None = None,
    ) -> Fee | None:
        """Record a payment for a fee.

        Updates the paid_amount and status based on the payment.

        Args:
            fee_id: The fee ID.
            payment_amount: The amount being paid.
            payment_date: The date of payment (defaults to today).

        Returns:
            The updated Fee object or None if not found.
        """
        fee = self.get_by_id(fee_id)
        if fee is None:
            return None

        if payment_date is None:
            payment_date = date.today()

        # Update paid amount
        fee.paid_amount = fee.paid_amount + payment_amount
        fee.payment_date = payment_date

        # Update status based on payment
        fee.status = self._calculate_fee_status(fee.paid_amount, fee.amount)

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
