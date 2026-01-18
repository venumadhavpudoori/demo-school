"""School repositories for Class, Section, and Subject data access operations.

This module provides repository classes that extend TenantAwareRepository
with school-specific query methods for classes, sections, and subjects.
"""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.school import Class, Section, Subject
from app.models.student import Student, StudentStatus
from app.repositories.base import PaginatedResult, TenantAwareRepository


class ClassRepository(TenantAwareRepository[Class]):
    """Repository for class data access operations.

    Extends TenantAwareRepository with class-specific methods for
    managing classes and their relationships.
    """

    model = Class

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the class repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Class]]:
        """Return base query with eager loading of class teacher relationship.

        Returns:
            A SQLAlchemy Select statement with class_teacher relationship loaded.
        """
        return (
            select(Class)
            .options(joinedload(Class.class_teacher))
            .where(Class.tenant_id == self.tenant_id)
        )

    def get_by_id_with_relations(self, id: int) -> Class | None:
        """Get class by ID with all relationships loaded.

        Args:
            id: The class ID.

        Returns:
            The class with relationships if found, None otherwise.
        """
        from app.models.teacher import Teacher
        from app.models.user import User
        
        stmt = (
            select(Class)
            .options(
                joinedload(Class.class_teacher).joinedload(Teacher.user),
                joinedload(Class.sections),
            )
            .where(
                Class.tenant_id == self.tenant_id,
                Class.id == id,
            )
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_name_and_year(
        self, name: str, academic_year: str
    ) -> Class | None:
        """Get class by name and academic year within tenant scope.

        Args:
            name: The class name.
            academic_year: The academic year.

        Returns:
            The class if found, None otherwise.
        """
        stmt = self.get_base_query().where(
            Class.name == name,
            Class.academic_year == academic_year,
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def list_by_academic_year(
        self,
        academic_year: str,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Class]:
        """List classes by academic year.

        Args:
            academic_year: The academic year to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the classes.
        """
        return self.list(
            filters={"academic_year": academic_year},
            page=page,
            page_size=page_size,
        )

    def get_sections(self, class_id: int) -> list[Section]:
        """Get all sections for a class.

        Args:
            class_id: The class ID.

        Returns:
            List of sections for the class.
        """
        stmt = (
            select(Section)
            .where(
                Section.tenant_id == self.tenant_id,
                Section.class_id == class_id,
            )
            .order_by(Section.name)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_subjects(self, class_id: int) -> list[Subject]:
        """Get all subjects for a class.

        Args:
            class_id: The class ID.

        Returns:
            List of subjects for the class.
        """
        stmt = (
            select(Subject)
            .options(joinedload(Subject.teacher))
            .where(
                Subject.tenant_id == self.tenant_id,
                Subject.class_id == class_id,
            )
            .order_by(Subject.name)
        )
        result = self.db.execute(stmt)
        return list(result.unique().scalars().all())

    def get_enrolled_students(
        self,
        class_id: int,
        section_id: int | None = None,
        include_inactive: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Student]:
        """Get students enrolled in a class.

        Args:
            class_id: The class ID.
            section_id: Optional section ID to filter by.
            include_inactive: Whether to include inactive students.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the students.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Build base query
        base_query = (
            select(Student)
            .options(joinedload(Student.user))
            .where(
                Student.tenant_id == self.tenant_id,
                Student.class_id == class_id,
            )
        )

        # Apply section filter
        if section_id is not None:
            base_query = base_query.where(Student.section_id == section_id)

        # Apply status filter
        if not include_inactive:
            base_query = base_query.where(Student.status == StudentStatus.ACTIVE)

        # Get total count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        base_query = base_query.order_by(Student.roll_number).offset(offset).limit(page_size)

        # Execute query
        result = self.db.execute(base_query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def class_name_exists(
        self,
        name: str,
        academic_year: str,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if class name already exists for the academic year within tenant.

        Args:
            name: The class name to check.
            academic_year: The academic year.
            exclude_id: Optional class ID to exclude from check (for updates).

        Returns:
            True if class name exists, False otherwise.
        """
        query = select(func.count()).where(
            Class.tenant_id == self.tenant_id,
            Class.name == name,
            Class.academic_year == academic_year,
        )
        if exclude_id is not None:
            query = query.where(Class.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0


class SectionRepository(TenantAwareRepository[Section]):
    """Repository for section data access operations.

    Extends TenantAwareRepository with section-specific methods.
    """

    model = Section

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the section repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Section]]:
        """Return base query with eager loading of class relationship.

        Returns:
            A SQLAlchemy Select statement with class relationship loaded.
        """
        return (
            select(Section)
            .options(joinedload(Section.class_))
            .where(Section.tenant_id == self.tenant_id)
        )

    def get_by_class_and_name(
        self, class_id: int, name: str
    ) -> Section | None:
        """Get section by class ID and name within tenant scope.

        Args:
            class_id: The class ID.
            name: The section name.

        Returns:
            The section if found, None otherwise.
        """
        stmt = self.get_base_query().where(
            Section.class_id == class_id,
            Section.name == name,
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def list_by_class(
        self,
        class_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Section]:
        """List sections by class.

        Args:
            class_id: The class ID to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the sections.
        """
        return self.list(
            filters={"class_id": class_id},
            page=page,
            page_size=page_size,
        )

    def section_name_exists(
        self,
        class_id: int,
        name: str,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if section name already exists for the class within tenant.

        Args:
            class_id: The class ID.
            name: The section name to check.
            exclude_id: Optional section ID to exclude from check (for updates).

        Returns:
            True if section name exists, False otherwise.
        """
        query = select(func.count()).where(
            Section.tenant_id == self.tenant_id,
            Section.class_id == class_id,
            Section.name == name,
        )
        if exclude_id is not None:
            query = query.where(Section.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0

    def update_student_count(self, section_id: int) -> int:
        """Update the student count for a section.

        Args:
            section_id: The section ID.

        Returns:
            The updated student count.
        """
        # Count active students in the section
        count_query = select(func.count()).where(
            Student.tenant_id == self.tenant_id,
            Student.section_id == section_id,
            Student.status == StudentStatus.ACTIVE,
        )
        count = self.db.execute(count_query).scalar() or 0

        # Update the section
        section = self.get_by_id(section_id)
        if section:
            section.students_count = count
            self.db.commit()

        return count


class SubjectRepository(TenantAwareRepository[Subject]):
    """Repository for subject data access operations.

    Extends TenantAwareRepository with subject-specific methods.
    """

    model = Subject

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the subject repository.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        super().__init__(db, tenant_id)

    def get_base_query(self) -> Select[tuple[Subject]]:
        """Return base query with eager loading of relationships.

        Returns:
            A SQLAlchemy Select statement with relationships loaded.
        """
        return (
            select(Subject)
            .options(
                joinedload(Subject.class_),
                joinedload(Subject.teacher),
            )
            .where(Subject.tenant_id == self.tenant_id)
        )

    def get_by_code(self, code: str) -> Subject | None:
        """Get subject by code within tenant scope.

        Args:
            code: The subject code.

        Returns:
            The subject if found, None otherwise.
        """
        stmt = self.get_base_query().where(Subject.code == code)
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def get_by_class_and_code(
        self, class_id: int, code: str
    ) -> Subject | None:
        """Get subject by class ID and code within tenant scope.

        Args:
            class_id: The class ID.
            code: The subject code.

        Returns:
            The subject if found, None otherwise.
        """
        stmt = self.get_base_query().where(
            Subject.class_id == class_id,
            Subject.code == code,
        )
        result = self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    def list_by_class(
        self,
        class_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Subject]:
        """List subjects by class.

        Args:
            class_id: The class ID to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the subjects.
        """
        return self.list(
            filters={"class_id": class_id},
            page=page,
            page_size=page_size,
        )

    def list_by_teacher(
        self,
        teacher_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[Subject]:
        """List subjects by teacher.

        Args:
            teacher_id: The teacher ID to filter by.
            page: The page number (1-indexed).
            page_size: The number of items per page.

        Returns:
            A PaginatedResult containing the subjects.
        """
        return self.list(
            filters={"teacher_id": teacher_id},
            page=page,
            page_size=page_size,
        )

    def subject_code_exists(
        self,
        class_id: int,
        code: str,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if subject code already exists for the class within tenant.

        Args:
            class_id: The class ID.
            code: The subject code to check.
            exclude_id: Optional subject ID to exclude from check (for updates).

        Returns:
            True if subject code exists, False otherwise.
        """
        query = select(func.count()).where(
            Subject.tenant_id == self.tenant_id,
            Subject.class_id == class_id,
            Subject.code == code,
        )
        if exclude_id is not None:
            query = query.where(Subject.id != exclude_id)

        count = self.db.execute(query).scalar() or 0
        return count > 0
