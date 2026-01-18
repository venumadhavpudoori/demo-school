"""CSRF (Cross-Site Request Forgery) protection middleware.

This middleware implements CSRF token validation to protect against
cross-site request forgery attacks on form submissions.
"""

import hashlib
import hmac
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce CSRF token validation on state-changing requests.
    
    Uses the double-submit cookie pattern with signed tokens for CSRF protection.
    """

    # HTTP methods that require CSRF validation
    UNSAFE_METHODS = frozenset(["POST", "PUT", "PATCH", "DELETE"])

    # Paths excluded from CSRF validation (e.g., API endpoints using JWT)
    EXCLUDED_PATHS = frozenset([
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    ])

    # API paths that use JWT authentication (exempt from CSRF)
    API_PATHS = frozenset([
        "/api/",
    ])

    # Token validity duration in seconds (1 hour)
    TOKEN_EXPIRY = 3600

    # Cookie name for CSRF token
    CSRF_COOKIE_NAME = "csrf_token"

    # Header name for CSRF token
    CSRF_HEADER_NAME = "X-CSRF-Token"

    # Form field name for CSRF token
    CSRF_FORM_FIELD = "csrf_token"

    def __init__(
        self,
        app,
        secret_key: str | None = None,
        token_expiry: int = TOKEN_EXPIRY,
        cookie_secure: bool = True,
        cookie_httponly: bool = False,
        cookie_samesite: str = "lax",
    ):
        """Initialize the CSRF middleware.

        Args:
            app: The ASGI application.
            secret_key: Secret key for signing tokens. Uses app secret if not provided.
            token_expiry: Token validity duration in seconds.
            cookie_secure: Whether to set Secure flag on cookie.
            cookie_httponly: Whether to set HttpOnly flag on cookie.
            cookie_samesite: SameSite attribute for cookie.
        """
        super().__init__(app)
        settings = get_settings()
        self.secret_key = secret_key or settings.secret_key
        self.token_expiry = token_expiry
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and validate CSRF token.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler.

        Raises:
            HTTPException: If CSRF validation fails.
        """
        # Skip CSRF for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Skip CSRF for API paths (they use JWT authentication)
        if self._is_api_path(request.url.path):
            return await call_next(request)

        # For safe methods, just ensure a token exists
        if request.method not in self.UNSAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie if not present
            if self.CSRF_COOKIE_NAME not in request.cookies:
                token = self._generate_token()
                response = self._set_csrf_cookie(response, token)
            return response

        # For unsafe methods, validate the token
        if not await self._validate_csrf_token(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token validation failed. Please refresh the page and try again.",
                    }
                },
            )

        response = await call_next(request)
        return response

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from CSRF validation.

        Args:
            path: The request path.

        Returns:
            True if the path is excluded, False otherwise.
        """
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _is_api_path(self, path: str) -> bool:
        """Check if the path is an API path (uses JWT auth).

        Args:
            path: The request path.

        Returns:
            True if the path is an API path, False otherwise.
        """
        return any(path.startswith(api_path) for api_path in self.API_PATHS)

    def _generate_token(self) -> str:
        """Generate a new CSRF token.

        Returns:
            A signed CSRF token string.
        """
        # Generate random token
        random_bytes = secrets.token_bytes(32)
        timestamp = int(time.time())

        # Create token payload
        payload = f"{random_bytes.hex()}:{timestamp}"

        # Sign the payload
        signature = self._sign_token(payload)

        return f"{payload}:{signature}"

    def _sign_token(self, payload: str) -> str:
        """Sign a token payload using HMAC-SHA256.

        Args:
            payload: The payload to sign.

        Returns:
            The signature as a hex string.
        """
        return hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _verify_token(self, token: str) -> bool:
        """Verify a CSRF token's signature and expiry.

        Args:
            token: The token to verify.

        Returns:
            True if the token is valid, False otherwise.
        """
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return False

            random_hex, timestamp_str, signature = parts

            # Verify signature
            payload = f"{random_hex}:{timestamp_str}"
            expected_signature = self._sign_token(payload)

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Verify expiry
            timestamp = int(timestamp_str)
            if time.time() - timestamp > self.token_expiry:
                return False

            return True

        except (ValueError, TypeError):
            return False

    async def _validate_csrf_token(self, request: Request) -> bool:
        """Validate the CSRF token from request.

        Checks both cookie and header/form field using double-submit pattern.

        Args:
            request: The incoming request.

        Returns:
            True if validation passes, False otherwise.
        """
        # Get token from cookie
        cookie_token = request.cookies.get(self.CSRF_COOKIE_NAME)
        if not cookie_token:
            return False

        # Get token from header or form
        header_token = request.headers.get(self.CSRF_HEADER_NAME)

        if header_token:
            submitted_token = header_token
        else:
            # Try to get from form data
            try:
                form = await request.form()
                submitted_token = form.get(self.CSRF_FORM_FIELD)
            except Exception:
                submitted_token = None

        if not submitted_token:
            return False

        # Verify both tokens match
        if not hmac.compare_digest(cookie_token, submitted_token):
            return False

        # Verify token is valid (signature and expiry)
        return self._verify_token(cookie_token)

    def _set_csrf_cookie(self, response: Response, token: str) -> Response:
        """Set the CSRF token cookie on the response.

        Args:
            response: The response to modify.
            token: The CSRF token to set.

        Returns:
            The modified response.
        """
        response.set_cookie(
            key=self.CSRF_COOKIE_NAME,
            value=token,
            max_age=self.token_expiry,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return response


def generate_csrf_token(secret_key: str | None = None) -> str:
    """Generate a new CSRF token.

    Args:
        secret_key: Secret key for signing. Uses app secret if not provided.

    Returns:
        A signed CSRF token string.
    """
    settings = get_settings()
    key = secret_key or settings.secret_key

    # Generate random token
    random_bytes = secrets.token_bytes(32)
    timestamp = int(time.time())

    # Create token payload
    payload = f"{random_bytes.hex()}:{timestamp}"

    # Sign the payload
    signature = hmac.new(
        key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload}:{signature}"


def verify_csrf_token(
    token: str,
    secret_key: str | None = None,
    max_age: int = 3600,
) -> bool:
    """Verify a CSRF token.

    Args:
        token: The token to verify.
        secret_key: Secret key for verification. Uses app secret if not provided.
        max_age: Maximum token age in seconds.

    Returns:
        True if the token is valid, False otherwise.
    """
    settings = get_settings()
    key = secret_key or settings.secret_key

    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False

        random_hex, timestamp_str, signature = parts

        # Verify signature
        payload = f"{random_hex}:{timestamp_str}"
        expected_signature = hmac.new(
            key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return False

        # Verify expiry
        timestamp = int(timestamp_str)
        if time.time() - timestamp > max_age:
            return False

        return True

    except (ValueError, TypeError):
        return False


def get_csrf_token_from_request(request: Request) -> str | None:
    """Get the CSRF token from request cookies.

    Args:
        request: The current request.

    Returns:
        The CSRF token or None if not present.
    """
    return request.cookies.get(CSRFMiddleware.CSRF_COOKIE_NAME)
