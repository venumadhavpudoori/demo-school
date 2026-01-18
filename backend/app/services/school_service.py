"""School services for class, section, and subject business logic operations.

This module provides service classes that handle all business logic
related to class, section, and subject management including CRUD operations.
"""

from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from app.models.school import Class, Section, Subject
from app.repositories.school import ClassRepository, SectionRepository, SubjectRepository
from app.services.cache_service import CacheService


# ============================================================================
# Exception Classes
# ============================================================================


class SchoolServiceError(Exception):
    """Base exception for school service errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ClassNotFoundError(SchoolServiceError):
    """Raised when a class is not found."""

    def __init__(self, class_id: int):
        super().__init__(
            message=f"Class with ID {class_id} not found",
            code="CLASS_NOT_FOUND",
        )


class DuplicateClassNameError(SchoolServiceError):
    """Raised when class name already exists for the academic year."""

    def __init__(self, name: str, academic_year: str):
        super().__init__(
            message=f"Class '{name}' already exists for academic year {academic_year}",
            code="DUPLICATE_CLASS_NAME",
        )


class SectionNotFoundError(SchoolServiceError):
    """Raised when a section is not found."""

    def __init__(self, section_id: int):
        super().__init__(
            message=f"Section with ID {section_id} not found",
            code="SECTION_NOT_FOUND",
        )


class DuplicateSectionNameError(SchoolServiceError):
    """Raised when section name already exists for the class."""

    def __init__(self, name: str, class_id: int):
        super().__init__(
            message=f"Section '{name}' already exists for class ID {class_id}",
            code="DUPLICATE_SECTION_NAME",
        )


class SubjectNotFoundError(SchoolServiceError):
    """Raised when a subject is not found."""

    def __init__(self, subject_id: int):
        super().__init__(
            message=f"Subject with ID {subject_id} not found",
            code="SUBJECT_NOT_FOUND",
        )


class DuplicateSubjectCodeError(SchoolServiceError):
    """Raised when subject code already exists for the class."""

    def __init__(self, code: str, class_id: int):
        super().__init__(
            message=f"Subject code '{code}' already exists for class ID {class_id}",
            code="DUPLICATE_SUBJECT_CODE",
        )


# ============================================================================
# Class Service
# ============================================================================


class ClassService:
    """Service class for class business logic.

    Handles all business operations related to classes including
    creation, updates, deletion, and retrieval.
    """

    # Cache TTL in seconds (5 minutes for class lists)
    CACHE_TTL = 300
    # Cache entity names
    CACHE_ENTITY_CLASS_LIST = "class_list"
    CACHE_ENTITY_CLASS = "class"
    CACHE_ENTITY_CLASS_SECTIONS = "class_sections"
    CACHE_ENTITY_CLASS_SUBJECTS = "class_subjects"

    def __init__(self, db: Session, tenant_id: int, redis: Redis | None = None):
        """Initialize the class service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
            redis: Optional Redis client for caching.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = ClassRepository(db, tenant_id)
        self.section_repository = SectionRepository(db, tenant_id)
        self.redis = redis
        self.cache = CacheService(redis, tenant_id) if redis else None

    def create_class(
        self,
        name: str,
        grade_level: int,
        academic_year: str,
        class_teacher_id: int | None = None,
    ) -> Class:
        """Create a new class.

        Args:
            name: The class name.
            grade_level: The grade level.
            academic_year: The academic year.
            class_teacher_id: Optional class teacher ID.

        Returns:
            The created Class object.

        Raises:
            DuplicateClassNameError: If class name exists for the academic year.
        """
        # Check for duplicate class name
        if self.repository.class_name_exists(name, academic_year):
            raise DuplicateClassNameError(name, academic_year)

        # Create class
        class_obj = self.repository.create({
            "name": name,
            "grade_level": grade_level,
            "academic_year": academic_year,
            "class_teacher_id": class_teacher_id,
        })

        # Invalidate class list cache
        self._invalidate_class_list_cache()

        return class_obj

    def _invalidate_class_list_cache(self) -> None:
        """Invalidate all class list cache entries for the tenant."""
        if self.cache:
            self.cache.invalidate_pattern(self.CACHE_ENTITY_CLASS_LIST)

    def _invalidate_class_cache(self, class_id: int) -> None:
        """Invalidate cache entries for a specific class.

        Args:
            class_id: The class ID to invalidate cache for.
        """
        if self.cache:
            # Invalidate individual class cache
            self.cache.invalidate(self.CACHE_ENTITY_CLASS, str(class_id))
            # Invalidate class sections cache
            self.cache.invalidate(self.CACHE_ENTITY_CLASS_SECTIONS, str(class_id))
            # Invalidate class subjects cache
            self.cache.invalidate(self.CACHE_ENTITY_CLASS_SUBJECTS, str(class_id))
            # Invalidate class list cache
            self._invalidate_class_list_cache()

    def _get_class_list_cache_key(
        self,
        academic_year: str | None,
        page: int,
        page_size: int,
    ) -> str:
        """Generate cache key for class list query.

        Args:
            academic_year: Optional academic year filter.
            page: Page number.
            page_size: Page size.

        Returns:
            Cache key string.
        """
        return f"{academic_year or 'all'}:{page}:{page_size}"

    def get_class(self, class_id: int) -> Class:
        """Get a class by ID.

        Args:
            class_id: The class ID.

        Returns:
            The Class object.

        Raises:
            ClassNotFoundError: If class not found.
        """
        class_obj = self.repository.get_by_id_with_relations(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)
        return class_obj

    def update_class(
        self,
        class_id: int,
        name: str | None = None,
        grade_level: int | None = None,
        academic_year: str | None = None,
        class_teacher_id: int | None = None,
    ) -> Class:
        """Update a class.

        Args:
            class_id: The class ID.
            name: Optional new name.
            grade_level: Optional new grade level.
            academic_year: Optional new academic year.
            class_teacher_id: Optional new class teacher ID.

        Returns:
            The updated Class object.

        Raises:
            ClassNotFoundError: If class not found.
            DuplicateClassNameError: If new name exists for the academic year.
        """
        class_obj = self.repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        # Check for duplicate name if changing
        new_name = name if name is not None else class_obj.name
        new_year = academic_year if academic_year is not None else class_obj.academic_year
        if (name is not None or academic_year is not None):
            if self.repository.class_name_exists(new_name, new_year, exclude_id=class_id):
                raise DuplicateClassNameError(new_name, new_year)

        # Build update data
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if grade_level is not None:
            update_data["grade_level"] = grade_level
        if academic_year is not None:
            update_data["academic_year"] = academic_year
        if class_teacher_id is not None:
            update_data["class_teacher_id"] = class_teacher_id

        if update_data:
            class_obj = self.repository.update(class_id, update_data)
            # Invalidate cache after update
            self._invalidate_class_cache(class_id)

        return class_obj

    def delete_class(self, class_id: int) -> bool:
        """Delete a class.

        Args:
            class_id: The class ID.

        Returns:
            True if deleted successfully.

        Raises:
            ClassNotFoundError: If class not found.
        """
        class_obj = self.repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        result = self.repository.hard_delete(class_id)

        # Invalidate cache after delete
        self._invalidate_class_cache(class_id)

        return result

    def list_classes(
        self,
        academic_year: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List classes with filtering and pagination.

        Args:
            academic_year: Optional academic year filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        # Try to get from cache first
        if self.cache:
            cache_key = self._get_class_list_cache_key(academic_year, page, page_size)
            cached_result = self.cache.get(self.CACHE_ENTITY_CLASS_LIST, cache_key)
            if cached_result is not None:
                return cached_result

        filters: dict[str, Any] = {}
        if academic_year is not None:
            filters["academic_year"] = academic_year

        result = self.repository.list(
            filters=filters,
            page=page,
            page_size=page_size,
        )

        response = {
            "items": [],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
        
        for cls in result.items:
            # Build class teacher data safely
            class_teacher_data = None
            if cls.class_teacher:
                class_teacher_data = {
                    "id": cls.class_teacher.id,
                    "employee_id": cls.class_teacher.employee_id,
                    "user": None,
                }
                if cls.class_teacher.user:
                    class_teacher_data["user"] = {
                        "email": cls.class_teacher.user.email,
                        "profile_data": cls.class_teacher.user.profile_data,
                    }
            
            response["items"].append({
                "id": cls.id,
                "name": cls.name,
                "grade_level": cls.grade_level,
                "academic_year": cls.academic_year,
                "class_teacher_id": cls.class_teacher_id,
                "class_teacher": class_teacher_data,
                "created_at": cls.created_at.isoformat() if cls.created_at else None,
                "updated_at": cls.updated_at.isoformat() if cls.updated_at else None,
            })

        # Cache the result
        if self.cache:
            cache_key = self._get_class_list_cache_key(academic_year, page, page_size)
            self.cache.set(self.CACHE_ENTITY_CLASS_LIST, cache_key, response, self.CACHE_TTL)

        return response

    def get_class_sections(self, class_id: int) -> list[dict[str, Any]]:
        """Get all sections for a class.

        Args:
            class_id: The class ID.

        Returns:
            List of section dictionaries.

        Raises:
            ClassNotFoundError: If class not found.
        """
        class_obj = self.repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        sections = self.repository.get_sections(class_id)
        return [
            {
                "id": section.id,
                "name": section.name,
                "capacity": section.capacity,
                "students_count": section.students_count,
            }
            for section in sections
        ]

    def get_class_subjects(self, class_id: int) -> list[dict[str, Any]]:
        """Get all subjects for a class.

        Args:
            class_id: The class ID.

        Returns:
            List of subject dictionaries.

        Raises:
            ClassNotFoundError: If class not found.
        """
        class_obj = self.repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        subjects = self.repository.get_subjects(class_id)
        return [
            {
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "credits": subject.credits,
                "teacher_id": subject.teacher_id,
                "teacher": {
                    "id": subject.teacher.id,
                    "employee_id": subject.teacher.employee_id,
                    "user": {
                        "email": subject.teacher.user.email,
                        "profile_data": subject.teacher.user.profile_data,
                    } if subject.teacher.user else None,
                } if subject.teacher else None,
            }
            for subject in subjects
        ]

    def get_enrolled_students(
        self,
        class_id: int,
        section_id: int | None = None,
        include_inactive: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get students enrolled in a class.

        Args:
            class_id: The class ID.
            section_id: Optional section ID to filter by.
            include_inactive: Whether to include inactive students.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.

        Raises:
            ClassNotFoundError: If class not found.
        """
        class_obj = self.repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        result = self.repository.get_enrolled_students(
            class_id=class_id,
            section_id=section_id,
            include_inactive=include_inactive,
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


# ============================================================================
# Section Service
# ============================================================================


class SectionService:
    """Service class for section business logic.

    Handles all business operations related to sections including
    creation, updates, deletion, and retrieval.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the section service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = SectionRepository(db, tenant_id)
        self.class_repository = ClassRepository(db, tenant_id)

    def create_section(
        self,
        class_id: int,
        name: str,
        capacity: int = 40,
    ) -> Section:
        """Create a new section.

        Args:
            class_id: The class ID.
            name: The section name.
            capacity: The section capacity.

        Returns:
            The created Section object.

        Raises:
            ClassNotFoundError: If class not found.
            DuplicateSectionNameError: If section name exists for the class.
        """
        # Check if class exists
        class_obj = self.class_repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        # Check for duplicate section name
        if self.repository.section_name_exists(class_id, name):
            raise DuplicateSectionNameError(name, class_id)

        # Create section
        section = self.repository.create({
            "class_id": class_id,
            "name": name,
            "capacity": capacity,
            "students_count": 0,
        })

        return section

    def get_section(self, section_id: int) -> Section:
        """Get a section by ID.

        Args:
            section_id: The section ID.

        Returns:
            The Section object.

        Raises:
            SectionNotFoundError: If section not found.
        """
        section = self.repository.get_by_id(section_id)
        if section is None:
            raise SectionNotFoundError(section_id)
        return section

    def update_section(
        self,
        section_id: int,
        name: str | None = None,
        capacity: int | None = None,
    ) -> Section:
        """Update a section.

        Args:
            section_id: The section ID.
            name: Optional new name.
            capacity: Optional new capacity.

        Returns:
            The updated Section object.

        Raises:
            SectionNotFoundError: If section not found.
            DuplicateSectionNameError: If new name exists for the class.
        """
        section = self.repository.get_by_id(section_id)
        if section is None:
            raise SectionNotFoundError(section_id)

        # Check for duplicate name if changing
        if name is not None and name != section.name:
            if self.repository.section_name_exists(section.class_id, name, exclude_id=section_id):
                raise DuplicateSectionNameError(name, section.class_id)

        # Build update data
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if capacity is not None:
            update_data["capacity"] = capacity

        if update_data:
            section = self.repository.update(section_id, update_data)

        return section

    def delete_section(self, section_id: int) -> bool:
        """Delete a section.

        Args:
            section_id: The section ID.

        Returns:
            True if deleted successfully.

        Raises:
            SectionNotFoundError: If section not found.
        """
        section = self.repository.get_by_id(section_id)
        if section is None:
            raise SectionNotFoundError(section_id)

        return self.repository.hard_delete(section_id)

    def list_sections(
        self,
        class_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List sections with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        filters: dict[str, Any] = {}
        if class_id is not None:
            filters["class_id"] = class_id

        result = self.repository.list(
            filters=filters,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                {
                    "id": section.id,
                    "class_id": section.class_id,
                    "class_name": section.class_.name if section.class_ else None,
                    "name": section.name,
                    "capacity": section.capacity,
                    "students_count": section.students_count,
                    "created_at": section.created_at.isoformat() if section.created_at else None,
                    "updated_at": section.updated_at.isoformat() if section.updated_at else None,
                }
                for section in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }


# ============================================================================
# Subject Service
# ============================================================================


class SubjectService:
    """Service class for subject business logic.

    Handles all business operations related to subjects including
    creation, updates, deletion, and retrieval.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the subject service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = SubjectRepository(db, tenant_id)
        self.class_repository = ClassRepository(db, tenant_id)

    def create_subject(
        self,
        class_id: int,
        name: str,
        code: str,
        credits: int = 1,
        teacher_id: int | None = None,
    ) -> Subject:
        """Create a new subject.

        Args:
            class_id: The class ID.
            name: The subject name.
            code: The subject code.
            credits: The subject credits.
            teacher_id: Optional teacher ID.

        Returns:
            The created Subject object.

        Raises:
            ClassNotFoundError: If class not found.
            DuplicateSubjectCodeError: If subject code exists for the class.
        """
        # Check if class exists
        class_obj = self.class_repository.get_by_id(class_id)
        if class_obj is None:
            raise ClassNotFoundError(class_id)

        # Check for duplicate subject code
        if self.repository.subject_code_exists(class_id, code):
            raise DuplicateSubjectCodeError(code, class_id)

        # Create subject
        subject = self.repository.create({
            "class_id": class_id,
            "name": name,
            "code": code,
            "credits": credits,
            "teacher_id": teacher_id,
        })

        return subject

    def get_subject(self, subject_id: int) -> Subject:
        """Get a subject by ID.

        Args:
            subject_id: The subject ID.

        Returns:
            The Subject object.

        Raises:
            SubjectNotFoundError: If subject not found.
        """
        subject = self.repository.get_by_id(subject_id)
        if subject is None:
            raise SubjectNotFoundError(subject_id)
        return subject

    def update_subject(
        self,
        subject_id: int,
        name: str | None = None,
        code: str | None = None,
        credits: int | None = None,
        teacher_id: int | None = None,
    ) -> Subject:
        """Update a subject.

        Args:
            subject_id: The subject ID.
            name: Optional new name.
            code: Optional new code.
            credits: Optional new credits.
            teacher_id: Optional new teacher ID.

        Returns:
            The updated Subject object.

        Raises:
            SubjectNotFoundError: If subject not found.
            DuplicateSubjectCodeError: If new code exists for the class.
        """
        subject = self.repository.get_by_id(subject_id)
        if subject is None:
            raise SubjectNotFoundError(subject_id)

        # Check for duplicate code if changing
        if code is not None and code != subject.code:
            if self.repository.subject_code_exists(subject.class_id, code, exclude_id=subject_id):
                raise DuplicateSubjectCodeError(code, subject.class_id)

        # Build update data
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if code is not None:
            update_data["code"] = code
        if credits is not None:
            update_data["credits"] = credits
        if teacher_id is not None:
            update_data["teacher_id"] = teacher_id

        if update_data:
            subject = self.repository.update(subject_id, update_data)

        return subject

    def delete_subject(self, subject_id: int) -> bool:
        """Delete a subject.

        Args:
            subject_id: The subject ID.

        Returns:
            True if deleted successfully.

        Raises:
            SubjectNotFoundError: If subject not found.
        """
        subject = self.repository.get_by_id(subject_id)
        if subject is None:
            raise SubjectNotFoundError(subject_id)

        return self.repository.hard_delete(subject_id)

    def list_subjects(
        self,
        class_id: int | None = None,
        teacher_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List subjects with filtering and pagination.

        Args:
            class_id: Optional class ID filter.
            teacher_id: Optional teacher ID filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with items and pagination metadata.
        """
        filters: dict[str, Any] = {}
        if class_id is not None:
            filters["class_id"] = class_id
        if teacher_id is not None:
            filters["teacher_id"] = teacher_id

        result = self.repository.list(
            filters=filters,
            page=page,
            page_size=page_size,
        )

        return {
            "items": [
                {
                    "id": subject.id,
                    "class_id": subject.class_id,
                    "class_name": subject.class_.name if subject.class_ else None,
                    "name": subject.name,
                    "code": subject.code,
                    "credits": subject.credits,
                    "teacher_id": subject.teacher_id,
                    "teacher": {
                        "id": subject.teacher.id,
                        "employee_id": subject.teacher.employee_id,
                        "user": {
                            "email": subject.teacher.user.email,
                            "profile_data": subject.teacher.user.profile_data,
                        } if subject.teacher.user else None,
                    } if subject.teacher else None,
                    "created_at": subject.created_at.isoformat() if subject.created_at else None,
                    "updated_at": subject.updated_at.isoformat() if subject.updated_at else None,
                }
                for subject in result.items
            ],
            "total_count": result.total_count,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "has_next": result.has_next,
            "has_previous": result.has_previous,
        }
