# Models package - SQLAlchemy models

from app.models.announcement import Announcement, TargetAudience
from app.models.attendance import Attendance, AttendanceStatus
from app.models.audit_log import AuditAction, AuditLog
from app.models.base import Base, TenantAwareBase, TenantMixin, TimestampMixin
from app.models.exam import Exam, ExamType, Grade
from app.models.fee import Fee, FeeStatus
from app.models.leave_request import LeaveRequest, LeaveStatus, RequesterType
from app.models.school import Class, Section, Subject
from app.models.student import Gender, Student, StudentStatus
from app.models.teacher import Teacher, TeacherStatus
from app.models.tenant import Tenant
from app.models.timetable import Timetable
from app.models.user import User, UserRole

__all__ = [
    # Base classes
    "Base",
    "TenantAwareBase",
    "TenantMixin",
    "TimestampMixin",
    # Models
    "Tenant",
    "User",
    "UserRole",
    "Student",
    "StudentStatus",
    "Gender",
    "Teacher",
    "TeacherStatus",
    "Class",
    "Section",
    "Subject",
    "Attendance",
    "AttendanceStatus",
    "Exam",
    "ExamType",
    "Grade",
    "Fee",
    "FeeStatus",
    "Timetable",
    "Announcement",
    "TargetAudience",
    "LeaveRequest",
    "RequesterType",
    "LeaveStatus",
    "AuditLog",
    "AuditAction",
]
