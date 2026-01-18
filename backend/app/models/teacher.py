"""Teacher model for teacher management."""

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.school import Class, Subject
    from app.models.timetable import Timetable
    from app.models.user import User


class TeacherStatus(str, enum.Enum):
    """Teacher employment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    RESIGNED = "resigned"


class Teacher(TenantAwareBase):
    """Teacher model with employment and assignment information."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subjects: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    classes_assigned: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    qualifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TeacherStatus] = mapped_column(
        Enum(TeacherStatus, values_callable=lambda x: [e.value for e in x]),
        default=TeacherStatus.ACTIVE, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="teacher")
    class_teacher_of: Mapped[list["Class"]] = relationship(
        "Class", back_populates="class_teacher", lazy="dynamic"
    )
    subjects_taught: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="teacher", lazy="dynamic"
    )
    timetable_entries: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="teacher", lazy="dynamic"
    )
    attendances_marked: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="marked_by_user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Teacher(id={self.id}, employee_id='{self.employee_id}')>"
