"""Authentication schemas for request/response validation."""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class TenantRegisterRequest(BaseModel):
    """Schema for tenant registration request."""

    name: str = Field(..., min_length=2, max_length=255, description="School/organization name")
    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="Unique subdomain slug (lowercase alphanumeric and hyphens)",
    )
    admin_email: EmailStr = Field(..., description="Admin user email")
    admin_password: str = Field(..., min_length=8, description="Admin user password")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate and normalize slug."""
        v = v.lower().strip()
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        return v


class TenantRegisterResponse(BaseModel):
    """Schema for tenant registration response."""

    id: int
    name: str
    slug: str
    status: str
    subscription_plan: str
    admin_user_id: int
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    tenant_id: int
    role: str


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="Valid refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    id: int
    email: str
    role: str
    tenant_id: int
    is_active: bool
    profile_data: dict
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: dict = Field(..., description="Error details")

    @classmethod
    def create(cls, code: str, message: str, details: list[dict] | None = None) -> "ErrorResponse":
        """Create an error response."""
        error = {"code": code, "message": message}
        if details:
            error["details"] = details
        return cls(error=error)


class CSRFTokenResponse(BaseModel):
    """Schema for CSRF token response."""

    csrf_token: str = Field(..., description="CSRF token for form submissions")
