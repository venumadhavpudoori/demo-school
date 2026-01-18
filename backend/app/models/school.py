"""School-related models: Class, Section, Subject."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantAwareBase

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.exam import Exam
    from app.models.grade import Grade
    from app.models.student import Student
    from app.models.teacher import Teacher
    from app.models.timetable import Timetable


class Class(TenantAwareBase):
    """Class model representing a grade/year level."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    class_teacher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    class_teacher: Mapped["Teacher | None"] = relationship(
        "Teacher", back_populates="class_teacher_of"
    )
    sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="class_", lazy="dynamic"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject", back_populates="class_", lazy="dynamic"
    )
    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="class_", lazy="dynamic"
    )
    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="class_", lazy="dynamic"
    )
    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="class_", lazy="dynamic")
    timetable_entries: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="class_", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Class(id={self.id}, name='{self.name}', grade_level={self.grade_level})>"


class Section(TenantAwareBase):
    """Section model representing a division within a class."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    students_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="sections")
    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="section", lazy="dynamic"
    )
    timetable_entries: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="section", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Section(id={self.id}, name='{self.name}', class_id={self.class_id})>"


class Subject(TenantAwareBase):
    """Subject model representing a course/subject taught in a class."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True
    )
    credits: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    class_: Mapped["Class"] = relationship("Class", back_populates="subjects")
    teacher: Mapped["Teacher | None"] = relationship("Teacher", back_populates="subjects_taught")
    grades: Mapped[list["Grade"]] = relationship("Grade", back_populates="subject", lazy="dynamic")
    timetable_entries: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="subject", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name='{self.name}', code='{self.code}')>"
