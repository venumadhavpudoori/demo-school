"""Timetable model for class scheduling."""

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.school import Class, Section, Subject
    from app.models.teacher import Teacher


class Timetable(TenantAwareBase):
    """Timetable model for managing class schedules."""

    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="timetable_entries")
    section: Mapped["Section | None"] = relationship("Section", back_populates="timetable_entries")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="timetable_entries")
    teacher: Mapped["Teacher | None"] = relationship("Teacher", back_populates="timetable_entries")

    def __repr__(self) -> str:
        return f"<Timetable(id={self.id}, day={self.day_of_week}, period={self.period_number})>"
