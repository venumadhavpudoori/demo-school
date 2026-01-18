"""Rate limiting middleware for API endpoints.

This middleware implements a sliding window rate limiter using Redis
to protect API endpoints from abuse and ensure fair usage.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API endpoints.
    
    Uses a sliding window algorithm with Redis for distributed rate limiting.
    Rate limits can be configured per-endpoint or use global defaults.
    """

    # Default rate limit settings
    DEFAULT_REQUESTS_PER_MINUTE = 60
    DEFAULT_REQUESTS_PER_HOUR = 1000
    
    # Endpoint-specific rate limits (path prefix -> (requests, window_seconds))
    ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
        "/api/auth/login": (10, 60),  # 10 requests per minute for login
        "/api/auth/register": (5, 60),  # 5 requests per minute for registration
        "/api/auth/refresh": (20, 60),  # 20 requests per minute for token refresh
    }
    
    # Paths excluded from rate limiting
    EXCLUDED_PATHS = frozenset([
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    ])

    def __init__(
        self,
        app,
        redis_getter: Callable[[], Any] | None = None,
        default_limit: int = DEFAULT_REQUESTS_PER_MINUTE,
        default_window: int = 60,
    ):
        """Initialize the rate limit middleware.

        Args:
            app: The ASGI application.
            redis_getter: A callable that returns the Redis client.
            default_limit: Default number of requests allowed per window.
            default_window: Default time window in seconds.
        """
        super().__init__(app)
        self.redis_getter = redis_getter
        self.default_limit = default_limit
        self.default_window = default_window

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and enforce rate limits.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler.

        Raises:
            HTTPException: If rate limit is exceeded.
        """
        # Skip rate limiting for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Get Redis client
        redis = self._get_redis(request)
        
        # If Redis is not available, skip rate limiting
        if redis is None:
            return await call_next(request)

        # Get client identifier (IP address or user ID if authenticated)
        client_id = self._get_client_identifier(request)
        
        # Get rate limit for this endpoint
        limit, window = self._get_rate_limit(request.url.path)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(
            redis, client_id, request.url.path, limit, window
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": reset_time,
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from rate limiting.

        Args:
            path: The request path.

        Returns:
            True if the path is excluded, False otherwise.
        """
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _get_redis(self, request: Request) -> Any | None:
        """Get Redis client from request state or getter.

        Args:
            request: The incoming request.

        Returns:
            Redis client or None if not available.
        """
        # Try to get from request state first
        redis = getattr(request.state, "redis", None)
        if redis is not None:
            return redis
        
        # Fall back to getter
        if self.redis_getter:
            return self.redis_getter()
        
        return None

    def _get_client_identifier(self, request: Request) -> str:
        """Get a unique identifier for the client.

        Uses user ID if authenticated, otherwise falls back to IP address.

        Args:
            request: The incoming request.

        Returns:
            A unique client identifier string.
        """
        # Try to get user ID from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            tenant_id = getattr(request.state, "tenant_id", "global")
            return f"user:{tenant_id}:{user.id}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: The incoming request.

        Returns:
            The client IP address.
        """
        # Check X-Forwarded-For header (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """Get the rate limit for a specific path.

        Args:
            path: The request path.

        Returns:
            Tuple of (max_requests, window_seconds).
        """
        # Check for endpoint-specific limits
        for prefix, limits in self.ENDPOINT_LIMITS.items():
            if path.startswith(prefix):
                return limits

        # Return default limits
        return (self.default_limit, self.default_window)

    async def _check_rate_limit(
        self,
        redis: Any,
        client_id: str,
        path: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """Check if the request is within rate limits using sliding window.

        Args:
            redis: Redis client.
            client_id: Unique client identifier.
            path: Request path (for key namespacing).
            limit: Maximum requests allowed.
            window: Time window in seconds.

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds).
        """
        # Normalize path for key (remove trailing slashes, use first segment)
        path_key = path.rstrip("/").split("/")[1:3]  # e.g., ["api", "auth"]
        path_key = "_".join(path_key) if path_key else "root"
        
        # Create Redis key
        key = f"ratelimit:{client_id}:{path_key}"
        
        current_time = int(time.time())
        window_start = current_time - window

        try:
            # Use Redis pipeline for atomic operations
            pipe = redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the key
            pipe.expire(key, window)
            
            # Execute pipeline
            results = pipe.execute()
            
            # Get count (before adding current request)
            current_count = results[1]
            
            # Calculate remaining requests
            remaining = max(0, limit - current_count - 1)
            
            # Calculate reset time
            reset_time = window
            
            # Check if limit exceeded
            is_allowed = current_count < limit
            
            return (is_allowed, remaining, reset_time)

        except Exception:
            # If Redis fails, allow the request (fail open)
            return (True, limit, window)


def get_rate_limit_key(client_id: str, endpoint: str) -> str:
    """Generate a rate limit key for Redis.

    Args:
        client_id: The client identifier.
        endpoint: The API endpoint.

    Returns:
        A formatted Redis key.
    """
    return f"ratelimit:{client_id}:{endpoint}"
