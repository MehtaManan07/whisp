from typing import Any, List, Optional
import json
import logging
from .sqlite_cache_client import SQLiteCacheClient


class CacheService:
    """Cache service for SQLite-based caching operations."""

    def __init__(self, cache_client: SQLiteCacheClient):
        """
        Initialize the cache service.

        Args:
            cache_client: SQLiteCacheClient instance injected via FastAPI dependencies.
        """
        self._cache_client = cache_client

    async def _ensure_cache_connected(self) -> bool:
        """Ensure cache is connected, return False if not available."""
        if not self._cache_client.is_connected:
            await self._cache_client.initialize()
        return self._cache_client.is_connected

    async def set_key(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in cache with optional TTL.

        Args:
            key: The key to set
            value: The value to store (will be JSON serialized)
            ttl: Time to live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        if not await self._ensure_cache_connected():
            return False

        try:
            # Serialize value to JSON
            serialized_value = json.dumps(value)
            return await self._cache_client.set(key, serialized_value, ttl)

        except Exception as e:
            return False

    async def set_key_ex(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set a key-value pair in cache with TTL.
        """
        if not await self._ensure_cache_connected():
            return False

        try:
            # If value is already a string, use it directly
            if isinstance(value, str):
                return await self._cache_client.set(key, value, ttl)
            else:
                serialized_value = json.dumps(value)
                return await self._cache_client.set(key, serialized_value, ttl)
        except Exception as e:
            return False

    async def get_key(self, key: str) -> Any:
        """
        Get a value from cache by key.

        Args:
            key: The key to retrieve

        Returns:
            Any: The deserialized value, or None if key doesn't exist or error occurs
        """
        if not await self._ensure_cache_connected():
            return None

        try:
            value = await self._cache_client.get(key)
            if value is None:
                return None

            # Deserialize from JSON
            return json.loads(value)

        except Exception as e:
            return None

    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: The key to delete

        Returns:
            bool: True if key was deleted, False otherwise
        """
        if not await self._ensure_cache_connected():
            return False

        try:
            result = await self._cache_client.delete(key)
            return result > 0

        except Exception as e:
            return False

    async def increment_key(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric key by the specified amount.

        Args:
            key: The key to increment
            amount: The amount to increment by (default: 1)

        Returns:
            int: The new value after increment, or None if error occurs
        """
        if not await self._ensure_cache_connected():
            return None

        try:
            if amount == 1:
                result = await self._cache_client.incr(key)
            else:
                result = await self._cache_client.incrby(key, amount)

            return result

        except Exception as e:
            return None

    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: The pattern to match (e.g., "user:*", "session:*")

        Returns:
            List[str]: List of matching keys, empty list if error occurs
        """
        if not await self._ensure_cache_connected():
            return []

        try:
            keys = await self._cache_client.keys(pattern)
            return keys

        except Exception as e:
            return []

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: The key to check

        Returns:
            bool: True if key exists, False otherwise
        """
        if not await self._ensure_cache_connected():
            return False

        try:
            result = await self._cache_client.exists(key)
            return result > 0

        except Exception as e:
            return False

    async def expire_key(self, key: str, time: int) -> bool:
        """
        Mark a key as expired in cache

        Args:
            key: The key to expire
            time: when to expire a key (in seconds)

        Returns:
            bool: True if key is set to expire, False otherwise
        """
        if not await self._ensure_cache_connected():
            return False

        try:
            result = await self._cache_client.expire(key, time)
            return result > 0

        except Exception as e:
            return False
