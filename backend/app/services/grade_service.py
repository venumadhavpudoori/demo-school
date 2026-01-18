"""Grade service for business logic operations.

This module provides the GradeService class that handles all business logic
related to grade management including creation, calculation, and reporting.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.exam import Grade
from app.repositories.grade import GradeRepository
from app.repositories.exam import ExamRepository


class GradeServiceError(Exception):
    """Base exception for grade service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class GradeNotFoundError(GradeServiceError):
    """Raised when a grade is not found."""

    def __init__(self, grade_id: int):
        super().__init__(
            message=f"Grade with ID {grade_id} not found",
            code="GRADE_NOT_FOUND",
        )


class InvalidGradeDataError(GradeServiceError):
    """Raised when grade data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_GRADE_DATA",
        )


class DuplicateGradeError(GradeServiceError):
    """Raised when grade already exists for student/subject/exam combination."""

    def __init__(self, student_id: int, subject_id: int, exam_id: int):
        super().__init__(
            message=f"Grade already exists for student {student_id}, subject {subject_id}, exam {exam_id}",
            code="DUPLICATE_GRADE",
        )


# Default grading scale configuration
DEFAULT_GRADING_SCALE = [
    {"min_percentage": 90, "max_percentage": 100, "grade": "A+"},
    {"min_percentage": 80, "max_percentage": 89.99, "grade": "A"},
    {"min_percentage": 70, "max_percentage": 79.99, "grade": "B+"},
    {"min_percentage": 60, "max_percentage": 69.99, "grade": "B"},
    {"min_percentage": 50, "max_percentage": 59.99, "grade": "C+"},
    {"min_percentage": 40, "max_percentage": 49.99, "grade": "C"},
    {"min_percentage": 33, "max_percentage": 39.99, "grade": "D"},
    {"min_percentage": 0, "max_percentage": 32.99, "grade": "F"},
]


class GradeService:
    """Service class for grade business logic.

    Handles all business operations related to grades including
    creation, calculation, and reporting.
    """

    def __init__(
        self,
        db: Session,
        tenant_id: int,
        grading_scale: list[dict[str, Any]] | None = None,
    ):
        """Initialize the grade service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
            grading_scale: Optional custom grading scale.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = GradeRepository(db, tenant_id)
        self.exam_repository = ExamRepository(db, tenant_id)
        self.grading_scale = grading_scale or DEFAULT_GRADING_SCALE

    @staticmethod
    def calculate_percentage(marks_obtained: Decimal, max_marks: Decimal) -> float:
        """Calculate percentage from marks.

        Formula: marks_obtained / max_marks * 100

        Args:
            marks_obtained: Marks obtained by the student.
            max_marks: Maximum marks for the exam.

        Returns:
            Percentage rounded to 2 decimal places.
        """
        if max_marks <= 0:
            return 0.0
        percentage = float(marks_obtained) / float(max_marks) * 100
        return round(percentage, 2)

    def calculate_grade_letter(self, percentage: float) -> str:
        """Calculate grade letter from percentage using the grading scale.

        Args:
            percentage: The percentage score.

        Returns:
            The grade letter.
        """
        for scale in self.grading_scale:
            if scale["min_percentage"] <= percentage <= scale["max_percentage"]:
                return scale["grade"]
        return "F"  # Default to F if no match

    def create_grade(
        self,
        student_id: int,
        subject_id: int,
        exam_id: int,
        marks_obtained: Decimal,
        max_marks: Decimal,
        remarks: str | None = None,
    ) -> Grade:
        """Create a new grade entry with automatic grade letter calculation.

        Args:
            student_id: The student ID.
            subject_id: The subject ID.
            exam_id: The exam ID.
            marks_obtained: Marks obtained by the student.
            max_marks: Maximum marks for the exam.
            remarks: Optional remarks.

        Returns:
            The created Grade object.

        Raises:
            InvalidGradeDataError: If grade data is invalid.
            DuplicateGradeError: If grade already exists.
        """
        # Validate marks
        if marks_obtained < 0:
            raise InvalidGradeDataError("Marks obtained cannot be negative")
        if max_marks <= 0:
            raise InvalidGradeDataError("Maximum marks must be greater than 0")
        if marks_obtained > max_marks:
            raise InvalidGradeDataError("Marks obtained cannot exceed maximum marks")

        # Check for existing grade
        existing = self.repository.get_by_student_subject_exam(
            student_id, subject_id, exam_id
        )
        if existing:
            raise DuplicateGradeError(student_id, subject_id, exam_id)

        # Calculate percentage and grade letter
        percentage = self.calculate_percentage(marks_obtained, max_marks)
        grade_letter = self.calculate_grade_letter(percentage)

        grade = self.repository.create({
            "student_id": student_id,
            "subject_id": subject_id,
            "exam_id": exam_id,
            "marks_obtained": marks_obtained,
            "max_marks": max_marks,
            "grade": grade_letter,
            "remarks": remarks,
        })

        return grade

    def bulk_create_grades(
        self,
        subject_id: int,
        exam_id: int,
        max_marks: Decimal,
        grades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create multiple grade entries in bulk with automatic grade calculation.

        Args:
            subject_id: The subject ID.
            exam_id: The exam ID.
            max_marks: Maximum marks for all entries.
            grades: List of dicts with student_id, marks_obtained, and optional remarks.

        Returns:
            Dictionary with summary of the operation.

        Raises:
            InvalidGradeDataError: If grade data is invalid.
        """
        if not grades:
            raise InvalidGradeDataError("No grade records provided")

        if max_marks <= 0:
            raise InvalidGradeDataError("Maximum marks must be greater than 0")

        # Validate and prepare records
        records = []
        for i, grade_data in enumerate(grades):
            if "student_id" not in grade_data:
                raise InvalidGradeDataError(f"Record {i}: missing student_id")
            if "marks_obtained" not in grade_data:
                raise InvalidGradeDataError(f"Record {i}: missing marks_obtained")

            marks_obtained = Decimal(str(grade_data["marks_obtained"]))
            if marks_obtained < 0:
                raise InvalidGradeDataError(
                    f"Record {i}: marks_obtained cannot be negative"
                )
            if marks_obtained > max_marks:
                raise InvalidGradeDataError(
                    f"Record {i}: marks_obtained cannot exceed max_marks"
                )

            # Calculate grade letter
            percentage = self.calculate_percentage(marks_obtained, max_marks)
            grade_letter = self.calculate_grade_letter(percentage)

            records.append({
                "student_id": grade_data["student_id"],
                "marks_obtained": marks_obtained,
                "grade": grade_letter,
                "remarks": grade_data.get("remarks"),
            })

        # Perform bulk upsert
        grade_records = self.repository.bulk_upsert(
            exam_id=exam_id,
            subject_id=subject_id,
            max_marks=max_marks,
            records=records,
        )

        return {
            "total_created": len(grade_records),
            "subject_id": subject_id,
            "exam_id": exam_id,
            "grades": [
                self._format_grade_response(g) for g in grade_records
            ],
        }

    def get_grade(self, grade_id: int) -> Grade:
        """Get a grade by ID.

        Args:
            grade_id: The grade ID.

        Returns:
            The Grade object.

        Raises:
            GradeNotFoundError: If grade not found.
        """
        grade = self.repository.get_by_id_with_relations(grade_id)
        if grade is None:
            raise GradeNotFoundError(grade_id)
        return grade

    def update_grade(
        self,
        grade_id: int,
        marks_obtained: Decimal | None = None,
        max_marks: Decimal | None = None,
        remarks: str | None = None,
    ) -> Grade:
        """Update a grade entry with automatic grade letter recalculation.

        Args:
            grade_id: The grade ID.
            marks_obtained: Optional new marks obtained.
            max_marks: Optional new maximum marks.
            remarks: Optional new remarks.

        Returns:
            The updated Grade object.

        Raises:
            GradeNotFoundError: If grade not found.
            InvalidGradeDataError: If grade data is invalid.
        """
        grade = self.repository.get_by_id(grade_id)
        if grade is None:
            raise GradeNotFoundError(grade_id)

        # Determine new values
        new_marks = marks_obtained if marks_obtained is not None else grade.marks_obtained
        new_max = max_marks if max_marks is not None else grade.max_marks

        # Validate
        if new_marks < 0:
            raise InvalidGradeDataError("Marks obtained cannot be negative")
        if new_max <= 0:
            raise InvalidGradeDataError("Maximum marks must be greater than 0")
        if new_marks > new_max:
            raise InvalidGradeDataError("Marks obtained cannot exceed maximum marks")

        # Update fields
        if marks_obtained is not None:
            grade.marks_obtained = marks_obtained
        if max_marks is not None:
            grade.max_marks = max_marks
        if remarks is not None:
            grade.remarks = remarks

        # Recalculate grade letter
        percentage = self.calculate_percentage(grade.marks_obtained, grade.max_marks)
        grade.grade = self.calculate_grade_letter(percentage)

        self.db.commit()
        self.db.refresh(grade)

        return grade

    def delete_grade(self, grade_id: int) -> bool:
        """Delete a grade.

        Args:
            grade_id: The grade ID.

        Returns:
            True if deleted successfully.

        Raises:
            GradeNotFoundError: If grade not found.
        """
        grade = self.repository.get_by_id(grade_id)
        if grade is None:
            raise GradeNotFoundError(grade_id)

        self.db.delete(grade)
        self.db.commit()
        return True

    def list_grades(
        self,
        student_id: int | None = None,
        subject_id: int | None = None,
        exam_id: int | None = None,
        class_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List grades with filtering and pagination.

        Args:
            student_id: Optional student ID filter.
            subject_id: Optional subject ID filter.
            exam_id: Optional exam ID filter.
            class_id: Optional class ID filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        result = self.repository.list_with_filters(
            student_id=student_id,
            subject_id=subject_id,
            exam_id=exam_id,
            class_id=class_id,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [self._format_grade_response(g) for g in result.items],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def _format_grade_response(self, grade: Grade) -> dict[str, Any]:
        """Format a grade object for response.

        Args:
            grade: The Grade object.

        Returns:
            Dictionary with formatted grade data.
        """
        percentage = self.calculate_percentage(grade.marks_obtained, grade.max_marks)

        student_name = None
        if grade.student and grade.student.user:
            first_name = grade.student.user.profile_data.get("first_name", "")
            last_name = grade.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return {
            "id": grade.id,
            "student_id": grade.student_id,
            "student_name": student_name,
            "subject_id": grade.subject_id,
            "subject_name": grade.subject.name if grade.subject else None,
            "exam_id": grade.exam_id,
            "exam_name": grade.exam.name if grade.exam else None,
            "marks_obtained": float(grade.marks_obtained),
            "max_marks": float(grade.max_marks),
            "percentage": percentage,
            "grade": grade.grade,
            "remarks": grade.remarks,
        }

    def get_student_grades(
        self,
        student_id: int,
        exam_id: int | None = None,
        subject_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get all grades for a student.

        Args:
            student_id: The student ID.
            exam_id: Optional exam ID filter.
            subject_id: Optional subject ID filter.

        Returns:
            List of grade dictionaries.
        """
        grades = self.repository.get_student_grades(student_id, exam_id, subject_id)
        return [self._format_grade_response(g) for g in grades]


    def get_report_card(
        self,
        student_id: int,
        academic_year: str | None = None,
    ) -> dict[str, Any]:
        """Generate a report card for a student.

        Args:
            student_id: The student ID.
            academic_year: Optional academic year filter.

        Returns:
            Dictionary with report card data.
        """
        from app.models.student import Student
        from sqlalchemy import select

        # Get student info
        stmt = select(Student).where(
            Student.tenant_id == self.tenant_id,
            Student.id == student_id,
        )
        result = self.db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            raise GradeNotFoundError(student_id)

        # Get student name
        student_name = ""
        if student.user:
            first_name = student.user.profile_data.get("first_name", "")
            last_name = student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip()

        # Get class and section info
        class_name = student.class_.name if student.class_ else "N/A"
        section_name = student.section.name if student.section else None

        # Get exams for the academic year
        exams = self.exam_repository.get_exams_for_academic_year(
            academic_year or "",
            class_id=student.class_id,
        )

        # If no academic year specified, get all exams for the student's class
        if not academic_year and student.class_id:
            from app.models.exam import Exam
            stmt = select(Exam).where(
                Exam.tenant_id == self.tenant_id,
                Exam.class_id == student.class_id,
            ).order_by(Exam.start_date.asc())
            result = self.db.execute(stmt)
            exams = list(result.scalars().all())

        # Build exam results
        exam_results = []
        all_percentages = []

        for exam in exams:
            grades = self.repository.get_student_grades(student_id, exam_id=exam.id)

            if not grades:
                continue

            subject_grades = []
            total_marks_obtained = Decimal("0")
            total_max_marks = Decimal("0")

            for grade in grades:
                percentage = self.calculate_percentage(
                    grade.marks_obtained, grade.max_marks
                )
                subject_grades.append({
                    "subject_id": grade.subject_id,
                    "subject_name": grade.subject.name if grade.subject else "N/A",
                    "subject_code": grade.subject.code if grade.subject else None,
                    "marks_obtained": float(grade.marks_obtained),
                    "max_marks": float(grade.max_marks),
                    "percentage": percentage,
                    "grade": grade.grade,
                    "remarks": grade.remarks,
                })
                total_marks_obtained += grade.marks_obtained
                total_max_marks += grade.max_marks

            if total_max_marks > 0:
                overall_percentage = self.calculate_percentage(
                    total_marks_obtained, total_max_marks
                )
                overall_grade = self.calculate_grade_letter(overall_percentage)
                all_percentages.append(overall_percentage)
            else:
                overall_percentage = 0.0
                overall_grade = "N/A"

            exam_results.append({
                "exam_id": exam.id,
                "exam_name": exam.name,
                "exam_type": exam.exam_type.value,
                "subject_grades": subject_grades,
                "total_marks_obtained": float(total_marks_obtained),
                "total_max_marks": float(total_max_marks),
                "overall_percentage": overall_percentage,
                "overall_grade": overall_grade,
            })

        # Calculate cumulative percentage
        cumulative_percentage = None
        cumulative_grade = None
        if all_percentages:
            cumulative_percentage = round(
                sum(all_percentages) / len(all_percentages), 2
            )
            cumulative_grade = self.calculate_grade_letter(cumulative_percentage)

        return {
            "student_id": student_id,
            "student_name": student_name,
            "admission_number": student.admission_number,
            "class_id": student.class_id,
            "class_name": class_name,
            "section_id": student.section_id,
            "section_name": section_name,
            "academic_year": academic_year or "All",
            "exam_results": exam_results,
            "cumulative_percentage": cumulative_percentage,
            "cumulative_grade": cumulative_grade,
        }

    def get_grade_analytics(
        self,
        class_id: int,
        exam_id: int,
    ) -> dict[str, Any]:
        """Get grade analytics for a class and exam.

        Args:
            class_id: The class ID.
            exam_id: The exam ID.

        Returns:
            Dictionary with analytics data.
        """
        from app.models.school import Class, Subject
        from sqlalchemy import select

        # Get class info
        stmt = select(Class).where(
            Class.tenant_id == self.tenant_id,
            Class.id == class_id,
        )
        result = self.db.execute(stmt)
        class_obj = result.scalar_one_or_none()
        class_name = class_obj.name if class_obj else "N/A"

        # Get exam info
        exam = self.exam_repository.get_by_id(exam_id)
        exam_name = exam.name if exam else "N/A"

        # Get all subjects for the class
        stmt = select(Subject).where(
            Subject.tenant_id == self.tenant_id,
            Subject.class_id == class_id,
        )
        result = self.db.execute(stmt)
        subjects = list(result.scalars().all())

        # Get all grades for the exam
        all_grades = self.repository.get_exam_grades(exam_id)

        if not all_grades:
            return {
                "class_analytics": {
                    "class_id": class_id,
                    "class_name": class_name,
                    "exam_id": exam_id,
                    "exam_name": exam_name,
                    "total_students": 0,
                    "average_percentage": 0.0,
                    "highest_percentage": 0.0,
                    "lowest_percentage": 0.0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "pass_percentage": 0.0,
                    "subject_analytics": [],
                    "grade_distribution": {},
                },
                "student_rankings": [],
            }

        # Calculate subject-level analytics
        subject_analytics = []
        for subject in subjects:
            stats = self.repository.get_subject_statistics(exam_id, subject.id)
            if stats["total_students"] > 0:
                subject_analytics.append({
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    **stats,
                })

        # Calculate student-level aggregates
        student_totals: dict[int, dict[str, Any]] = {}
        for grade in all_grades:
            student_id = grade.student_id
            if student_id not in student_totals:
                student_name = ""
                if grade.student and grade.student.user:
                    first_name = grade.student.user.profile_data.get("first_name", "")
                    last_name = grade.student.user.profile_data.get("last_name", "")
                    student_name = f"{first_name} {last_name}".strip()

                student_totals[student_id] = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "total_marks": Decimal("0"),
                    "total_max": Decimal("0"),
                }

            student_totals[student_id]["total_marks"] += grade.marks_obtained
            student_totals[student_id]["total_max"] += grade.max_marks

        # Calculate percentages and rankings
        student_rankings = []
        pass_threshold = 33.0
        pass_count = 0
        fail_count = 0
        grade_distribution: dict[str, int] = {}

        for student_data in student_totals.values():
            if student_data["total_max"] > 0:
                percentage = self.calculate_percentage(
                    student_data["total_marks"], student_data["total_max"]
                )
            else:
                percentage = 0.0

            grade_letter = self.calculate_grade_letter(percentage)
            grade_distribution[grade_letter] = grade_distribution.get(grade_letter, 0) + 1

            if percentage >= pass_threshold:
                pass_count += 1
            else:
                fail_count += 1

            student_rankings.append({
                "student_id": student_data["student_id"],
                "student_name": student_data["student_name"],
                "total_marks": float(student_data["total_marks"]),
                "total_max_marks": float(student_data["total_max"]),
                "percentage": percentage,
                "grade": grade_letter,
            })

        # Sort by percentage descending
        student_rankings.sort(key=lambda x: x["percentage"], reverse=True)

        # Add rank
        for i, student in enumerate(student_rankings, 1):
            student["rank"] = i

        # Calculate class-level statistics
        total_students = len(student_rankings)
        percentages = [s["percentage"] for s in student_rankings]

        return {
            "class_analytics": {
                "class_id": class_id,
                "class_name": class_name,
                "exam_id": exam_id,
                "exam_name": exam_name,
                "total_students": total_students,
                "average_percentage": round(sum(percentages) / total_students, 2) if total_students > 0 else 0.0,
                "highest_percentage": max(percentages) if percentages else 0.0,
                "lowest_percentage": min(percentages) if percentages else 0.0,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "pass_percentage": round(pass_count / total_students * 100, 2) if total_students > 0 else 0.0,
                "subject_analytics": subject_analytics,
                "grade_distribution": grade_distribution,
            },
            "student_rankings": student_rankings,
        }
