"""Property-based tests for tenant-prefixed cache keys.

**Feature: school-erp-multi-tenancy, Property 2: Tenant-Prefixed Cache Keys**
**Validates: Design - Property 2**

Property 2: Tenant-Prefixed Cache Keys
*For any* Redis cache operation, the generated cache key SHALL follow the format
`{tenant_id}:cache:{entity}:{id}`.
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.cache_service import CacheService

# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid entity names (non-empty alphanumeric strings with underscores)
entity_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=50,
).filter(lambda s: s and not s.startswith("_") and not s.endswith("_"))

# Strategy for valid entity IDs (non-empty strings)
entity_id_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() == s and len(s) > 0)


class TestTenantPrefixedCacheKeys:
    """**Feature: school-erp-multi-tenancy, Property 2: Tenant-Prefixed Cache Keys**"""

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_cache_key_format_matches_specification(
        self, tenant_id: int, entity: str, entity_id: str
    ):
        """For any cache operation, the key SHALL follow format {tenant_id}:cache:{entity}:{id}.

        **Validates: Requirements 1.3**
        """
        # Arrange: Create a CacheService with a mock Redis client
        mock_redis = MagicMock()
        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Generate the cache key
        generated_key = cache_service._key(entity, entity_id)

        # Assert: Key follows the exact format {tenant_id}:cache:{entity}:{id}
        expected_key = f"{tenant_id}:cache:{entity}:{entity_id}"
        assert generated_key == expected_key, (
            f"Cache key format mismatch. " f"Expected: {expected_key}, Got: {generated_key}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_cache_key_contains_tenant_id_prefix(self, tenant_id: int, entity: str, entity_id: str):
        """For any cache key, it SHALL start with the tenant_id.

        **Validates: Requirements 1.3**
        """
        # Arrange
        mock_redis = MagicMock()
        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act
        generated_key = cache_service._key(entity, entity_id)

        # Assert: Key starts with tenant_id followed by colon
        assert generated_key.startswith(f"{tenant_id}:"), (
            f"Cache key must start with tenant_id. " f"Tenant ID: {tenant_id}, Key: {generated_key}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_cache_key_contains_cache_namespace(self, tenant_id: int, entity: str, entity_id: str):
        """For any cache key, it SHALL contain ':cache:' namespace.

        **Validates: Requirements 1.3**
        """
        # Arrange
        mock_redis = MagicMock()
        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act
        generated_key = cache_service._key(entity, entity_id)

        # Assert: Key contains :cache: namespace
        assert (
            ":cache:" in generated_key
        ), f"Cache key must contain ':cache:' namespace. Key: {generated_key}"

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_cache_key_has_four_parts(self, tenant_id: int, entity: str, entity_id: str):
        """For any cache key, it SHALL have exactly 4 colon-separated parts.

        Format: {tenant_id}:cache:{entity}:{id}

        **Validates: Requirements 1.3**
        """
        # Arrange
        mock_redis = MagicMock()
        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act
        generated_key = cache_service._key(entity, entity_id)

        # Assert: Key has exactly 4 parts when split by ':'
        parts = generated_key.split(":")
        assert len(parts) == 4, (
            f"Cache key must have exactly 4 parts. " f"Got {len(parts)} parts: {parts}"
        )
        assert parts[0] == str(tenant_id), "First part must be tenant_id"
        assert parts[1] == "cache", "Second part must be 'cache'"
        assert parts[2] == entity, "Third part must be entity"
        assert parts[3] == entity_id, "Fourth part must be entity_id"

    @given(
        tenant_id_a=tenant_id_strategy,
        tenant_id_b=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_different_tenants_produce_different_keys(
        self, tenant_id_a: int, tenant_id_b: int, entity: str, entity_id: str
    ):
        """For any two different tenants, cache keys for the same entity SHALL differ.

        This ensures tenant isolation in the cache layer.

        **Validates: Requirements 1.3**
        """
        # Skip if tenant IDs happen to be the same
        if tenant_id_a == tenant_id_b:
            return

        # Arrange
        mock_redis = MagicMock()
        cache_service_a = CacheService(redis=mock_redis, tenant_id=tenant_id_a)
        cache_service_b = CacheService(redis=mock_redis, tenant_id=tenant_id_b)

        # Act
        key_a = cache_service_a._key(entity, entity_id)
        key_b = cache_service_b._key(entity, entity_id)

        # Assert: Keys are different for different tenants
        assert key_a != key_b, (
            f"Different tenants must produce different cache keys. "
            f"Tenant A ({tenant_id_a}): {key_a}, Tenant B ({tenant_id_b}): {key_b}"
        )
