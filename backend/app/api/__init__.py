# API package - FastAPI routes

from app.api.announcements import router as announcements_router
from app.api.auth import router as auth_router
from app.api.classes import router as classes_router
from app.api.classes import sections_router
from app.api.deps import (
    ActiveUserDep,
    CurrentUser,
    CurrentUserDep,
    TokenPayloadDep,
    get_auth_service,
    get_current_active_user,
    get_current_user,
    get_token_payload,
)
from app.api.fees import router as fees_router
from app.api.leave_requests import router as leave_requests_router
from app.api.students import router as students_router
from app.api.teachers import router as teachers_router
from app.api.timetable import router as timetable_router

__all__ = [
    "ActiveUserDep",
    "CurrentUser",
    "CurrentUserDep",
    "TokenPayloadDep",
    "announcements_router",
    "auth_router",
    "classes_router",
    "fees_router",
    "leave_requests_router",
    "sections_router",
    "students_router",
    "teachers_router",
    "timetable_router",
    "get_auth_service",
    "get_current_active_user",
    "get_current_user",
    "get_token_payload",
]
