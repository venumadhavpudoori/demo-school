"""Property-based tests for JWT token round-trip verification.

**Feature: school-erp-multi-tenancy, Property 5: JWT Token Round-Trip**
**Validates: Design - Property 5**

Property 5: JWT Token Round-Trip
*For any* valid user with tenant and role, creating a JWT token and then verifying/decoding
it SHALL return the original user_id, tenant_id, and role claims.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.auth_service import AuthService


# Strategy for valid user IDs (positive integers)
user_id_strategy = st.integers(min_value=1, max_value=2**31 - 1)

# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=2**31 - 1)

# Strategy for valid roles (matching UserRole enum values)
role_strategy = st.sampled_from(["super_admin", "admin", "teacher", "student", "parent"])


class TestJWTTokenRoundTrip:
    """**Feature: school-erp-multi-tenancy, Property 5: JWT Token Round-Trip**"""

    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100)
    def test_access_token_roundtrip_preserves_claims(
        self, user_id: int, tenant_id: int, role: str
    ):
        """For any valid user, creating and verifying access token SHALL preserve claims.

        **Validates: Requirements 3.1, 3.3**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Create access token
        token = auth_service.create_access_token(user_id, tenant_id, role)

        # Act: Verify and decode the token
        payload = auth_service.verify_access_token(token)

        # Assert: Payload is not None (token is valid)
        assert payload is not None, "Access token verification must succeed"

        # Assert: Claims are preserved
        assert payload.user_id == user_id, (
            f"user_id must be preserved. Expected: {user_id}, Got: {payload.user_id}"
        )
        assert payload.tenant_id == tenant_id, (
            f"tenant_id must be preserved. Expected: {tenant_id}, Got: {payload.tenant_id}"
        )
        assert payload.role == role, (
            f"role must be preserved. Expected: {role}, Got: {payload.role}"
        )
        assert payload.token_type == "access", (
            f"token_type must be 'access'. Got: {payload.token_type}"
        )

    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100)
    def test_refresh_token_roundtrip_preserves_claims(
        self, user_id: int, tenant_id: int, role: str
    ):
        """For any valid user, creating and verifying refresh token SHALL preserve claims.

        **Validates: Requirements 3.1, 3.3**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Create refresh token
        token = auth_service.create_refresh_token(user_id, tenant_id, role)

        # Act: Verify and decode the token
        payload = auth_service.verify_refresh_token(token)

        # Assert: Payload is not None (token is valid)
        assert payload is not None, "Refresh token verification must succeed"

        # Assert: Claims are preserved
        assert payload.user_id == user_id, (
            f"user_id must be preserved. Expected: {user_id}, Got: {payload.user_id}"
        )
        assert payload.tenant_id == tenant_id, (
            f"tenant_id must be preserved. Expected: {tenant_id}, Got: {payload.tenant_id}"
        )
        assert payload.role == role, (
            f"role must be preserved. Expected: {role}, Got: {payload.role}"
        )
        assert payload.token_type == "refresh", (
            f"token_type must be 'refresh'. Got: {payload.token_type}"
        )

    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100)
    def test_access_token_not_valid_as_refresh(
        self, user_id: int, tenant_id: int, role: str
    ):
        """Access token SHALL NOT be accepted as refresh token.

        **Validates: Requirements 3.1, 3.3**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Create access token
        token = auth_service.create_access_token(user_id, tenant_id, role)

        # Act: Try to verify as refresh token
        payload = auth_service.verify_refresh_token(token)

        # Assert: Should be rejected
        assert payload is None, "Access token must not be accepted as refresh token"

    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100)
    def test_refresh_token_not_valid_as_access(
        self, user_id: int, tenant_id: int, role: str
    ):
        """Refresh token SHALL NOT be accepted as access token.

        **Validates: Requirements 3.1, 3.3**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Create refresh token
        token = auth_service.create_refresh_token(user_id, tenant_id, role)

        # Act: Try to verify as access token
        payload = auth_service.verify_access_token(token)

        # Assert: Should be rejected
        assert payload is None, "Refresh token must not be accepted as access token"

    @given(
        user_id=user_id_strategy,
        tenant_id=tenant_id_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100)
    def test_token_has_valid_timestamps(
        self, user_id: int, tenant_id: int, role: str
    ):
        """For any token, iat SHALL be before exp.

        **Validates: Requirements 3.1, 3.3**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Create access token
        token = auth_service.create_access_token(user_id, tenant_id, role)
        payload = auth_service.verify_access_token(token)

        # Assert: Timestamps are valid
        assert payload is not None, "Token verification must succeed"
        assert payload.iat < payload.exp, (
            f"iat must be before exp. iat: {payload.iat}, exp: {payload.exp}"
        )
