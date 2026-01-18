"""Authentication service for password hashing, JWT tokens, and user authentication."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from pydantic import BaseModel

from app.config import get_settings


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    user_id: int
    tenant_id: int
    role: str
    exp: datetime
    iat: datetime
    token_type: str  # "access" or "refresh"


class AuthService:
    """Service for authentication operations including password hashing and JWT tokens."""

    def __init__(self):
        self.settings = get_settings()

    # Password hashing methods

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password to hash.

        Returns:
            Hashed password string.
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify.
            hashed_password: Hashed password to check against.

        Returns:
            True if password matches, False otherwise.
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


    # JWT token methods

    def create_access_token(self, user_id: int, tenant_id: int, role: str) -> str:
        """Generate a JWT access token with user claims.

        Args:
            user_id: The user's ID.
            tenant_id: The tenant's ID.
            role: The user's role.

        Returns:
            Encoded JWT access token string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.settings.access_token_expire_minutes)

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "exp": expire,
            "iat": now,
            "token_type": "access",
        }

        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

    def create_refresh_token(self, user_id: int, tenant_id: int, role: str) -> str:
        """Generate a JWT refresh token.

        Args:
            user_id: The user's ID.
            tenant_id: The tenant's ID.
            role: The user's role.

        Returns:
            Encoded JWT refresh token string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.settings.refresh_token_expire_days)

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "exp": expire,
            "iat": now,
            "token_type": "refresh",
        }

        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )


    def verify_token(self, token: str) -> TokenPayload | None:
        """Validate and decode a JWT token.

        Args:
            token: The JWT token string to verify.

        Returns:
            TokenPayload if valid, None if invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )

            return TokenPayload(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                token_type=payload["token_type"],
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_access_token(self, token: str) -> TokenPayload | None:
        """Verify an access token specifically.

        Args:
            token: The JWT access token string to verify.

        Returns:
            TokenPayload if valid access token, None otherwise.
        """
        payload = self.verify_token(token)
        if payload and payload.token_type == "access":
            return payload
        return None

    def verify_refresh_token(self, token: str) -> TokenPayload | None:
        """Verify a refresh token specifically.

        Args:
            token: The JWT refresh token string to verify.

        Returns:
            TokenPayload if valid refresh token, None otherwise.
        """
        payload = self.verify_token(token)
        if payload and payload.token_type == "refresh":
            return payload
        return None
