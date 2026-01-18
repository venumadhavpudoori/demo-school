"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.user import User, UserRole
from app.services.auth_service import AuthService, TokenPayload


# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    """Get AuthService instance."""
    return AuthService()


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPayload:
    """Extract and validate JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from request.
        auth_service: AuthService instance.

    Returns:
        Validated TokenPayload.

    Raises:
        HTTPException: If token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload



class CurrentUser:
    """Represents the current authenticated user context.

    This is a lightweight object that holds the user's identity information
    extracted from the JWT token without requiring a database lookup.
    """

    def __init__(self, payload: TokenPayload):
        self.user_id = payload.user_id
        self.tenant_id = payload.tenant_id
        self.role = UserRole(payload.role)
        self.token_type = payload.token_type

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        """Check if user has super admin role."""
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_teacher(self) -> bool:
        """Check if user has teacher role."""
        return self.role == UserRole.TEACHER

    @property
    def is_student(self) -> bool:
        """Check if user has student role."""
        return self.role == UserRole.STUDENT

    @property
    def is_parent(self) -> bool:
        """Check if user has parent role."""
        return self.role == UserRole.PARENT


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> CurrentUser:
    """Get the current authenticated user from the JWT token.

    Args:
        payload: Validated token payload.

    Returns:
        CurrentUser object with user identity information.
    """
    return CurrentUser(payload)


async def get_current_active_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Get the current active user.

    This dependency can be extended to check if the user is active
    by performing a database lookup if needed.

    Args:
        current_user: Current user from token.

    Returns:
        CurrentUser if active.
    """
    # In a full implementation, you might want to check the database
    # to ensure the user is still active
    return current_user


async def get_super_admin_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Get the current user and verify they have super admin role.

    This dependency ensures that only super_admin users can access
    the protected route. It's used for platform-wide administrative
    operations that should not be accessible to regular tenant admins.

    Args:
        current_user: Current user from token.

    Returns:
        CurrentUser if they are a super admin.

    Raises:
        HTTPException: 403 Forbidden if user is not a super admin.
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
ActiveUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
TokenPayloadDep = Annotated[TokenPayload, Depends(get_token_payload)]
SuperAdminDep = Annotated[CurrentUser, Depends(get_super_admin_user)]
