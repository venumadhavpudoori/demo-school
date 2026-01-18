"""Teacher service for business logic operations.

This module provides the TeacherService class that handles all business logic
related to teacher management including CRUD operations.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.teacher import Teacher, TeacherStatus
from app.models.user import User, UserRole
from app.repositories.teacher import TeacherRepository
from app.services.auth_service import AuthService


class TeacherServiceError(Exception):
    """Base exception for teacher service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class TeacherNotFoundError(TeacherServiceError):
    """Raised when a teacher is not found."""

    def __init__(self, teacher_id: int):
        super().__init__(
            message=f"Teacher with ID {teacher_id} not found",
            code="TEACHER_NOT_FOUND",
        )


class DuplicateEmployeeIdError(TeacherServiceError):
    """Raised when employee ID already exists."""

    def __init__(self, employee_id: str):
        super().__init__(
            message=f"Employee ID '{employee_id}' already exists",
            code="DUPLICATE_EMPLOYEE_ID",
        )


class DuplicateEmailError(TeacherServiceError):
    """Raised when email already exists."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Email '{email}' already exists",
            code="DUPLICATE_EMAIL",
        )


class TeacherService:
    """Service class for teacher business logic.

    Handles all business operations related to teachers including
    creation, updates, and retrieval.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the teacher service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = TeacherRepository(db, tenant_id)
        self.auth_service = AuthService()

    def create_teacher(
        self,
        employee_id: str,
        email: str,
        password: str,
        joining_date: date,
        subjects: list[str] | None = None,
        classes_assigned: list[int] | None = None,
        qualifications: str | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> Teacher:
        """Create a new teacher with associated user account.

        Args:
            employee_id: Unique employee ID.
            email: Teacher's email address.
            password: Password for the user account.
            joining_date: Date of joining.
            subjects: Optional list of subjects taught.
            classes_assigned: Optional list of assigned class IDs.
            qualifications: Optional qualifications text.
            profile_data: Optional additional profile data.

        Returns:
            The created Teacher object.

        Raises:
            DuplicateEmployeeIdError: If employee ID exists.
            DuplicateEmailError: If email already exists.
        """
        # Check for duplicate employee ID
        if self.repository.employee_id_exists(employee_id):
            raise DuplicateEmployeeIdError(employee_id)

        # Check for duplicate email
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
            role=UserRole.TEACHER,
            profile_data=profile_data or {},
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()  # Get user ID

        # Create teacher record
        teacher = Teacher(
            tenant_id=self.tenant_id,
            user_id=user.id,
            employee_id=employee_id,
            subjects=subjects,
            classes_assigned=classes_assigned,
            qualifications=qualifications,
            joining_date=joining_date,
            status=TeacherStatus.ACTIVE,
        )
        self.db.add(teacher)
        self.db.commit()
        self.db.refresh(teacher)

        return teacher

    def get_teacher(self, teacher_id: int) -> Teacher:
        """Get a teacher by ID.

        Args:
            teacher_id: The teacher ID.

        Returns:
            The Teacher object.

        Raises:
            TeacherNotFoundError: If teacher not found.
        """
        teacher = self.repository.get_by_id_with_relations(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        return teacher

    def update_teacher(
        self,
        teacher_id: int,
        employee_id: str | None = None,
        subjects: list[str] | None = None,
        classes_assigned: list[int] | None = None,
        qualifications: str | None = None,
        status: TeacherStatus | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> Teacher:
        """Update a teacher's information.

        Args:
            teacher_id: The teacher ID.
            employee_id: Optional new employee ID.
            subjects: Optional new subjects list.
            classes_assigned: Optional new assigned classes.
            qualifications: Optional new qualifications.
            status: Optional new status.
            profile_data: Optional new profile data for user.

        Returns:
            The updated Teacher object.

        Raises:
            TeacherNotFoundError: If teacher not found.
            DuplicateEmployeeIdError: If new employee ID exists.
        """
        teacher = self.repository.get_by_id(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)

        # Check for duplicate employee ID if changing
        if employee_id and employee_id != teacher.employee_id:
            if self.repository.employee_id_exists(employee_id, exclude_id=teacher_id):
                raise DuplicateEmployeeIdError(employee_id)
            teacher.employee_id = employee_id

        # Update fields if provided
        if subjects is not None:
            teacher.subjects = subjects
        if classes_assigned is not None:
            teacher.classes_assigned = classes_assigned
        if qualifications is not None:
            teacher.qualifications = qualifications
        if status is not None:
            teacher.status = status

        # Update user profile data if provided
        if profile_data is not None:
            teacher.user.profile_data = {
                **teacher.user.profile_data,
                **profile_data,
            }

        self.db.commit()
        self.db.refresh(teacher)

        return teacher

    def get_teacher_classes(self, teacher_id: int) -> dict[str, Any]:
        """Get all classes associated with a teacher.

        Args:
            teacher_id: The teacher ID.

        Returns:
            Dictionary with assigned classes and class teacher classes.

        Raises:
            TeacherNotFoundError: If teacher not found.
        """
        teacher = self.repository.get_by_id(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)

        assigned_classes = self.repository.get_assigned_classes(teacher_id)
        class_teacher_classes = self.repository.get_class_teacher_classes(teacher_id)

        return {
            "teacher_id": teacher_id,
            "assigned_classes": assigned_classes,
            "class_teacher_of": class_teacher_classes,
        }

    def list_teachers(
        self,
        status: TeacherStatus | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List teachers with filtering and pagination.

        Args:
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
                status=status,
                page=page,
                page_size=page_size,
            )
        else:
            filters: dict[str, Any] = {}
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
                    "id": teacher.id,
                    "employee_id": teacher.employee_id,
                    "subjects": teacher.subjects,
                    "classes_assigned": teacher.classes_assigned,
                    "qualifications": teacher.qualifications,
                    "joining_date": teacher.joining_date.isoformat(),
                    "status": teacher.status.value,
                    "user": {
                        "id": teacher.user.id,
                        "email": teacher.user.email,
                        "profile_data": teacher.user.profile_data,
                    }
                    if teacher.user
                    else None,
                }
                for teacher in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
