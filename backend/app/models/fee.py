"""Fee model for financial management and payment tracking."""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.student import Student


class FeeStatus(str, enum.Enum):
    """Fee payment status."""

    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"


class Fee(TenantAwareBase):
    """Fee model for tracking student fees and payments."""

    __tablename__ = "fees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fee_type: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[FeeStatus] = mapped_column(
        Enum(FeeStatus), default=FeeStatus.PENDING, nullable=False
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="fees")

    def __repr__(self) -> str:
        return f"<Fee(id={self.id}, student_id={self.student_id}, amount={self.amount}, status='{self.status.value}')>"
