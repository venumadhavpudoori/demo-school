"""Tenant middleware for multi-tenancy support.

This middleware extracts the tenant from the subdomain or X-Tenant-ID header
and injects it into the request state for use by downstream handlers.
"""

import re
from collections.abc import Callable

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.models.tenant import Tenant, TenantStatus


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant from subdomain/header and inject into request state."""

    # Paths that don't require tenant context
    EXCLUDED_PATHS = frozenset(
        [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/me",
        ]
    )

    def __init__(self, app, db_session_factory: Callable[[], Session]):
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            db_session_factory: A callable that returns a database session.
        """
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and extract tenant context.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler.
        """
        # Skip tenant extraction for excluded paths
        if self._is_excluded_path(request.url.path):
            request.state.tenant = None
            request.state.tenant_id = None
            return await call_next(request)

        # Try to extract tenant slug or ID from subdomain or header
        tenant_identifier = self._extract_tenant_slug(request)

        if tenant_identifier is not None:
            tenant = await self._get_tenant(tenant_identifier)
            if tenant:
                request.state.tenant = tenant
                request.state.tenant_id = tenant.id
            else:
                request.state.tenant = None
                request.state.tenant_id = None
        else:
            request.state.tenant = None
            request.state.tenant_id = None

        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from tenant extraction.

        Args:
            path: The request path.

        Returns:
            True if the path is excluded, False otherwise.
        """
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _extract_tenant_slug(self, request: Request) -> str | int | None:
        """Extract tenant slug or ID from subdomain or X-Tenant-ID header.

        Priority:
        1. X-Tenant-ID header (for API clients) - can be slug or numeric ID
        2. Subdomain from Host header

        Args:
            request: The incoming request.

        Returns:
            The tenant slug/ID if found, None otherwise.
        """
        # Check X-Tenant-ID header first
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            tenant_header = tenant_header.strip()
            # Check if it's a numeric ID
            if tenant_header.isdigit():
                return int(tenant_header)
            return tenant_header.lower()

        # Extract from subdomain
        host = request.headers.get("host", "")
        return self._extract_subdomain(host)

    def _extract_subdomain(self, host: str) -> str | None:
        """Parse subdomain from host header.

        Args:
            host: The host header value (e.g., "school-a.platform.com:8000").

        Returns:
            The subdomain if found, None otherwise.
        """
        if not host:
            return None

        # Remove port if present
        host_without_port = host.split(":")[0]

        base_domain = self.settings.base_domain

        # Handle localhost specially
        if base_domain == "localhost" or host_without_port == "localhost":
            return None

        # Check if host ends with base domain
        if not host_without_port.endswith(base_domain):
            return None

        # Extract subdomain
        # e.g., "school-a.platform.com" with base "platform.com" -> "school-a"
        prefix = host_without_port[: -len(base_domain)].rstrip(".")

        if not prefix:
            return None

        # Validate subdomain format (alphanumeric and hyphens only)
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", prefix):
            return None

        return prefix

    async def _get_tenant(self, identifier: str | int) -> Tenant | None:
        """Lookup tenant by slug or ID.

        Args:
            identifier: The tenant slug (string) or ID (int).

        Returns:
            The tenant if found and active, None otherwise.
        """
        db = self.db_session_factory()
        try:
            if isinstance(identifier, int):
                # Lookup by ID
                stmt = select(Tenant).where(
                    Tenant.id == identifier,
                )
            else:
                # Lookup by slug
                stmt = select(Tenant).where(
                    Tenant.slug == identifier,
                )
            result = db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            # Check if tenant exists and has valid status
            if tenant and tenant.status in [TenantStatus.ACTIVE, TenantStatus.TRIAL]:
                return tenant
            return None
        finally:
            db.close()


def get_current_tenant(request: Request) -> Tenant | None:
    """Get the current tenant from request state.

    Args:
        request: The current request.

    Returns:
        The current tenant or None.
    """
    return getattr(request.state, "tenant", None)


def get_current_tenant_id(request: Request) -> int | None:
    """Get the current tenant ID from request state.

    Args:
        request: The current request.

    Returns:
        The current tenant ID or None.
    """
    return getattr(request.state, "tenant_id", None)
