"""Cache service with tenant-prefixed keys for multi-tenancy support.

This module provides a CacheService class that automatically prefixes
all cache keys with the tenant_id to ensure cache isolation between tenants.
"""

import json
from typing import Any

from redis import Redis


class CacheService:
    """Cache service with tenant-prefixed keys.

    All cache operations are automatically scoped to the current tenant
    by prefixing keys with the tenant_id.

    Key format: {tenant_id}:cache:{entity}:{id}

    Attributes:
        redis: The Redis client.
        tenant_id: The current tenant's ID.
    """

    DEFAULT_TTL = 3600  # 1 hour default TTL

    def __init__(self, redis: Redis, tenant_id: int):
        """Initialize the cache service.

        Args:
            redis: The Redis client.
            tenant_id: The current tenant's ID.
        """
        self.redis = redis
        self.tenant_id = tenant_id

    def _key(self, entity: str, id: str) -> str:
        """Generate tenant-prefixed cache key.

        Args:
            entity: The entity type (e.g., "student", "teacher").
            id: The entity identifier.

        Returns:
            The formatted cache key: {tenant_id}:cache:{entity}:{id}
        """
        return f"{self.tenant_id}:cache:{entity}:{id}"

    def get(self, entity: str, id: str) -> dict[str, Any] | None:
        """Get cached value.

        Args:
            entity: The entity type.
            id: The entity identifier.

        Returns:
            The cached value as a dictionary, or None if not found.
        """
        key = self._key(entity, id)
        value = self.redis.get(key)

        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(
        self,
        entity: str,
        id: str,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set cached value with TTL.

        Args:
            entity: The entity type.
            id: The entity identifier.
            value: The value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. Defaults to DEFAULT_TTL.
        """
        key = self._key(entity, id)
        ttl = ttl if ttl is not None else self.DEFAULT_TTL

        serialized = json.dumps(value, default=str)
        self.redis.setex(key, ttl, serialized)

    def invalidate(self, entity: str, id: str) -> bool:
        """Invalidate (delete) cache entry.

        Args:
            entity: The entity type.
            id: The entity identifier.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        key = self._key(entity, id)
        return bool(self.redis.delete(key))

    def invalidate_pattern(self, entity: str) -> int:
        """Invalidate all cache entries for an entity type.

        Args:
            entity: The entity type.

        Returns:
            The number of keys deleted.
        """
        pattern = f"{self.tenant_id}:cache:{entity}:*"
        keys = list(self.redis.scan_iter(match=pattern))

        if not keys:
            return 0

        return self.redis.delete(*keys)

    def exists(self, entity: str, id: str) -> bool:
        """Check if cache entry exists.

        Args:
            entity: The entity type.
            id: The entity identifier.

        Returns:
            True if the key exists, False otherwise.
        """
        key = self._key(entity, id)
        return bool(self.redis.exists(key))

    def get_ttl(self, entity: str, id: str) -> int:
        """Get remaining TTL for cache entry.

        Args:
            entity: The entity type.
            id: The entity identifier.

        Returns:
            The remaining TTL in seconds, -2 if key doesn't exist,
            -1 if key has no expiry.
        """
        key = self._key(entity, id)
        return self.redis.ttl(key)

    def set_many(
        self,
        entity: str,
        items: dict[str, dict[str, Any]],
        ttl: int | None = None,
    ) -> None:
        """Set multiple cache entries at once.

        Args:
            entity: The entity type.
            items: Dictionary mapping IDs to values.
            ttl: Time-to-live in seconds. Defaults to DEFAULT_TTL.
        """
        ttl = ttl if ttl is not None else self.DEFAULT_TTL
        pipe = self.redis.pipeline()

        for id, value in items.items():
            key = self._key(entity, id)
            serialized = json.dumps(value, default=str)
            pipe.setex(key, ttl, serialized)

        pipe.execute()

    def get_many(
        self,
        entity: str,
        ids: list[str],
    ) -> dict[str, dict[str, Any] | None]:
        """Get multiple cache entries at once.

        Args:
            entity: The entity type.
            ids: List of entity identifiers.

        Returns:
            Dictionary mapping IDs to cached values (or None if not found).
        """
        if not ids:
            return {}

        keys = [self._key(entity, id) for id in ids]
        values = self.redis.mget(keys)

        result = {}
        for id, value in zip(ids, values, strict=False):
            if value is None:
                result[id] = None
            else:
                try:
                    result[id] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[id] = None

        return result

    def invalidate_tenant(self) -> int:
        """Invalidate all cache entries for the current tenant.

        Returns:
            The number of keys deleted.
        """
        pattern = f"{self.tenant_id}:cache:*"
        keys = list(self.redis.scan_iter(match=pattern))

        if not keys:
            return 0

        return self.redis.delete(*keys)
