"""Input sanitization middleware for XSS prevention.

This middleware sanitizes incoming request data to prevent
Cross-Site Scripting (XSS) attacks.
"""

import json
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.sanitization import sanitize_value


class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize incoming request data for XSS prevention.
    
    This middleware intercepts JSON request bodies and sanitizes
    string values to prevent XSS attacks.
    """

    # Content types that should be sanitized
    SANITIZABLE_CONTENT_TYPES = frozenset([
        "application/json",
        "application/x-www-form-urlencoded",
    ])

    # Paths excluded from sanitization (e.g., file uploads)
    EXCLUDED_PATHS = frozenset([
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    ])

    # Fields that should not be escaped (e.g., HTML content fields)
    # These will still have dangerous scripts removed but HTML entities preserved
    HTML_ALLOWED_FIELDS = frozenset([
        "content",  # Announcement content
        "description",  # Rich text descriptions
        "body",  # Email body
    ])

    def __init__(self, app, escape_html: bool = True):
        """Initialize the sanitization middleware.

        Args:
            app: The ASGI application.
            escape_html: Whether to escape HTML entities by default.
        """
        super().__init__(app)
        self.escape_html = escape_html

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and sanitize input data.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler.
        """
        # Skip sanitization for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Skip if not a sanitizable content type
        content_type = request.headers.get("content-type", "")
        if not self._should_sanitize(content_type):
            return await call_next(request)

        # Only sanitize POST, PUT, PATCH requests with body
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Store sanitized body in request state for later use
        try:
            body = await request.body()
            if body:
                sanitized_body = await self._sanitize_body(body, content_type)
                # Store sanitized data in request state
                request.state.sanitized_body = sanitized_body
        except Exception:
            # If sanitization fails, continue with original request
            pass

        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from sanitization.

        Args:
            path: The request path.

        Returns:
            True if the path is excluded, False otherwise.
        """
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _should_sanitize(self, content_type: str) -> bool:
        """Check if the content type should be sanitized.

        Args:
            content_type: The Content-Type header value.

        Returns:
            True if the content should be sanitized, False otherwise.
        """
        content_type_lower = content_type.lower().split(";")[0].strip()
        return content_type_lower in self.SANITIZABLE_CONTENT_TYPES

    async def _sanitize_body(self, body: bytes, content_type: str) -> dict[str, Any] | None:
        """Sanitize the request body.

        Args:
            body: The raw request body.
            content_type: The Content-Type header value.

        Returns:
            The sanitized body as a dictionary, or None if parsing fails.
        """
        content_type_lower = content_type.lower().split(";")[0].strip()

        if content_type_lower == "application/json":
            return self._sanitize_json_body(body)

        return None

    def _sanitize_json_body(self, body: bytes) -> dict[str, Any] | None:
        """Sanitize a JSON request body.

        Args:
            body: The raw JSON body.

        Returns:
            The sanitized body as a dictionary, or None if parsing fails.
        """
        try:
            data = json.loads(body.decode("utf-8"))
            if isinstance(data, dict):
                return self._sanitize_dict_with_field_awareness(data)
            elif isinstance(data, list):
                return [
                    self._sanitize_dict_with_field_awareness(item)
                    if isinstance(item, dict)
                    else sanitize_value(item, self.escape_html)
                    for item in data
                ]
            else:
                return sanitize_value(data, self.escape_html)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _sanitize_dict_with_field_awareness(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Sanitize a dictionary with awareness of HTML-allowed fields.

        Args:
            data: The dictionary to sanitize.

        Returns:
            The sanitized dictionary.
        """
        sanitized = {}
        for key, value in data.items():
            # Check if this field allows HTML
            escape_html = key not in self.HTML_ALLOWED_FIELDS

            if isinstance(value, dict):
                sanitized[key] = self._sanitize_dict_with_field_awareness(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict_with_field_awareness(item)
                    if isinstance(item, dict)
                    else sanitize_value(item, escape_html)
                    for item in value
                ]
            else:
                sanitized[key] = sanitize_value(value, escape_html)

        return sanitized


def get_sanitized_body(request: Request) -> dict[str, Any] | None:
    """Get the sanitized body from request state.

    Args:
        request: The current request.

    Returns:
        The sanitized body or None if not available.
    """
    return getattr(request.state, "sanitized_body", None)
