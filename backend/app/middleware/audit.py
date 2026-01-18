"""Audit logging middleware for tracking sensitive operations.

This middleware captures request context (IP address, user agent) and provides
utilities for automatic audit logging on sensitive API operations.

Validates: Design - Property 17 (Audit Log Completeness)
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.audit_log import AuditAction
from app.services.audit_service import AuditService


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# Sensitive operations that should be audited
SENSITIVE_METHODS = frozenset(["POST", "PUT", "PATCH", "DELETE"])

# Entity type mapping from URL patterns
ENTITY_TYPE_PATTERNS = {
    "/api/students": "student",
    "/api/teachers": "teacher",
    "/api/classes": "class",
    "/api/sections": "section",
    "/api/attendance": "attendance",
    "/api/grades": "grade",
    "/api/exams": "exam",
    "/api/fees": "fee",
    "/api/announcements": "announcement",
    "/api/leave-requests": "leave_request",
    "/api/timetable": "timetable",
    "/api/auth": "auth",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to capture request context for audit logging.
    
    This middleware extracts client IP address and user agent from requests
    and stores them in request state for use by audit logging decorators.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and capture audit context.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler.
        """
        # Extract client IP address
        request.state.client_ip = self._get_client_ip(request)
        
        # Extract user agent
        request.state.user_agent = request.headers.get("user-agent")
        
        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str | None:
        """Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: The incoming request.

        Returns:
            The client IP address or None.
        """
        # Check for X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check for X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None


def get_entity_type_from_path(path: str) -> str | None:
    """Extract entity type from URL path.

    Args:
        path: The request URL path.

    Returns:
        The entity type or None if not found.
    """
    for pattern, entity_type in ENTITY_TYPE_PATTERNS.items():
        if path.startswith(pattern):
            return entity_type
    return None


def get_action_from_method(method: str, path: str) -> AuditAction | None:
    """Determine audit action from HTTP method and path.

    Args:
        method: The HTTP method.
        path: The request URL path.

    Returns:
        The audit action or None.
    """
    method = method.upper()
    
    if method == "POST":
        # Check for special actions
        if "/login" in path:
            return AuditAction.LOGIN
        if "/logout" in path:
            return AuditAction.LOGOUT
        if "/payment" in path:
            return AuditAction.UPDATE
        return AuditAction.CREATE
    elif method in ("PUT", "PATCH"):
        return AuditAction.UPDATE
    elif method == "DELETE":
        return AuditAction.DELETE
    
    return None


def audit_endpoint(
    entity_type: str | None = None,
    action: AuditAction | None = None,
    get_entity_id: Callable[..., int | None] | None = None,
    get_old_values: Callable[..., dict[str, Any] | None] | None = None,
    get_new_values: Callable[..., dict[str, Any] | None] | None = None,
) -> Callable[[F], F]:
    """Decorator for automatically logging audit events on API endpoints.

    This decorator wraps FastAPI endpoint functions to automatically create
    audit log entries after successful operations.

    Args:
        entity_type: The type of entity being affected. If None, inferred from path.
        action: The type of action being performed. If None, inferred from method.
        get_entity_id: Optional function to extract entity ID from response.
        get_old_values: Optional function to extract old values before operation.
        get_new_values: Optional function to extract new values from response.

    Returns:
        Decorated function.

    Example:
        @router.post("/api/students")
        @audit_endpoint(entity_type="student", action=AuditAction.CREATE)
        async def create_student(request: Request, data: StudentCreate):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in args or kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Execute the original function
            result = await func(*args, **kwargs)

            # Only log if we have a request and the operation succeeded
            if request is not None:
                try:
                    await _log_audit_event(
                        request=request,
                        result=result,
                        entity_type=entity_type,
                        action=action,
                        get_entity_id=get_entity_id,
                        get_new_values=get_new_values,
                    )
                except Exception as e:
                    # Don't fail the operation if audit logging fails
                    logger.warning(f"Failed to create audit log: {e}")

            return result

        return wrapper  # type: ignore
    return decorator


async def _log_audit_event(
    request: Request,
    result: Any,
    entity_type: str | None,
    action: AuditAction | None,
    get_entity_id: Callable[..., int | None] | None,
    get_new_values: Callable[..., dict[str, Any] | None] | None,
) -> None:
    """Create an audit log entry for the operation.

    Args:
        request: The FastAPI request object.
        result: The result from the endpoint function.
        entity_type: The type of entity affected.
        action: The audit action.
        get_entity_id: Function to extract entity ID.
        get_new_values: Function to extract new values.
    """
    # Get tenant_id from request state
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        return  # Can't log without tenant context

    # Get database session from request state
    db = getattr(request.state, "db", None)
    if db is None:
        return  # Can't log without database

    # Determine entity type
    final_entity_type = entity_type or get_entity_type_from_path(request.url.path)
    if final_entity_type is None:
        return  # Can't log without entity type

    # Determine action
    final_action = action or get_action_from_method(request.method, request.url.path)
    if final_action is None:
        return  # Can't log without action

    # Get user_id from request state (set by auth dependency)
    user_id = getattr(request.state, "user_id", None)
    
    # Try to get user_id from current_user if not in state
    if user_id is None:
        current_user = getattr(request.state, "current_user", None)
        if current_user:
            user_id = getattr(current_user, "user_id", None)

    # Get entity_id
    entity_id = None
    if get_entity_id:
        try:
            entity_id = get_entity_id(result)
        except Exception:
            pass
    elif hasattr(result, "id"):
        entity_id = result.id
    elif isinstance(result, dict) and "id" in result:
        entity_id = result["id"]

    # Get new values
    new_values = None
    if get_new_values:
        try:
            new_values = get_new_values(result)
        except Exception:
            pass

    # Get request context
    ip_address = getattr(request.state, "client_ip", None)
    user_agent = getattr(request.state, "user_agent", None)

    # Create audit service and log
    audit_service = AuditService(db, tenant_id)
    audit_service.log_action(
        user_id=user_id,
        action=final_action,
        entity_type=final_entity_type,
        entity_id=entity_id,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_sensitive_operation(
    db,
    tenant_id: int,
    user_id: int | None,
    action: AuditAction,
    entity_type: str,
    entity_id: int | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    additional_info: dict[str, Any] | None = None,
) -> None:
    """Utility function to manually log a sensitive operation.

    This function provides a simple way to log audit events from service
    methods or other code that doesn't use the decorator.

    Args:
        db: The database session.
        tenant_id: The tenant ID.
        user_id: The ID of the user performing the action.
        action: The type of action performed.
        entity_type: The type of entity affected.
        entity_id: The ID of the affected entity.
        old_values: The previous values before the change.
        new_values: The new values after the change.
        ip_address: The client IP address.
        user_agent: The client user agent.
        additional_info: Any additional context information.
    """
    try:
        audit_service = AuditService(db, tenant_id)
        audit_service.log_action(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


class AuditLoggerMixin:
    """Mixin class for services that need audit logging capabilities.
    
    This mixin provides convenient methods for logging audit events
    from within service classes.
    
    Example:
        class StudentService(AuditLoggerMixin):
            def __init__(self, db, tenant_id):
                self.db = db
                self.tenant_id = tenant_id
                
            def create_student(self, data, user_id=None):
                student = self._create_student(data)
                self.log_audit(
                    user_id=user_id,
                    action=AuditAction.CREATE,
                    entity_type="student",
                    entity_id=student.id,
                    new_values=data,
                )
                return student
    """

    db: Any  # Database session
    tenant_id: int  # Current tenant ID
    _audit_ip_address: str | None = None
    _audit_user_agent: str | None = None

    def set_audit_context(
        self,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Set the audit context for subsequent operations.

        Args:
            ip_address: The client IP address.
            user_agent: The client user agent.
        """
        self._audit_ip_address = ip_address
        self._audit_user_agent = user_agent

    def log_audit(
        self,
        user_id: int | None,
        action: AuditAction,
        entity_type: str,
        entity_id: int | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            user_id: The ID of the user performing the action.
            action: The type of action performed.
            entity_type: The type of entity affected.
            entity_id: The ID of the affected entity.
            old_values: The previous values before the change.
            new_values: The new values after the change.
            additional_info: Any additional context information.
        """
        log_sensitive_operation(
            db=self.db,
            tenant_id=self.tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=self._audit_ip_address,
            user_agent=self._audit_user_agent,
            additional_info=additional_info,
        )
