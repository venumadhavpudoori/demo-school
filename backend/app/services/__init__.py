# Services package - Business logic

from app.services.announcement_service import (
    AnnouncementNotFoundError,
    AnnouncementService,
    AnnouncementServiceError,
    InvalidAnnouncementDataError,
)
from app.services.audit_service import AuditContext, AuditService, audit_log
from app.services.auth_service import AuthService, TokenPayload
from app.services.cache_service import CacheService
from app.services.exam_service import (
    ExamDateConflictError,
    ExamNotFoundError,
    ExamService,
    ExamServiceError,
    InvalidExamDataError,
)
from app.services.fee_service import (
    FeeNotFoundError,
    FeeService,
    FeeServiceError,
    InvalidFeeDataError,
    InvalidPaymentError,
)
from app.services.grade_service import (
    DuplicateGradeError,
    GradeNotFoundError,
    GradeService,
    GradeServiceError,
    InvalidGradeDataError,
)
from app.services.leave_request_service import (
    InvalidLeaveRequestDataError,
    InvalidStatusTransitionError,
    LeaveRequestNotFoundError,
    LeaveRequestService,
    LeaveRequestServiceError,
    OverlappingLeaveRequestError,
)
from app.services.school_service import (
    ClassNotFoundError,
    ClassService,
    DuplicateClassNameError,
    DuplicateSectionNameError,
    DuplicateSubjectCodeError,
    SchoolServiceError,
    SectionNotFoundError,
    SectionService,
    SubjectNotFoundError,
    SubjectService,
)
from app.services.student_service import (
    DuplicateAdmissionNumberError,
    DuplicateEmailError,
    StudentNotFoundError,
    StudentService,
    StudentServiceError,
)
from app.services.teacher_service import (
    DuplicateEmployeeIdError,
    TeacherNotFoundError,
    TeacherService,
    TeacherServiceError,
)
from app.services.timetable_service import (
    InvalidTimetableDataError,
    TimetableConflictError,
    TimetableNotFoundError,
    TimetableService,
    TimetableServiceError,
)

__all__ = [
    # Announcement services
    "AnnouncementService",
    "AnnouncementServiceError",
    "AnnouncementNotFoundError",
    "InvalidAnnouncementDataError",
    # Audit services
    "AuditService",
    "AuditContext",
    "audit_log",
    # Auth services
    "AuthService",
    "CacheService",
    "TokenPayload",
    # Exam services
    "ExamService",
    "ExamServiceError",
    "ExamNotFoundError",
    "InvalidExamDataError",
    "ExamDateConflictError",
    # Fee services
    "FeeService",
    "FeeServiceError",
    "FeeNotFoundError",
    "InvalidFeeDataError",
    "InvalidPaymentError",
    # Grade services
    "GradeService",
    "GradeServiceError",
    "GradeNotFoundError",
    "InvalidGradeDataError",
    "DuplicateGradeError",
    # Leave request services
    "LeaveRequestService",
    "LeaveRequestServiceError",
    "LeaveRequestNotFoundError",
    "InvalidLeaveRequestDataError",
    "OverlappingLeaveRequestError",
    "InvalidStatusTransitionError",
    # School services
    "ClassService",
    "SectionService",
    "SubjectService",
    "SchoolServiceError",
    "ClassNotFoundError",
    "DuplicateClassNameError",
    "SectionNotFoundError",
    "DuplicateSectionNameError",
    "SubjectNotFoundError",
    "DuplicateSubjectCodeError",
    # Student services
    "StudentService",
    "StudentServiceError",
    "StudentNotFoundError",
    "DuplicateAdmissionNumberError",
    "DuplicateEmailError",
    # Teacher services
    "TeacherService",
    "TeacherServiceError",
    "TeacherNotFoundError",
    "DuplicateEmployeeIdError",
    # Timetable services
    "TimetableService",
    "TimetableServiceError",
    "TimetableNotFoundError",
    "InvalidTimetableDataError",
    "TimetableConflictError",
]
