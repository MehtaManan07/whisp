from typing import Any, List, Optional
import json
import logging
from .redis_client import RedisClient


class CacheService:
    """Cache service for Redis operations."""

    def __init__(self, redis_client: RedisClient):
        """
        Initialize the cache service.

        Args:
            redis_client: RedisClient instance injected via FastAPI dependencies.
        """
        self._redis_client = redis_client

    def _ensure_redis_connected(self) -> bool:
        """Ensure Redis is connected, return False if not available."""
        if not self._redis_client.is_connected:
            return False
        return True

    def set_key(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis with optional TTL.

        Args:
            key: The key to set
            value: The value to store (will be JSON serialized)
            ttl: Time to live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._ensure_redis_connected():
            return False

        try:
            # Serialize value to JSON
            serialized_value = json.dumps(value)

            if ttl:
                self._redis_client.client.setex(key, ttl, serialized_value)
            else:
                self._redis_client.client.set(key, serialized_value)

            return True

        except Exception as e:
            return False

    def set_key_ex(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set a key-value pair in Redis with optional TTL.
        """
        if not self._ensure_redis_connected():
            return False

        try:
            self._redis_client.client.setex(key, ttl, value)
            return True
        except Exception as e:
            return False

    def get_key(self, key: str) -> Any:
        """
        Get a value from Redis by key.

        Args:
            key: The key to retrieve

        Returns:
            Any: The deserialized value, or None if key doesn't exist or error occurs
        """
        if not self._ensure_redis_connected():
            return None

        try:
            value = self._redis_client.client.get(key)
            if value is None:
                return None

            # Deserialize from JSON
            return json.loads(value)

        except Exception as e:
            return None

    def delete_key(self, key: str) -> bool:
        """
        Delete a key from Redis.

        Args:
            key: The key to delete

        Returns:
            bool: True if key was deleted, False otherwise
        """
        if not self._ensure_redis_connected():
            return False

        try:
            result = self._redis_client.client.delete(key)
            return result > 0

        except Exception as e:
            return False

    def increment_key(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric key by the specified amount.

        Args:
            key: The key to increment
            amount: The amount to increment by (default: 1)

        Returns:
            int: The new value after increment, or None if error occurs
        """
        if not self._ensure_redis_connected():
            return None

        try:
            if amount == 1:
                result = self._redis_client.client.incr(key)
            else:
                result = self._redis_client.client.incrby(key, amount)

            return result

        except Exception as e:
            return None

    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: The pattern to match (e.g., "user:*", "session:*")

        Returns:
            List[str]: List of matching keys, empty list if error occurs
        """
        if not self._ensure_redis_connected():
            return []

        try:
            keys = self._redis_client.client.keys(pattern)
            return keys

        except Exception as e:
            return []

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.

        Args:
            key: The key to check

        Returns:
            bool: True if key exists, False otherwise
        """
        if not self._ensure_redis_connected():
            return False

        try:
            result = self._redis_client.client.exists(key)
            return result > 0

        except Exception as e:
            return False

    def expire_key(self, key: str, time: int) -> bool:
        """
        Mark a key as expired in redis

        Args:
            key: The key to expire
            time: when to expire a key

        Returns:
            bool: True if key is set to expire, False otherwise
        """
        if not self._ensure_redis_connected():
            return False

        try:
            result = self._redis_client.client.expire(key, time)
            return result > 0

        except Exception as e:
            return False
