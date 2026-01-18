"""Exam and Grade models for academic assessment."""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.school import Class, Subject
    from app.models.student import Student


class ExamType(str, enum.Enum):
    """Types of examinations."""

    UNIT_TEST = "unit_test"
    MIDTERM = "midterm"
    FINAL = "final"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"


class Exam(TenantAwareBase):
    """Exam model for managing examinations."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType), nullable=False)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="exams")
    grades: Mapped[list["Grade"]] = relationship("Grade", back_populates="exam", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, name='{self.name}', type='{self.exam_type.value}')>"


class Grade(TenantAwareBase):
    """Grade model for storing student exam results."""

    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marks_obtained: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="grades")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="grades")
    exam: Mapped["Exam"] = relationship("Exam", back_populates="grades")

    def __repr__(self) -> str:
        return f"<Grade(id={self.id}, student_id={self.student_id}, marks={self.marks_obtained}/{self.max_marks})>"
