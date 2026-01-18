"""Student service for business logic operations.

This module provides the StudentService class that handles all business logic
related to student management including CRUD operations and profile aggregation.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.student import Gender, Student, StudentStatus
from app.models.user import User, UserRole
from app.repositories.student import StudentRepository
from app.services.auth_service import AuthService


class StudentServiceError(Exception):
    """Base exception for student service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class StudentNotFoundError(StudentServiceError):
    """Raised when a student is not found."""

    def __init__(self, student_id: int):
        super().__init__(
            message=f"Student with ID {student_id} not found",
            code="STUDENT_NOT_FOUND",
        )


class DuplicateAdmissionNumberError(StudentServiceError):
    """Raised when admission number already exists."""

    def __init__(self, admission_number: str):
        super().__init__(
            message=f"Admission number '{admission_number}' already exists",
            code="DUPLICATE_ADMISSION_NUMBER",
        )


class DuplicateEmailError(StudentServiceError):
    """Raised when email already exists."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Email '{email}' already exists",
            code="DUPLICATE_EMAIL",
        )


class StudentService:
    """Service class for student business logic.

    Handles all business operations related to students including
    creation, updates, deletion, and profile aggregation.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the student service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = StudentRepository(db, tenant_id)
        self.auth_service = AuthService()

    def create_student(
        self,
        admission_number: str,
        email: str,
        password: str,
        date_of_birth: date,
        gender: Gender,
        admission_date: date,
        class_id: int | None = None,
        section_id: int | None = None,
        roll_number: int | None = None,
        address: str | None = None,
        parent_ids: list[int] | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> Student:
        """Create a new student with associated user account.

        Args:
            admission_number: Unique admission number.
            email: Student's email address.
            password: Password for the user account.
            date_of_birth: Student's date of birth.
            gender: Student's gender.
            admission_date: Date of admission.
            class_id: Optional class ID.
            section_id: Optional section ID.
            roll_number: Optional roll number.
            address: Optional address.
            parent_ids: Optional list of parent user IDs.
            profile_data: Optional additional profile data.

        Returns:
            The created Student object.

        Raises:
            DuplicateAdmissionNumberError: If admission number exists.
            DuplicateEmailError: If email already exists.
        """
        # Check for duplicate admission number
        if self.repository.admission_number_exists(admission_number):
            raise DuplicateAdmissionNumberError(admission_number)

        # Check for duplicate email
        from sqlalchemy import select
        existing_user = self.db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing_user:
            raise DuplicateEmailError(email)

        # Create user account
        password_hash = self.auth_service.hash_password(password)
        user = User(
            tenant_id=self.tenant_id,
            email=email,
            password_hash=password_hash,
            role=UserRole.STUDENT,
            profile_data=profile_data or {},
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()  # Get user ID

        # Create student record
        student = Student(
            tenant_id=self.tenant_id,
            user_id=user.id,
            admission_number=admission_number,
            class_id=class_id,
            section_id=section_id,
            roll_number=roll_number,
            date_of_birth=date_of_birth,
            gender=gender,
            address=address,
            parent_ids=parent_ids,
            admission_date=admission_date,
            status=StudentStatus.ACTIVE,
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)

        return student

    def get_student(self, student_id: int) -> Student:
        """Get a student by ID.

        Args:
            student_id: The student ID.

        Returns:
            The Student object.

        Raises:
            StudentNotFoundError: If student not found.
        """
        student = self.repository.get_by_id_with_relations(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return student

    def get_student_profile(self, student_id: int) -> dict[str, Any]:
        """Get complete student profile with aggregated data.

        Args:
            student_id: The student ID.

        Returns:
            Dictionary containing student info, attendance, grades, and fees.

        Raises:
            StudentNotFoundError: If student not found.
        """
        student = self.get_student(student_id)

        # Get aggregated data
        attendance_summary = self.repository.get_attendance_summary(student_id)
        grades_summary = self.repository.get_grades_summary(student_id)
        fees_summary = self.repository.get_fees_summary(student_id)

        return {
            "student": {
                "id": student.id,
                "admission_number": student.admission_number,
                "class_id": student.class_id,
                "class_name": student.class_.name if student.class_ else None,
                "section_id": student.section_id,
                "section_name": student.section.name if student.section else None,
                "roll_number": student.roll_number,
                "date_of_birth": student.date_of_birth.isoformat(),
                "gender": student.gender.value,
                "address": student.address,
                "admission_date": student.admission_date.isoformat(),
                "status": student.status.value,
                "user": {
                    "id": student.user.id,
                    "email": student.user.email,
                    "profile_data": student.user.profile_data,
                    "is_active": student.user.is_active,
                },
            },
            "attendance": attendance_summary,
            "grades": grades_summary,
            "fees": fees_summary,
        }

    def update_student(
        self,
        student_id: int,
        admission_number: str | None = None,
        class_id: int | None = None,
        section_id: int | None = None,
        roll_number: int | None = None,
        address: str | None = None,
        parent_ids: list[int] | None = None,
        status: StudentStatus | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> Student:
        """Update a student's information.

        Args:
            student_id: The student ID.
            admission_number: Optional new admission number.
            class_id: Optional new class ID.
            section_id: Optional new section ID.
            roll_number: Optional new roll number.
            address: Optional new address.
            parent_ids: Optional new parent IDs.
            status: Optional new status.
            profile_data: Optional new profile data for user.

        Returns:
            The updated Student object.

        Raises:
            StudentNotFoundError: If student not found.
            DuplicateAdmissionNumberError: If new admission number exists.
        """
        student = self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        # Check for duplicate admission number if changing
        if admission_number and admission_number != student.admission_number:
            if self.repository.admission_number_exists(admission_number, exclude_id=student_id):
                raise DuplicateAdmissionNumberError(admission_number)
            student.admission_number = admission_number

        # Update fields if provided
        if class_id is not None:
            student.class_id = class_id
        if section_id is not None:
            student.section_id = section_id
        if roll_number is not None:
            student.roll_number = roll_number
        if address is not None:
            student.address = address
        if parent_ids is not None:
            student.parent_ids = parent_ids
        if status is not None:
            student.status = status

        # Update user profile data if provided
        if profile_data is not None:
            student.user.profile_data = {
                **student.user.profile_data,
                **profile_data,
            }

        self.db.commit()
        self.db.refresh(student)

        return student

    def delete_student(self, student_id: int, hard_delete: bool = False) -> bool:
        """Delete a student (soft delete by default).

        Args:
            student_id: The student ID.
            hard_delete: If True, permanently delete the record.

        Returns:
            True if deleted successfully.

        Raises:
            StudentNotFoundError: If student not found.
        """
        student = self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        if hard_delete:
            # Also delete the associated user
            self.db.delete(student.user)
            self.db.delete(student)
        else:
            # Soft delete - set status to deleted
            student.status = StudentStatus.DELETED
            student.user.is_active = False

        self.db.commit()
        return True

    def list_students(
        self,
        class_id: int | None = None,
        section_id: int | None = None,
        status: StudentStatus | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List students with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            section_id: Optional section ID filter.
            status: Optional status filter.
            search: Optional search query.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        if search:
            result = self.repository.search(
                query=search,
                class_id=class_id,
                section_id=section_id,
                status=status,
                page=page,
                page_size=page_size,
            )
        else:
            filters: dict[str, Any] = {}
            if class_id is not None:
                filters["class_id"] = class_id
            if section_id is not None:
                filters["section_id"] = section_id
            if status is not None:
                filters["status"] = status

            result = self.repository.list(
                filters=filters,
                page=page,
                page_size=page_size,
            )

        return {
            "items": [
                {
                    "id": student.id,
                    "admission_number": student.admission_number,
                    "class_id": student.class_id,
                    "section_id": student.section_id,
                    "roll_number": student.roll_number,
                    "date_of_birth": student.date_of_birth.isoformat(),
                    "gender": student.gender.value,
                    "status": student.status.value,
                    "user": {
                        "id": student.user.id,
                        "email": student.user.email,
                        "profile_data": student.user.profile_data,
                    } if student.user else None,
                }
                for student in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
