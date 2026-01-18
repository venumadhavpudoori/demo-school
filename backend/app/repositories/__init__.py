# Repositories package - Data access layer

from app.repositories.announcement import AnnouncementRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.base import PaginatedResult, TenantAwareRepository
from app.repositories.exam import ExamRepository
from app.repositories.fee import FeeRepository
from app.repositories.grade import GradeRepository
from app.repositories.leave_request import LeaveRequestRepository
from app.repositories.school import ClassRepository, SectionRepository, SubjectRepository
from app.repositories.student import StudentRepository
from app.repositories.teacher import TeacherRepository

__all__ = [
    "AnnouncementRepository",
    "AuditLogRepository",
    "LeaveRequestRepository",
    "PaginatedResult",
    "TenantAwareRepository",
    "ClassRepository",
    "ExamRepository",
    "FeeRepository",
    "GradeRepository",
    "SectionRepository",
    "SubjectRepository",
    "StudentRepository",
    "TeacherRepository",
]
