"""Property-based tests for password hash verification round-trip.

**Feature: school-erp-multi-tenancy, Property 4: Password Hash Verification Round-Trip**
**Validates: Design - Property 4**

Property 4: Password Hash Verification Round-Trip
*For any* valid password string, hashing the password and then verifying the original
password against the hash SHALL return true.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.auth_service import AuthService


# Strategy for valid passwords (non-empty strings with printable ASCII characters)
# bcrypt has a 72-byte limit, so we constrain to ASCII characters (1 byte each)
# and limit length to 72 characters to stay within bcrypt's limit
password_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),  # Letters, Numbers, Punctuation, Symbols
        whitelist_characters=" ",  # Allow spaces
        max_codepoint=127,  # ASCII only to ensure 1 byte per character
    ),
    min_size=1,
    max_size=72,  # bcrypt's maximum password length in bytes
).filter(lambda s: len(s.strip()) > 0 and len(s.encode("utf-8")) <= 72)

# bcrypt is intentionally slow for security, so we need a longer deadline
# Each hash operation takes ~100-200ms by design
BCRYPT_DEADLINE_MS = 5000  # 5 seconds to account for bcrypt's intentional slowness

# Reduced examples due to bcrypt's intentional computational cost
# 10 examples provides coverage while keeping test runtime reasonable (~30s per test)
BCRYPT_MAX_EXAMPLES = 10


class TestPasswordHashRoundTrip:
    """**Feature: school-erp-multi-tenancy, Property 4: Password Hash Verification Round-Trip**"""

    @given(password=password_strategy)
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_hash_then_verify_returns_true(self, password: str):
        """For any valid password, hash then verify SHALL return true.

        **Validates: Requirements 3.4**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Hash the password
        hashed = auth_service.hash_password(password)

        # Act: Verify the original password against the hash
        result = auth_service.verify_password(password, hashed)

        # Assert: Verification must succeed
        assert result is True, (
            f"Password verification must succeed for the original password. "
            f"Password length: {len(password)}, Hash: {hashed[:20]}..."
        )

    @given(password=password_strategy)
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_hash_produces_different_output_than_input(self, password: str):
        """For any password, the hash SHALL be different from the original password.

        **Validates: Requirements 3.4**
        """
        # Arrange
        auth_service = AuthService()

        # Act
        hashed = auth_service.hash_password(password)

        # Assert: Hash is different from original
        assert hashed != password, (
            f"Hashed password must be different from original. "
            f"Password: {password}, Hash: {hashed}"
        )

    @given(password=password_strategy)
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_hash_is_bcrypt_format(self, password: str):
        """For any password, the hash SHALL be in bcrypt format.

        **Validates: Requirements 3.4**
        """
        # Arrange
        auth_service = AuthService()

        # Act
        hashed = auth_service.hash_password(password)

        # Assert: Hash starts with bcrypt prefix ($2b$ or $2a$ or $2y$)
        assert hashed.startswith(("$2b$", "$2a$", "$2y$")), (
            f"Hash must be in bcrypt format (starting with $2b$, $2a$, or $2y$). "
            f"Got: {hashed[:10]}..."
        )

    @given(
        password=password_strategy,
        wrong_password=password_strategy,
    )
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_verify_with_wrong_password_returns_false(
        self, password: str, wrong_password: str
    ):
        """For any two different passwords, verifying wrong password SHALL return false.

        **Validates: Requirements 3.4**
        """
        # Skip if passwords happen to be the same
        if password == wrong_password:
            return

        # Arrange
        auth_service = AuthService()

        # Act: Hash the original password
        hashed = auth_service.hash_password(password)

        # Act: Try to verify with wrong password
        result = auth_service.verify_password(wrong_password, hashed)

        # Assert: Verification must fail
        assert result is False, (
            f"Password verification must fail for wrong password. "
            f"Original length: {len(password)}, Wrong length: {len(wrong_password)}"
        )

    @given(password=password_strategy)
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_hashing_same_password_twice_produces_different_hashes(self, password: str):
        """For any password, hashing twice SHALL produce different hashes (due to salt).

        **Validates: Requirements 3.4**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Hash the same password twice
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Assert: Hashes are different (due to random salt)
        assert hash1 != hash2, (
            f"Hashing same password twice must produce different hashes. "
            f"Hash1: {hash1}, Hash2: {hash2}"
        )

    @given(password=password_strategy)
    @settings(max_examples=BCRYPT_MAX_EXAMPLES, deadline=BCRYPT_DEADLINE_MS)
    def test_both_hashes_verify_correctly(self, password: str):
        """For any password hashed multiple times, all hashes SHALL verify correctly.

        **Validates: Requirements 3.4**
        """
        # Arrange
        auth_service = AuthService()

        # Act: Hash the same password twice
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Assert: Both hashes verify correctly
        assert auth_service.verify_password(password, hash1) is True, (
            "First hash must verify correctly"
        )
        assert auth_service.verify_password(password, hash2) is True, (
            "Second hash must verify correctly"
        )
