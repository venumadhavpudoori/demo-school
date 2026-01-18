"""Property-based tests for cache invalidation on update.

**Feature: school-erp-multi-tenancy, Property 16: Cache Invalidation on Update**
**Validates: Design - Property 16**

Property 16: Cache Invalidation on Update
*For any* entity update operation, the corresponding cache entry SHALL be invalidated
(removed or updated) before the operation completes.
"""

from typing import Any
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
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=1,
    max_size=50,
)

# Strategy for cache values (simple dictionaries)
cache_value_strategy = st.fixed_dictionaries({
    "id": st.integers(min_value=1, max_value=1_000_000),
    "name": st.text(min_size=1, max_size=100),
    "data": st.text(min_size=0, max_size=200),
})


class TestCacheInvalidationOnUpdate:
    """**Feature: school-erp-multi-tenancy, Property 16: Cache Invalidation on Update**"""

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
        initial_value=cache_value_strategy,
    )
    @settings(max_examples=100)
    def test_invalidate_removes_cached_entry(
        self,
        tenant_id: int,
        entity: str,
        entity_id: str,
        initial_value: dict[str, Any],
    ):
        """For any cached entity, calling invalidate SHALL remove the cache entry.

        This tests that after invalidation, the cache entry no longer exists.

        **Validates: Requirements 16.3**
        """
        # Arrange: Create a mock Redis client that tracks state
        cache_store: dict[str, str] = {}

        mock_redis = MagicMock()

        def mock_setex(key: str, ttl: int, value: str) -> None:
            cache_store[key] = value

        def mock_get(key: str) -> str | None:
            return cache_store.get(key)

        def mock_delete(key: str) -> int:
            if key in cache_store:
                del cache_store[key]
                return 1
            return 0

        def mock_exists(key: str) -> int:
            return 1 if key in cache_store else 0

        mock_redis.setex = mock_setex
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete
        mock_redis.exists = mock_exists

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Set a value in cache, then invalidate it
        cache_service.set(entity, entity_id, initial_value)

        # Verify the value was cached
        assert cache_service.exists(entity, entity_id), "Value should be cached before invalidation"

        # Invalidate the cache entry
        result = cache_service.invalidate(entity, entity_id)

        # Assert: The cache entry should be removed
        assert result is True, "Invalidate should return True when entry existed"
        assert not cache_service.exists(entity, entity_id), (
            "Cache entry should not exist after invalidation"
        )
        assert cache_service.get(entity, entity_id) is None, (
            "Get should return None after invalidation"
        )

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_invalidate_nonexistent_entry_returns_false(
        self,
        tenant_id: int,
        entity: str,
        entity_id: str,
    ):
        """For any non-existent cache entry, invalidate SHALL return False.

        **Validates: Requirements 16.3**
        """
        # Arrange: Create a mock Redis client with empty cache
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 0

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Try to invalidate a non-existent entry
        result = cache_service.invalidate(entity, entity_id)

        # Assert: Should return False for non-existent entry
        assert result is False, "Invalidate should return False when entry doesn't exist"

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
        initial_value=cache_value_strategy,
        updated_value=cache_value_strategy,
    )
    @settings(max_examples=100)
    def test_invalidate_then_set_updates_cache(
        self,
        tenant_id: int,
        entity: str,
        entity_id: str,
        initial_value: dict[str, Any],
        updated_value: dict[str, Any],
    ):
        """For any entity update, invalidate followed by set SHALL update the cached value.

        This simulates the pattern: invalidate old cache -> update DB -> set new cache.

        **Validates: Requirements 16.3**
        """
        import json

        # Arrange: Create a mock Redis client that tracks state
        cache_store: dict[str, str] = {}

        mock_redis = MagicMock()

        def mock_setex(key: str, ttl: int, value: str) -> None:
            cache_store[key] = value

        def mock_get(key: str) -> bytes | None:
            value = cache_store.get(key)
            return value.encode() if value else None

        def mock_delete(key: str) -> int:
            if key in cache_store:
                del cache_store[key]
                return 1
            return 0

        mock_redis.setex = mock_setex
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Set initial value, invalidate, then set updated value
        cache_service.set(entity, entity_id, initial_value)
        cache_service.invalidate(entity, entity_id)
        cache_service.set(entity, entity_id, updated_value)

        # Assert: Cache should contain the updated value
        cached_value = cache_service.get(entity, entity_id)
        assert cached_value is not None, "Cache should contain the updated value"
        assert cached_value["id"] == updated_value["id"], "Cached ID should match updated value"
        assert cached_value["name"] == updated_value["name"], "Cached name should match updated value"

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_ids=st.lists(entity_id_strategy, min_size=2, max_size=5, unique=True),
        values=st.lists(cache_value_strategy, min_size=2, max_size=5),
    )
    @settings(max_examples=100)
    def test_invalidate_only_affects_specified_entry(
        self,
        tenant_id: int,
        entity: str,
        entity_ids: list[str],
        values: list[dict[str, Any]],
    ):
        """For any invalidation, only the specified cache entry SHALL be removed.

        Other cache entries for the same entity type should remain intact.

        **Validates: Requirements 16.3**
        """
        import json

        # Ensure we have matching counts
        count = min(len(entity_ids), len(values))
        entity_ids = entity_ids[:count]
        values = values[:count]

        if count < 2:
            return  # Need at least 2 entries to test isolation

        # Arrange: Create a mock Redis client that tracks state
        cache_store: dict[str, str] = {}

        mock_redis = MagicMock()

        def mock_setex(key: str, ttl: int, value: str) -> None:
            cache_store[key] = value

        def mock_get(key: str) -> bytes | None:
            value = cache_store.get(key)
            return value.encode() if value else None

        def mock_delete(key: str) -> int:
            if key in cache_store:
                del cache_store[key]
                return 1
            return 0

        def mock_exists(key: str) -> int:
            return 1 if key in cache_store else 0

        mock_redis.setex = mock_setex
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete
        mock_redis.exists = mock_exists

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Set all values in cache
        for entity_id, value in zip(entity_ids, values, strict=False):
            cache_service.set(entity, entity_id, value)

        # Invalidate only the first entry
        invalidated_id = entity_ids[0]
        cache_service.invalidate(entity, invalidated_id)

        # Assert: Only the invalidated entry should be removed
        assert not cache_service.exists(entity, invalidated_id), (
            f"Invalidated entry {invalidated_id} should not exist"
        )

        # All other entries should still exist
        for entity_id in entity_ids[1:]:
            assert cache_service.exists(entity, entity_id), (
                f"Non-invalidated entry {entity_id} should still exist"
            )

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_ids=st.lists(entity_id_strategy, min_size=1, max_size=5, unique=True),
        values=st.lists(cache_value_strategy, min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_invalidate_pattern_removes_all_entity_entries(
        self,
        tenant_id: int,
        entity: str,
        entity_ids: list[str],
        values: list[dict[str, Any]],
    ):
        """For any entity type, invalidate_pattern SHALL remove all cache entries of that type.

        **Validates: Requirements 16.3**
        """
        import json

        # Ensure we have matching counts
        count = min(len(entity_ids), len(values))
        entity_ids = entity_ids[:count]
        values = values[:count]

        # Arrange: Create a mock Redis client that tracks state
        cache_store: dict[str, str] = {}

        mock_redis = MagicMock()

        def mock_setex(key: str, ttl: int, value: str) -> None:
            cache_store[key] = value

        def mock_scan_iter(match: str) -> list[str]:
            # Simple pattern matching for tenant:cache:entity:*
            prefix = match.rstrip("*")
            return [k for k in cache_store.keys() if k.startswith(prefix)]

        def mock_delete(*keys: str) -> int:
            deleted = 0
            for key in keys:
                if key in cache_store:
                    del cache_store[key]
                    deleted += 1
            return deleted

        def mock_exists(key: str) -> int:
            return 1 if key in cache_store else 0

        mock_redis.setex = mock_setex
        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = mock_delete
        mock_redis.exists = mock_exists

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Set all values in cache
        for entity_id, value in zip(entity_ids, values, strict=False):
            cache_service.set(entity, entity_id, value)

        # Verify all entries exist
        for entity_id in entity_ids:
            assert cache_service.exists(entity, entity_id), (
                f"Entry {entity_id} should exist before pattern invalidation"
            )

        # Invalidate all entries for the entity type
        deleted_count = cache_service.invalidate_pattern(entity)

        # Assert: All entries should be removed
        assert deleted_count == len(entity_ids), (
            f"Should have deleted {len(entity_ids)} entries, but deleted {deleted_count}"
        )

        for entity_id in entity_ids:
            assert not cache_service.exists(entity, entity_id), (
                f"Entry {entity_id} should not exist after pattern invalidation"
            )

    @given(
        tenant_id=tenant_id_strategy,
        entity=entity_strategy,
        entity_id=entity_id_strategy,
        value=cache_value_strategy,
    )
    @settings(max_examples=100)
    def test_cache_key_used_for_invalidation_matches_set_key(
        self,
        tenant_id: int,
        entity: str,
        entity_id: str,
        value: dict[str, Any],
    ):
        """For any cache operation, the key used for invalidation SHALL match the key used for set.

        This ensures that invalidation targets the correct cache entry.

        **Validates: Requirements 16.3**
        """
        # Arrange: Track the keys used in operations
        set_keys: list[str] = []
        delete_keys: list[str] = []

        mock_redis = MagicMock()

        def mock_setex(key: str, ttl: int, value: str) -> None:
            set_keys.append(key)

        def mock_delete(key: str) -> int:
            delete_keys.append(key)
            return 1

        mock_redis.setex = mock_setex
        mock_redis.delete = mock_delete

        cache_service = CacheService(redis=mock_redis, tenant_id=tenant_id)

        # Act: Set a value, then invalidate it
        cache_service.set(entity, entity_id, value)
        cache_service.invalidate(entity, entity_id)

        # Assert: The same key should be used for both operations
        assert len(set_keys) == 1, "Should have one set operation"
        assert len(delete_keys) == 1, "Should have one delete operation"
        assert set_keys[0] == delete_keys[0], (
            f"Set key '{set_keys[0]}' should match delete key '{delete_keys[0]}'"
        )

        # Verify the key format
        expected_key = f"{tenant_id}:cache:{entity}:{entity_id}"
        assert set_keys[0] == expected_key, (
            f"Key should follow format {{tenant_id}}:cache:{{entity}}:{{id}}, "
            f"expected '{expected_key}', got '{set_keys[0]}'"
        )
