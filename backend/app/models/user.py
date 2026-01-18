"""User model for authentication and authorization."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.announcement import Announcement
    from app.models.leave_request import LeaveRequest
    from app.models.student import Student
    from app.models.teacher import Teacher
    from app.models.tenant import Tenant


class UserRole(str, enum.Enum):
    """User role types for RBAC."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class User(TenantAwareBase):
    """User model for authentication and role-based access control."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    student: Mapped["Student | None"] = relationship(
        "Student", back_populates="user", uselist=False
    )
    teacher: Mapped["Teacher | None"] = relationship(
        "Teacher", back_populates="user", uselist=False
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        "Announcement", back_populates="author", lazy="dynamic"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.requester_id",
        back_populates="requester",
        lazy="dynamic",
    )
    approved_leaves: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest",
        foreign_keys="LeaveRequest.approved_by",
        back_populates="approver",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
