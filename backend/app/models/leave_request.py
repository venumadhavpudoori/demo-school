"""Leave request model for managing leave applications."""

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.user import User


class RequesterType(str, enum.Enum):
    """Type of requester for leave."""

    TEACHER = "teacher"
    STUDENT = "student"


class LeaveStatus(str, enum.Enum):
    """Status of leave request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveRequest(TenantAwareBase):
    """Leave request model for managing leave applications."""

    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requester_type: Mapped[RequesterType] = mapped_column(Enum(RequesterType), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False
    )
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    requester: Mapped["User"] = relationship(
        "User", foreign_keys=[requester_id], back_populates="leave_requests"
    )
    approver: Mapped["User | None"] = relationship(
        "User", foreign_keys=[approved_by], back_populates="approved_leaves"
    )

    def __repr__(self) -> str:
        return f"<LeaveRequest(id={self.id}, requester_id={self.requester_id}, status='{self.status.value}')>"
