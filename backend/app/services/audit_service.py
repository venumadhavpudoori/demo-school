"""Audit logging service for tracking sensitive operations.

This module provides the AuditService class and decorators for automatically
logging sensitive operations on core entities.

Validates: Design - Property 17 (Audit Log Completeness)
"""

import functools
import json
from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog
from app.repositories.audit_log import AuditLogRepository


F = TypeVar("F", bound=Callable[..., Any])


class AuditService:
    """Service class for audit logging operations.

    Provides methods for creating audit log entries and querying audit history.
    All audit logs are scoped to a tenant for multi-tenancy support.
    """

    def __init__(self, db: Session, tenant_id: int):
        """Initialize the audit service.

        Args:
            db: The database session.
            tenant_id: The current tenant's ID.
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = AuditLogRepository(db, tenant_id)

    def log_create(
        self,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a create operation.

        Args:
            user_id: The ID of the user who performed the action.
            entity_type: The type of entity created (e.g., 'student', 'teacher').
            entity_id: The ID of the created entity.
            new_values: The values of the created entity.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=self._serialize_values(new_values),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_update(
        self,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log an update operation.

        Args:
            user_id: The ID of the user who performed the action.
            entity_type: The type of entity updated.
            entity_id: The ID of the updated entity.
            old_values: The previous values before the update.
            new_values: The new values after the update.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=self._serialize_values(old_values),
            new_values=self._serialize_values(new_values),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_delete(
        self,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        old_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a delete operation.

        Args:
            user_id: The ID of the user who performed the action.
            entity_type: The type of entity deleted.
            entity_id: The ID of the deleted entity.
            old_values: The values of the entity before deletion.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=self._serialize_values(old_values),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_soft_delete(
        self,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        old_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a soft delete operation.

        Args:
            user_id: The ID of the user who performed the action.
            entity_type: The type of entity soft-deleted.
            entity_id: The ID of the soft-deleted entity.
            old_values: The values of the entity before soft deletion.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.SOFT_DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=self._serialize_values(old_values),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_login(
        self,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a login event.

        Args:
            user_id: The ID of the user who logged in.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_logout(
        self,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a logout event.

        Args:
            user_id: The ID of the user who logged out.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_password_change(
        self,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a password change event.

        Args:
            user_id: The ID of the user whose password was changed.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            entity_type="user",
            entity_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_permission_change(
        self,
        user_id: int | None,
        target_user_id: int,
        old_role: str | None = None,
        new_role: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a permission/role change event.

        Args:
            user_id: The ID of the user who made the change.
            target_user_id: The ID of the user whose permissions changed.
            old_role: The previous role.
            new_role: The new role.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=AuditAction.PERMISSION_CHANGE,
            entity_type="user",
            entity_id=target_user_id,
            old_values={"role": old_role} if old_role else None,
            new_values={"role": new_role} if new_role else None,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def log_action(
        self,
        user_id: int | None,
        action: AuditAction,
        entity_type: str,
        entity_id: int | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        additional_info: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a generic action.

        Args:
            user_id: The ID of the user who performed the action.
            action: The type of action performed.
            entity_type: The type of entity affected.
            entity_id: The ID of the affected entity.
            old_values: The previous values before the change.
            new_values: The new values after the change.
            ip_address: The IP address of the client.
            user_agent: The user agent string of the client.
            additional_info: Any additional context information.

        Returns:
            The created AuditLog entry.
        """
        return self.repository.create_log(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=self._serialize_values(old_values),
            new_values=self._serialize_values(new_values),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_info=additional_info,
        )

    def _serialize_values(self, values: dict[str, Any] | None) -> dict[str, Any] | None:
        """Serialize values for JSON storage.

        Converts non-JSON-serializable types to strings.

        Args:
            values: Dictionary of values to serialize.

        Returns:
            Serialized dictionary or None.
        """
        if values is None:
            return None

        serialized = {}
        for key, value in values.items():
            try:
                # Test if value is JSON serializable
                json.dumps(value)
                serialized[key] = value
            except (TypeError, ValueError):
                # Convert to string if not serializable
                serialized[key] = str(value)

        return serialized


def audit_log(
    action: AuditAction,
    entity_type: str,
    entity_id_param: str | None = None,
    get_old_values: Callable[..., dict[str, Any] | None] | None = None,
    get_new_values: Callable[..., dict[str, Any] | None] | None = None,
) -> Callable[[F], F]:
    """Decorator for automatically logging audit events on service methods.

    This decorator wraps service methods to automatically create audit log
    entries before or after the method execution.

    Args:
        action: The type of action being performed.
        entity_type: The type of entity being affected.
        entity_id_param: The name of the parameter containing the entity ID.
        get_old_values: Optional function to extract old values before the operation.
        get_new_values: Optional function to extract new values after the operation.

    Returns:
        Decorated function.

    Example:
        @audit_log(AuditAction.CREATE, "student", entity_id_param="student_id")
        def create_student(self, ...):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get audit service from self (assumes service has db and tenant_id)
            audit_service = AuditService(self.db, self.tenant_id)

            # Get user_id from kwargs or self if available
            user_id = kwargs.get("user_id") or getattr(self, "current_user_id", None)

            # Get entity_id from kwargs if specified
            entity_id = None
            if entity_id_param:
                entity_id = kwargs.get(entity_id_param)

            # Get old values before operation if needed
            old_values = None
            if get_old_values and entity_id:
                try:
                    old_values = get_old_values(self, entity_id)
                except Exception:
                    pass  # Ignore errors in getting old values

            # Execute the original function
            result = func(self, *args, **kwargs)

            # Get entity_id from result if not in kwargs (for create operations)
            if entity_id is None and hasattr(result, "id"):
                entity_id = result.id

            # Get new values after operation if needed
            new_values = None
            if get_new_values:
                try:
                    new_values = get_new_values(self, result)
                except Exception:
                    pass  # Ignore errors in getting new values

            # Get IP and user agent from request context if available
            ip_address = getattr(self, "ip_address", None)
            user_agent = getattr(self, "user_agent", None)

            # Create audit log entry
            try:
                audit_service.log_action(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            except Exception:
                # Don't fail the operation if audit logging fails
                pass

            return result

        return wrapper  # type: ignore
    return decorator


class AuditContext:
    """Context manager for audit logging with request context.

    This class provides a way to capture request context (IP address, user agent)
    and pass it to audit logging operations.

    Example:
        with AuditContext(request) as ctx:
            audit_service.log_create(
                user_id=user.id,
                entity_type="student",
                entity_id=student.id,
                ip_address=ctx.ip_address,
                user_agent=ctx.user_agent,
            )
    """

    def __init__(self, request: Any = None):
        """Initialize the audit context.

        Args:
            request: The FastAPI request object (optional).
        """
        self.ip_address: str | None = None
        self.user_agent: str | None = None

        if request:
            # Extract IP address from request
            self.ip_address = self._get_client_ip(request)
            # Extract user agent from request headers
            self.user_agent = request.headers.get("user-agent")

    def _get_client_ip(self, request: Any) -> str | None:
        """Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: The FastAPI request object.

        Returns:
            The client IP address or None.
        """
        # Check for X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None

    def __enter__(self) -> "AuditContext":
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        pass
