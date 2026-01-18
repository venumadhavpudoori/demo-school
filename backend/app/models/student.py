"""Student model for student management."""

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.exam import Grade
    from app.models.fee import Fee
    from app.models.school import Class, Section
    from app.models.user import User


class Gender(str, enum.Enum):
    """Gender options."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class StudentStatus(str, enum.Enum):
    """Student enrollment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"
    TRANSFERRED = "transferred"
    DELETED = "deleted"


class Student(TenantAwareBase):
    """Student model with enrollment and personal information."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    admission_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    roll_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus), default=StudentStatus.ACTIVE, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="student")
    class_: Mapped["Class | None"] = relationship("Class", back_populates="students")
    section: Mapped["Section | None"] = relationship("Section", back_populates="students")
    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="student", lazy="dynamic"
    )
    grades: Mapped[list["Grade"]] = relationship("Grade", back_populates="student", lazy="dynamic")
    fees: Mapped[list["Fee"]] = relationship("Fee", back_populates="student", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, admission_number='{self.admission_number}')>"
