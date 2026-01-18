"""Exam service for business logic operations.

This module provides the ExamService class that handles all business logic
related to exam management including creation, querying, and validation.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamType
from app.repositories.exam import ExamRepository


class ExamServiceError(Exception):
    """Base exception for exam service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ExamNotFoundError(ExamServiceError):
    """Raised when an exam is not found."""

    def __init__(self, exam_id: int):
        super().__init__(
            message=f"Exam with ID {exam_id} not found",
            code="EXAM_NOT_FOUND",
        )


class InvalidExamDataError(ExamServiceError):
    """Raised when exam data is invalid."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_EXAM_DATA",
        )


class ExamDateConflictError(ExamServiceError):
    """Raised when exam dates conflict with existing exams."""

    def __init__(self, class_id: int, start_date: date, end_date: date):
        super().__init__(
            message=f"Exam dates {start_date} to {end_date} conflict with existing exam for class {class_id}",
            code="EXAM_DATE_CONFLICT",
        )


class ExamService:
    """Service class for exam business logic.

    Handles all business operations related to exams including
    creation, updates, and querying.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the exam service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = ExamRepository(db, tenant_id)

    def create_exam(
        self,
        name: str,
        exam_type: str,
        class_id: int,
        start_date: date,
        end_date: date,
        academic_year: str,
    ) -> Exam:
        """Create a new exam.

        Args:
            name: The exam name.
            exam_type: The type of exam.
            class_id: The class ID.
            start_date: The exam start date.
            end_date: The exam end date.
            academic_year: The academic year.

        Returns:
            The created Exam object.

        Raises:
            InvalidExamDataError: If exam data is invalid.
        """
        # Validate dates
        if end_date < start_date:
            raise InvalidExamDataError("End date must be on or after start date")

        # Convert exam_type string to enum
        try:
            exam_type_enum = ExamType(exam_type)
        except ValueError:
            raise InvalidExamDataError(f"Invalid exam type: {exam_type}")

        exam = self.repository.create({
            "name": name,
            "exam_type": exam_type_enum,
            "class_id": class_id,
            "start_date": start_date,
            "end_date": end_date,
            "academic_year": academic_year,
        })

        return exam

    def get_exam(self, exam_id: int) -> Exam:
        """Get an exam by ID.

        Args:
            exam_id: The exam ID.

        Returns:
            The Exam object.

        Raises:
            ExamNotFoundError: If exam not found.
        """
        exam = self.repository.get_by_id_with_relations(exam_id)
        if exam is None:
            raise ExamNotFoundError(exam_id)
        return exam

    def update_exam(
        self,
        exam_id: int,
        name: str | None = None,
        exam_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        academic_year: str | None = None,
    ) -> Exam:
        """Update an exam.

        Args:
            exam_id: The exam ID.
            name: Optional new name.
            exam_type: Optional new exam type.
            start_date: Optional new start date.
            end_date: Optional new end date.
            academic_year: Optional new academic year.

        Returns:
            The updated Exam object.

        Raises:
            ExamNotFoundError: If exam not found.
            InvalidExamDataError: If exam data is invalid.
        """
        exam = self.repository.get_by_id(exam_id)
        if exam is None:
            raise ExamNotFoundError(exam_id)

        # Validate dates if both are provided or one is being updated
        new_start = start_date if start_date is not None else exam.start_date
        new_end = end_date if end_date is not None else exam.end_date
        if new_end < new_start:
            raise InvalidExamDataError("End date must be on or after start date")

        update_data: dict[str, Any] = {}

        if name is not None:
            update_data["name"] = name
        if exam_type is not None:
            try:
                update_data["exam_type"] = ExamType(exam_type)
            except ValueError:
                raise InvalidExamDataError(f"Invalid exam type: {exam_type}")
        if start_date is not None:
            update_data["start_date"] = start_date
        if end_date is not None:
            update_data["end_date"] = end_date
        if academic_year is not None:
            update_data["academic_year"] = academic_year

        if update_data:
            for field, value in update_data.items():
                setattr(exam, field, value)
            self.db.commit()
            self.db.refresh(exam)

        return exam

    def delete_exam(self, exam_id: int) -> bool:
        """Delete an exam.

        Args:
            exam_id: The exam ID.

        Returns:
            True if deleted successfully.

        Raises:
            ExamNotFoundError: If exam not found.
        """
        exam = self.repository.get_by_id(exam_id)
        if exam is None:
            raise ExamNotFoundError(exam_id)

        self.db.delete(exam)
        self.db.commit()
        return True

    def list_exams(
        self,
        class_id: int | None = None,
        exam_type: str | None = None,
        academic_year: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List exams with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            exam_type: Optional exam type filter.
            academic_year: Optional academic year filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        # Convert exam_type string to enum if provided
        exam_type_enum = None
        if exam_type is not None:
            try:
                exam_type_enum = ExamType(exam_type)
            except ValueError:
                pass  # Invalid type, will return no results

        result = self.repository.list_with_filters(
            class_id=class_id,
            exam_type=exam_type_enum,
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                {
                    "id": exam.id,
                    "name": exam.name,
                    "exam_type": exam.exam_type.value,
                    "class_id": exam.class_id,
                    "class_name": exam.class_.name if exam.class_ else None,
                    "start_date": exam.start_date.isoformat(),
                    "end_date": exam.end_date.isoformat(),
                    "academic_year": exam.academic_year,
                }
                for exam in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }

    def get_exams_for_academic_year(
        self, academic_year: str, class_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Get all exams for an academic year.

        Args:
            academic_year: The academic year.
            class_id: Optional class ID filter.

        Returns:
            List of exam dictionaries.
        """
        exams = self.repository.get_exams_for_academic_year(academic_year, class_id)

        return [
            {
                "id": exam.id,
                "name": exam.name,
                "exam_type": exam.exam_type.value,
                "class_id": exam.class_id,
                "class_name": exam.class_.name if exam.class_ else None,
                "start_date": exam.start_date.isoformat(),
                "end_date": exam.end_date.isoformat(),
                "academic_year": exam.academic_year,
            }
            for exam in exams
        ]
