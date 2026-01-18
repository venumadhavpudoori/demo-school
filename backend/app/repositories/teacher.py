"""Teacher repository for data access operations.

This module provides the TeacherRepository class that extends TenantAwareRepository
with teacher-specific query methods.
"""

from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.school import Class
from app.models.teacher import Teacher, TeacherStatus
from app.models.user import User
from app.repositories.base import PaginatedResult, TenantAwareRepository


class TeacherRepository(TenantAwareRepository[Teacher]):
    """Repository for teacher data access operations.

    Extends TenantAwareRepository with teacher-specific methods for
    searching, filtering, and retrieving teacher data.
    """

    model = Teacher

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the teacher repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Teacher]]:
        """Return base query with eager loading of user relationship.

        Returns:
            A SQLAlchemy Select statement with user relationship loaded.
        """
        return (
            select(Teacher)
            .options(joinedload(Teacher.user))
            .where(Teacher.tenant_id == self.tenant_id)
        )

    def get_by_id_with_relations(self, id: int) -> Teacher | None:
        """Get teacher by ID with all relationships loaded.

        Args:
            id: The teacher ID.

        Returns:
            The teacher with relationships if found, None otherwise.
        """
        stmt = (
            select(Teacher)
            .options(joinedload(Teacher.user))
            .where(
                Teacher.tenant_id == self.tenant_id,
                Teacher.id == id,
            )
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_employee_id(self, employee_id: str) -> Teacher | None:
        """Get teacher by employee ID within tenant scope.

        Args:
            employee_id: The teacher's employee ID.

        Returns:
            The teacher if found, None otherwise.
        """
        stmt = self.get_base_query().where(Teacher.employee_id == employee_id)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Teacher | None:
        """Get teacher by user ID within tenant scope.

        Args:
            user_id: The associated user's ID.

        Returns:
            The teacher if found, None otherwise.
        """
        stmt = self.get_base_query().where(Teacher.user_id == user_id)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def search(
        self,
        query: str,
        status: TeacherStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Teacher]:
        """Search teachers by name, email, or employee ID.

        Args:
            query: Search query string.
            status: Optional status filter.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing matching teachers.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Build base query with join to User for name/email search
        base_query = (
            select(Teacher)
            .join(User, Teacher.user_id == User.id)
            .options(joinedload(Teacher.user))
            .where(Teacher.tenant_id == self.tenant_id)
        )

        # Apply search filter
        search_pattern = f"%{query}%"
        base_query = base_query.where(
            or_(
                Teacher.employee_id.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.profile_data["first_name"].astext.ilike(search_pattern),
                User.profile_data["last_name"].astext.ilike(search_pattern),
            )
        )

        # Apply status filter
        if status is not None:
            base_query = base_query.where(Teacher.status == status)

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(base_query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_assigned_classes(self, teacher_id: int) -> list[dict[str, Any]]:
        """Get classes assigned to a teacher.

        Args:
            teacher_id: The teacher ID.

        Returns:
            List of class information dictionaries.
        """
        teacher = self.get_by_id(teacher_id)
        if teacher is None or not teacher.classes_assigned:
            return []

        # Query classes by IDs
        stmt = (
            select(Class)
            .where(
                Class.tenant_id == self.tenant_id,
                Class.id.in_(teacher.classes_assigned),
            )
        )
        result = self.db.execute(stmt)
        classes = result.scalars().all()

        return [
            {
                "id": cls.id,
                "name": cls.name,
                "grade_level": cls.grade_level,
                "academic_year": cls.academic_year,
                "is_class_teacher": cls.class_teacher_id == teacher_id,
            }
            for cls in classes
        ]

    def get_class_teacher_classes(self, teacher_id: int) -> list[dict[str, Any]]:
        """Get classes where teacher is the class teacher.

        Args:
            teacher_id: The teacher ID.

        Returns:
            List of class information dictionaries.
        """
        stmt = (
            select(Class)
            .where(
                Class.tenant_id == self.tenant_id,
                Class.class_teacher_id == teacher_id,
            )
        )
        result = self.db.execute(stmt)
        classes = result.scalars().all()

        return [
            {
                "id": cls.id,
                "name": cls.name,
                "grade_level": cls.grade_level,
                "academic_year": cls.academic_year,
            }
            for cls in classes
        ]

    def employee_id_exists(
        self, employee_id: str, exclude_id: int | None = None
    ) -> bool:
        """Check if employee ID already exists within tenant.

        Args:
            employee_id: The employee ID to check.
            exclude_id: Optional teacher ID to exclude from check (for updates).

        Returns:
            True if employee ID exists, False otherwise.
        """
        query = select(func.count()).where(
            Teacher.tenant_id == self.tenant_id,
            Teacher.employee_id == employee_id,
        )
        if exclude_id is not None:
            query = query.where(Teacher.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0
