"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.analytics import router as analytics_router
from app.api.announcements import router as announcements_router
from app.api.attendance import router as attendance_router
from app.api.auth import router as auth_router
from app.api.classes import router as classes_router
from app.api.classes import sections_router
from app.api.exams import router as exams_router
from app.api.fees import router as fees_router
from app.api.grades import router as grades_router
from app.api.leave_requests import router as leave_requests_router
from app.api.reports import router as reports_router
from app.api.students import router as students_router
from app.api.teachers import router as teachers_router
from app.api.tenants import router as tenants_router
from app.api.timetable import router as timetable_router
from app.config import get_settings
from app.middleware.audit import AuditMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.sanitization import SanitizationMiddleware
from app.middleware.tenant import TenantMiddleware
from app.models.base import Base


settings = get_settings()

# Database setup
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client: Redis | None = None


def get_redis() -> Redis | None:
    """Get the Redis client instance."""
    return redis_client


def get_db_session() -> Session:
    """Create a new database session."""
    return SessionLocal()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global redis_client
    
    # Import all models to ensure they're registered with Base
    from app.models import (
        Tenant, User, Student, Teacher, Class, Section, Subject,
        Attendance, Exam, Grade, Fee, Timetable, Announcement,
        LeaveRequest, AuditLog
    )
    
    # Create all tables (for SQLite development)
    Base.metadata.create_all(bind=engine)
    
    # Startup
    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        # Test connection
        redis_client.ping()
    except Exception:
        # Redis is optional - continue without it
        redis_client = None
    yield
    # Shutdown
    if redis_client:
        redis_client.close()
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Multi-tenancy School ERP System API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_getter=get_redis)

# CSRF protection middleware
app.add_middleware(
    CSRFMiddleware,
    cookie_secure=not settings.debug,  # Secure cookies in production
)

# Input sanitization middleware (XSS prevention)
app.add_middleware(SanitizationMiddleware)

# Tenant middleware
app.add_middleware(TenantMiddleware, db_session_factory=get_db_session)

# Audit middleware (captures request context for audit logging)
app.add_middleware(AuditMiddleware)


# Database session middleware
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """Inject database session and Redis client into request state."""
    request.state.db = SessionLocal()
    request.state.redis = redis_client
    try:
        response = await call_next(request)
        return response
    finally:
        request.state.db.close()


# Include routers
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(announcements_router)
app.include_router(students_router)
app.include_router(teachers_router)
app.include_router(classes_router)
app.include_router(sections_router)
app.include_router(attendance_router)
app.include_router(exams_router)
app.include_router(fees_router)
app.include_router(grades_router)
app.include_router(leave_requests_router)
app.include_router(reports_router)
app.include_router(tenants_router)
app.include_router(timetable_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
