"""Background tasks for CSV bulk import operations.

This module provides Celery tasks for importing data from CSV files
with progress tracking, validation, and tenant context isolation.
"""

import csv
import io
import logging
import os
from datetime import date, datetime
from typing import Any

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_db_session() -> Session:
    """Create a new database session for background tasks."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_uploads_directory() -> str:
    """Get the directory for uploaded files."""
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    return uploads_dir


class CSVImportError(Exception):
    """Exception raised for CSV import errors."""

    def __init__(self, row: int, field: str, message: str):
        self.row = row
        self.field = field
        self.message = message
        super().__init__(f"Row {row}, Field '{field}': {message}")


class CSVValidator:
    """CSV data validator for import operations."""

    def __init__(self, tenant_id: int):
        """Initialize validator with tenant context.

        Args:
            tenant_id: The tenant ID for context.
        """
        self.tenant_id = tenant_id

    def validate_email(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            True if valid, False otherwise.
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_date(self, date_str: str, formats: list[str] | None = None) -> date | None:
        """Validate and parse date string.

        Args:
            date_str: Date string to parse.
            formats: List of date formats to try.

        Returns:
            Parsed date or None if invalid.
        """
        if not formats:
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def validate_required(self, value: str | None, field_name: str) -> str:
        """Validate required field is not empty.

        Args:
            value: Field value.
            field_name: Name of the field for error messages.

        Returns:
            Stripped value.

        Raises:
            ValueError: If field is empty.
        """
        if not value or not value.strip():
            raise ValueError(f"{field_name} is required")
        return value.strip()

    def validate_gender(self, gender: str) -> str:
        """Validate and normalize gender value.

        Args:
            gender: Gender string.

        Returns:
            Normalized gender value.

        Raises:
            ValueError: If gender is invalid.
        """
        gender_map = {
            "m": "male", "male": "male", "boy": "male",
            "f": "female", "female": "female", "girl": "female",
            "o": "other", "other": "other",
        }
        normalized = gender.lower().strip()
        if normalized not in gender_map:
            raise ValueError(f"Invalid gender: {gender}")
        return gender_map[normalized]

    def validate_attendance_status(self, status: str) -> str:
        """Validate and normalize attendance status.

        Args:
            status: Attendance status string.

        Returns:
            Normalized status value.

        Raises:
            ValueError: If status is invalid.
        """
        status_map = {
            "p": "present", "present": "present", "1": "present",
            "a": "absent", "absent": "absent", "0": "absent",
            "l": "late", "late": "late",
            "h": "half_day", "half_day": "half_day", "half": "half_day",
            "e": "excused", "excused": "excused",
        }
        normalized = status.lower().strip()
        if normalized not in status_map:
            raise ValueError(f"Invalid attendance status: {status}")
        return status_map[normalized]


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_students_csv",
    max_retries=3,
    default_retry_delay=60,
)
def import_students_csv(
    self,
    tenant_id: int,
    file_path: str,
    class_id: int,
    section_id: int,
    user_id: int,
    batch_size: int = 50,
) -> dict:
    """Import students from a CSV file with progress tracking.

    Expected CSV columns:
    - admission_number (required)
    - email (required)
    - first_name (required)
    - last_name (required)
    - date_of_birth (required, format: YYYY-MM-DD)
    - gender (required: male/female/other)
    - roll_number (optional)
    - address (optional)
    - password (optional, default generated)

    Args:
        tenant_id: The tenant ID.
        file_path: Path to the uploaded CSV file.
        class_id: Target class ID.
        section_id: Target section ID.
        user_id: ID of user performing the import.
        batch_size: Number of records to process per batch.

    Returns:
        dict with import status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting student CSV import: "
        f"file={file_path}, class={class_id}, section={section_id}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "processed": 0, "total": 0, "status": "Reading file..."},
        )

        # Read and parse CSV file
        if not os.path.exists(file_path):
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"File not found: {file_path}",
            }

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = len(rows)
        if total_rows == 0:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": 0,
                "successful": 0,
                "failed": 0,
                "message": "CSV file is empty",
            }

        self.update_state(
            state="PROGRESS",
            meta={"progress": 5, "processed": 0, "total": total_rows, "status": "Validating..."},
        )

        db = get_db_session()
        validator = CSVValidator(tenant_id)

        try:
            from app.models.student import Gender, Student, StudentStatus
            from app.models.user import User, UserRole
            from app.services.auth_service import AuthService

            auth_service = AuthService()
            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for i, row in enumerate(rows):
                row_num = i + 2  # Account for header row and 0-indexing

                try:
                    # Validate required fields
                    admission_number = validator.validate_required(
                        row.get("admission_number"), "admission_number"
                    )
                    email = validator.validate_required(row.get("email"), "email")
                    first_name = validator.validate_required(row.get("first_name"), "first_name")
                    last_name = validator.validate_required(row.get("last_name"), "last_name")
                    dob_str = validator.validate_required(row.get("date_of_birth"), "date_of_birth")
                    gender_str = validator.validate_required(row.get("gender"), "gender")

                    # Validate email format
                    if not validator.validate_email(email):
                        raise ValueError(f"Invalid email format: {email}")

                    # Parse date of birth
                    date_of_birth = validator.validate_date(dob_str)
                    if not date_of_birth:
                        raise ValueError(f"Invalid date format: {dob_str}")

                    # Validate gender
                    gender = validator.validate_gender(gender_str)

                    # Check for duplicate admission number
                    existing_student = db.execute(
                        select(Student).where(
                            Student.tenant_id == tenant_id,
                            Student.admission_number == admission_number,
                        )
                    ).scalar_one_or_none()

                    if existing_student:
                        raise ValueError(f"Admission number already exists: {admission_number}")

                    # Check for duplicate email
                    existing_user = db.execute(
                        select(User).where(User.email == email)
                    ).scalar_one_or_none()

                    if existing_user:
                        raise ValueError(f"Email already exists: {email}")

                    # Generate password if not provided
                    password = row.get("password", "").strip()
                    if not password:
                        password = f"Student@{admission_number}"

                    # Create user
                    user = User(
                        tenant_id=tenant_id,
                        email=email,
                        password_hash=auth_service.hash_password(password),
                        role=UserRole.STUDENT,
                        profile_data={
                            "first_name": first_name,
                            "last_name": last_name,
                        },
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()

                    # Create student
                    student = Student(
                        tenant_id=tenant_id,
                        user_id=user.id,
                        admission_number=admission_number,
                        class_id=class_id,
                        section_id=section_id,
                        roll_number=int(row.get("roll_number")) if row.get("roll_number") else None,
                        date_of_birth=date_of_birth,
                        gender=Gender(gender),
                        address=row.get("address", "").strip() or None,
                        admission_date=date.today(),
                        status=StudentStatus.ACTIVE,
                    )
                    db.add(student)
                    successful += 1

                    # Commit in batches
                    if successful % batch_size == 0:
                        db.commit()

                except Exception as e:
                    failed += 1
                    errors.append({
                        "row": row_num,
                        "admission_number": row.get("admission_number", ""),
                        "error": str(e),
                    })
                    db.rollback()

                # Update progress
                progress = int((i + 1) / total_rows * 95) + 5
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "processed": i + 1,
                        "total": total_rows,
                        "successful": successful,
                        "failed": failed,
                        "status": f"Processing row {i + 1}/{total_rows}",
                    },
                )

            # Final commit
            db.commit()

            logger.info(
                f"[Tenant {tenant_id}] Student import completed: "
                f"{successful} successful, {failed} failed"
            )

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": total_rows,
                "successful": successful,
                "failed": failed,
                "errors": errors[:100],  # Limit to first 100 errors
                "imported_by": user_id,
                "completed_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error importing students: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "error": str(e),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_teachers_csv",
    max_retries=3,
    default_retry_delay=60,
)
def import_teachers_csv(
    self,
    tenant_id: int,
    file_path: str,
    user_id: int,
    batch_size: int = 50,
) -> dict:
    """Import teachers from a CSV file.

    Expected CSV columns:
    - employee_id (required)
    - email (required)
    - first_name (required)
    - last_name (required)
    - joining_date (required, format: YYYY-MM-DD)
    - subjects (optional, comma-separated)
    - qualifications (optional)
    - password (optional, default generated)

    Args:
        tenant_id: The tenant ID.
        file_path: Path to the uploaded CSV file.
        user_id: ID of user performing the import.
        batch_size: Number of records to process per batch.

    Returns:
        dict with import status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting teacher CSV import: file={file_path}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "processed": 0, "total": 0, "status": "Reading file..."},
        )

        if not os.path.exists(file_path):
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"File not found: {file_path}",
            }

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = len(rows)
        if total_rows == 0:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": 0,
                "successful": 0,
                "failed": 0,
                "message": "CSV file is empty",
            }

        db = get_db_session()
        validator = CSVValidator(tenant_id)

        try:
            from app.models.teacher import Teacher, TeacherStatus
            from app.models.user import User, UserRole
            from app.services.auth_service import AuthService

            auth_service = AuthService()
            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for i, row in enumerate(rows):
                row_num = i + 2

                try:
                    # Validate required fields
                    employee_id = validator.validate_required(row.get("employee_id"), "employee_id")
                    email = validator.validate_required(row.get("email"), "email")
                    first_name = validator.validate_required(row.get("first_name"), "first_name")
                    last_name = validator.validate_required(row.get("last_name"), "last_name")
                    joining_date_str = validator.validate_required(
                        row.get("joining_date"), "joining_date"
                    )

                    if not validator.validate_email(email):
                        raise ValueError(f"Invalid email format: {email}")

                    joining_date = validator.validate_date(joining_date_str)
                    if not joining_date:
                        raise ValueError(f"Invalid date format: {joining_date_str}")

                    # Check for duplicates
                    existing_teacher = db.execute(
                        select(Teacher).where(
                            Teacher.tenant_id == tenant_id,
                            Teacher.employee_id == employee_id,
                        )
                    ).scalar_one_or_none()

                    if existing_teacher:
                        raise ValueError(f"Employee ID already exists: {employee_id}")

                    existing_user = db.execute(
                        select(User).where(User.email == email)
                    ).scalar_one_or_none()

                    if existing_user:
                        raise ValueError(f"Email already exists: {email}")

                    # Parse subjects
                    subjects_str = row.get("subjects", "").strip()
                    subjects = [s.strip() for s in subjects_str.split(",") if s.strip()] if subjects_str else None

                    # Generate password
                    password = row.get("password", "").strip()
                    if not password:
                        password = f"Teacher@{employee_id}"

                    # Create user
                    user = User(
                        tenant_id=tenant_id,
                        email=email,
                        password_hash=auth_service.hash_password(password),
                        role=UserRole.TEACHER,
                        profile_data={
                            "first_name": first_name,
                            "last_name": last_name,
                        },
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()

                    # Create teacher
                    teacher = Teacher(
                        tenant_id=tenant_id,
                        user_id=user.id,
                        employee_id=employee_id,
                        subjects=subjects,
                        qualifications=row.get("qualifications", "").strip() or None,
                        joining_date=joining_date,
                        status=TeacherStatus.ACTIVE,
                    )
                    db.add(teacher)
                    successful += 1

                    if successful % batch_size == 0:
                        db.commit()

                except Exception as e:
                    failed += 1
                    errors.append({
                        "row": row_num,
                        "employee_id": row.get("employee_id", ""),
                        "error": str(e),
                    })
                    db.rollback()

                progress = int((i + 1) / total_rows * 95) + 5
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "processed": i + 1,
                        "total": total_rows,
                        "successful": successful,
                        "failed": failed,
                    },
                )

            db.commit()

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": total_rows,
                "successful": successful,
                "failed": failed,
                "errors": errors[:100],
                "imported_by": user_id,
                "completed_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error importing teachers: {e}", exc_info=True)
        return {"status": "failed", "tenant_id": tenant_id, "error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_attendance_csv",
    max_retries=3,
    default_retry_delay=60,
)
def import_attendance_csv(
    self,
    tenant_id: int,
    file_path: str,
    class_id: int,
    attendance_date: str,
    user_id: int,
    batch_size: int = 100,
) -> dict:
    """Import attendance records from a CSV file.

    Expected CSV columns:
    - admission_number OR student_id (required)
    - status (required: present/absent/late/half_day/excused)
    - remarks (optional)

    Args:
        tenant_id: The tenant ID.
        file_path: Path to the uploaded CSV file.
        class_id: Class ID for attendance.
        attendance_date: Date for attendance records (ISO format).
        user_id: ID of user performing the import.
        batch_size: Number of records to process per batch.

    Returns:
        dict with import status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting attendance CSV import: "
        f"file={file_path}, class={class_id}, date={attendance_date}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "processed": 0, "total": 0, "status": "Reading file..."},
        )

        if not os.path.exists(file_path):
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"File not found: {file_path}",
            }

        # Parse attendance date
        try:
            att_date = date.fromisoformat(attendance_date)
        except ValueError:
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"Invalid date format: {attendance_date}",
            }

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = len(rows)
        if total_rows == 0:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": 0,
                "successful": 0,
                "failed": 0,
                "message": "CSV file is empty",
            }

        db = get_db_session()
        validator = CSVValidator(tenant_id)

        try:
            from app.models.attendance import Attendance, AttendanceStatus
            from app.models.student import Student
            from app.models.teacher import Teacher

            # Get teacher ID for marked_by
            teacher = db.execute(
                select(Teacher).where(
                    Teacher.tenant_id == tenant_id,
                    Teacher.user_id == user_id,
                )
            ).scalar_one_or_none()

            marked_by = teacher.id if teacher else None

            # Build student lookup map
            students = db.execute(
                select(Student).where(
                    Student.tenant_id == tenant_id,
                    Student.class_id == class_id,
                )
            ).scalars().all()

            student_by_admission = {s.admission_number: s for s in students}
            student_by_id = {s.id: s for s in students}

            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for i, row in enumerate(rows):
                row_num = i + 2

                try:
                    # Find student
                    student = None
                    if row.get("student_id"):
                        student_id = int(row["student_id"])
                        student = student_by_id.get(student_id)
                    elif row.get("admission_number"):
                        admission_number = row["admission_number"].strip()
                        student = student_by_admission.get(admission_number)

                    if not student:
                        raise ValueError("Student not found")

                    # Validate status
                    status_str = validator.validate_required(row.get("status"), "status")
                    status = validator.validate_attendance_status(status_str)

                    # Check for existing attendance record
                    existing = db.execute(
                        select(Attendance).where(
                            Attendance.tenant_id == tenant_id,
                            Attendance.student_id == student.id,
                            Attendance.date == att_date,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Update existing record
                        existing.status = AttendanceStatus(status)
                        existing.remarks = row.get("remarks", "").strip() or None
                        existing.marked_by = marked_by
                    else:
                        # Create new record
                        attendance = Attendance(
                            tenant_id=tenant_id,
                            student_id=student.id,
                            class_id=class_id,
                            date=att_date,
                            status=AttendanceStatus(status),
                            marked_by=marked_by,
                            remarks=row.get("remarks", "").strip() or None,
                        )
                        db.add(attendance)

                    successful += 1

                    if successful % batch_size == 0:
                        db.commit()

                except Exception as e:
                    failed += 1
                    errors.append({
                        "row": row_num,
                        "student": row.get("admission_number") or row.get("student_id", ""),
                        "error": str(e),
                    })
                    db.rollback()

                progress = int((i + 1) / total_rows * 95) + 5
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "processed": i + 1,
                        "total": total_rows,
                        "successful": successful,
                        "failed": failed,
                    },
                )

            db.commit()

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "class_id": class_id,
                "date": attendance_date,
                "total_rows": total_rows,
                "successful": successful,
                "failed": failed,
                "errors": errors[:100],
                "imported_by": user_id,
                "completed_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error importing attendance: {e}", exc_info=True)
        return {"status": "failed", "tenant_id": tenant_id, "error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_grades_csv",
    max_retries=3,
    default_retry_delay=60,
)
def import_grades_csv(
    self,
    tenant_id: int,
    file_path: str,
    exam_id: int,
    subject_id: int,
    user_id: int,
    batch_size: int = 100,
) -> dict:
    """Import grade records from a CSV file.

    Expected CSV columns:
    - admission_number OR student_id (required)
    - marks_obtained (required)
    - max_marks (required)
    - remarks (optional)

    Args:
        tenant_id: The tenant ID.
        file_path: Path to the uploaded CSV file.
        exam_id: Exam ID for grades.
        subject_id: Subject ID for grades.
        user_id: ID of user performing the import.
        batch_size: Number of records to process per batch.

    Returns:
        dict with import status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting grades CSV import: "
        f"file={file_path}, exam={exam_id}, subject={subject_id}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "processed": 0, "total": 0, "status": "Reading file..."},
        )

        if not os.path.exists(file_path):
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"File not found: {file_path}",
            }

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = len(rows)
        if total_rows == 0:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": 0,
                "successful": 0,
                "failed": 0,
                "message": "CSV file is empty",
            }

        db = get_db_session()
        validator = CSVValidator(tenant_id)

        try:
            from decimal import Decimal, InvalidOperation

            from app.models.exam import Exam, Grade
            from app.models.student import Student

            # Verify exam exists
            exam = db.execute(
                select(Exam).where(
                    Exam.id == exam_id,
                    Exam.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()

            if not exam:
                return {
                    "status": "failed",
                    "tenant_id": tenant_id,
                    "error": f"Exam not found: {exam_id}",
                }

            # Build student lookup
            students = db.execute(
                select(Student).where(
                    Student.tenant_id == tenant_id,
                    Student.class_id == exam.class_id,
                )
            ).scalars().all()

            student_by_admission = {s.admission_number: s for s in students}
            student_by_id = {s.id: s for s in students}

            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for i, row in enumerate(rows):
                row_num = i + 2

                try:
                    # Find student
                    student = None
                    if row.get("student_id"):
                        student_id = int(row["student_id"])
                        student = student_by_id.get(student_id)
                    elif row.get("admission_number"):
                        admission_number = row["admission_number"].strip()
                        student = student_by_admission.get(admission_number)

                    if not student:
                        raise ValueError("Student not found")

                    # Validate marks
                    marks_str = validator.validate_required(row.get("marks_obtained"), "marks_obtained")
                    max_marks_str = validator.validate_required(row.get("max_marks"), "max_marks")

                    try:
                        marks_obtained = Decimal(marks_str)
                        max_marks = Decimal(max_marks_str)
                    except InvalidOperation:
                        raise ValueError("Invalid marks format")

                    if marks_obtained < 0 or max_marks <= 0:
                        raise ValueError("Invalid marks values")

                    if marks_obtained > max_marks:
                        raise ValueError("Marks obtained cannot exceed max marks")

                    # Calculate grade letter
                    percentage = float(marks_obtained) / float(max_marks) * 100
                    grade_letter = _calculate_grade_letter(percentage)

                    # Check for existing grade
                    existing = db.execute(
                        select(Grade).where(
                            Grade.tenant_id == tenant_id,
                            Grade.student_id == student.id,
                            Grade.exam_id == exam_id,
                            Grade.subject_id == subject_id,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        # Update existing
                        existing.marks_obtained = marks_obtained
                        existing.max_marks = max_marks
                        existing.grade = grade_letter
                        existing.remarks = row.get("remarks", "").strip() or None
                    else:
                        # Create new
                        grade = Grade(
                            tenant_id=tenant_id,
                            student_id=student.id,
                            subject_id=subject_id,
                            exam_id=exam_id,
                            marks_obtained=marks_obtained,
                            max_marks=max_marks,
                            grade=grade_letter,
                            remarks=row.get("remarks", "").strip() or None,
                        )
                        db.add(grade)

                    successful += 1

                    if successful % batch_size == 0:
                        db.commit()

                except Exception as e:
                    failed += 1
                    errors.append({
                        "row": row_num,
                        "student": row.get("admission_number") or row.get("student_id", ""),
                        "error": str(e),
                    })
                    db.rollback()

                progress = int((i + 1) / total_rows * 95) + 5
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "processed": i + 1,
                        "total": total_rows,
                        "successful": successful,
                        "failed": failed,
                    },
                )

            db.commit()

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "exam_id": exam_id,
                "subject_id": subject_id,
                "total_rows": total_rows,
                "successful": successful,
                "failed": failed,
                "errors": errors[:100],
                "imported_by": user_id,
                "completed_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error importing grades: {e}", exc_info=True)
        return {"status": "failed", "tenant_id": tenant_id, "error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.imports.import_fees_csv",
    max_retries=3,
    default_retry_delay=60,
)
def import_fees_csv(
    self,
    tenant_id: int,
    file_path: str,
    academic_year: str,
    user_id: int,
    batch_size: int = 100,
) -> dict:
    """Import fee records from a CSV file.

    Expected CSV columns:
    - admission_number OR student_id (required)
    - fee_type (required)
    - amount (required)
    - due_date (required, format: YYYY-MM-DD)

    Args:
        tenant_id: The tenant ID.
        file_path: Path to the uploaded CSV file.
        academic_year: Academic year for fees.
        user_id: ID of user performing the import.
        batch_size: Number of records to process per batch.

    Returns:
        dict with import status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting fees CSV import: "
        f"file={file_path}, academic_year={academic_year}"
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "processed": 0, "total": 0, "status": "Reading file..."},
        )

        if not os.path.exists(file_path):
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": f"File not found: {file_path}",
            }

        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        total_rows = len(rows)
        if total_rows == 0:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "total_rows": 0,
                "successful": 0,
                "failed": 0,
                "message": "CSV file is empty",
            }

        db = get_db_session()
        validator = CSVValidator(tenant_id)

        try:
            from decimal import Decimal, InvalidOperation

            from app.models.fee import Fee, FeeStatus
            from app.models.student import Student

            # Build student lookup
            students = db.execute(
                select(Student).where(Student.tenant_id == tenant_id)
            ).scalars().all()

            student_by_admission = {s.admission_number: s for s in students}
            student_by_id = {s.id: s for s in students}

            successful = 0
            failed = 0
            errors: list[dict[str, Any]] = []

            for i, row in enumerate(rows):
                row_num = i + 2

                try:
                    # Find student
                    student = None
                    if row.get("student_id"):
                        student_id = int(row["student_id"])
                        student = student_by_id.get(student_id)
                    elif row.get("admission_number"):
                        admission_number = row["admission_number"].strip()
                        student = student_by_admission.get(admission_number)

                    if not student:
                        raise ValueError("Student not found")

                    # Validate fields
                    fee_type = validator.validate_required(row.get("fee_type"), "fee_type")
                    amount_str = validator.validate_required(row.get("amount"), "amount")
                    due_date_str = validator.validate_required(row.get("due_date"), "due_date")

                    try:
                        amount = Decimal(amount_str)
                    except InvalidOperation:
                        raise ValueError("Invalid amount format")

                    if amount <= 0:
                        raise ValueError("Amount must be positive")

                    due_date = validator.validate_date(due_date_str)
                    if not due_date:
                        raise ValueError(f"Invalid date format: {due_date_str}")

                    # Create fee record
                    fee = Fee(
                        tenant_id=tenant_id,
                        student_id=student.id,
                        fee_type=fee_type,
                        amount=amount,
                        due_date=due_date,
                        paid_amount=Decimal("0.00"),
                        status=FeeStatus.PENDING,
                        academic_year=academic_year,
                    )
                    db.add(fee)
                    successful += 1

                    if successful % batch_size == 0:
                        db.commit()

                except Exception as e:
                    failed += 1
                    errors.append({
                        "row": row_num,
                        "student": row.get("admission_number") or row.get("student_id", ""),
                        "error": str(e),
                    })
                    db.rollback()

                progress = int((i + 1) / total_rows * 95) + 5
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "processed": i + 1,
                        "total": total_rows,
                        "successful": successful,
                        "failed": failed,
                    },
                )

            db.commit()

            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "academic_year": academic_year,
                "total_rows": total_rows,
                "successful": successful,
                "failed": failed,
                "errors": errors[:100],
                "imported_by": user_id,
                "completed_at": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error importing fees: {e}", exc_info=True)
        return {"status": "failed", "tenant_id": tenant_id, "error": str(e)}


def _calculate_grade_letter(percentage: float) -> str:
    """Calculate grade letter from percentage."""
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B+"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C+"
    elif percentage >= 40:
        return "C"
    elif percentage >= 33:
        return "D"
    else:
        return "F"
