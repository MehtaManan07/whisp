import logging
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from app.core.cache.service import CacheService

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """Information about an API key and its usage."""

    key: str
    usage_today: int
    daily_limit: int
    key_index: int

    @property
    def is_available(self) -> bool:
        """Check if this key is still available for use today."""
        return self.usage_today < self.daily_limit

    @property
    def remaining_requests(self) -> int:
        """Get remaining requests for this key today."""
        return max(0, self.daily_limit - self.usage_today)


class APIKeyManager:
    """
    Manages multiple API keys with daily usage limits and automatic rotation.

    Features:
    - Tracks daily usage per key using Redis
    - Automatically rotates to next available key when limit is reached
    - Resets counters daily
    - Falls back gracefully when Redis is unavailable
    """

    def __init__(
        self,
        cache_service: CacheService,
        key_prefix: str,
        keys: str,
        daily_limit: int = 50,
    ):
        """
        Initialize the API key manager.

        Args:
            cache_service: CacheService instance for Redis operations
            daily_limit: Daily request limit per key
        """
        self.cache_service = cache_service
        self.daily_limit = daily_limit
        self._api_keys = self._load_api_keys(keys)
        self._current_key_index = 0
        self._key_prefix = key_prefix

    def _load_api_keys(self, keys_string: str) -> List[str]:
        """Load API keys from configuration."""
        keys = []

        # First, try the new comma-separated list
        if keys_string:
            keys = [key.strip() for key in keys_string.split(",") if key.strip()]
        if not keys:
            raise ValueError("No API keys provided")
        return keys

    def _get_today_key(self, key_index: int) -> str:
        """Get Redis key for today's usage count for a specific API key."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{self._key_prefix}:{today}:key_{key_index}"

    def _get_key_usage_today(self, key_index: int) -> int:
        """Get today's usage count for a specific key."""
        redis_key = self._get_today_key(key_index)
        usage = self.cache_service.get_key(redis_key)
        return usage if usage is not None else 0

    def _increment_key_usage(self, key_index: int) -> int:
        """Increment usage count for a key and return new count."""
        redis_key = self._get_today_key(key_index)

        # Set TTL to expire at end of day (86400 seconds = 24 hours)
        # This ensures counters reset daily
        new_count = self.cache_service.increment_key(redis_key, 1)

        if new_count == 1:  # First increment of the day
            # Set expiration to end of day
            if self.cache_service._ensure_redis_connected():
                try:
                    # Calculate seconds until end of day
                    now = datetime.now(timezone.utc)
                    end_of_day = now.replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    )
                    seconds_until_eod = int((end_of_day - now).total_seconds()) + 1

                    self.cache_service.expire_key(redis_key, seconds_until_eod)
                except Exception as e:
                    logger.error(f"Failed to set expiration for {redis_key}: {e}")

        return new_count if new_count is not None else 1

    def get_available_key(self) -> Optional[Tuple[str, int]]:
        """
        Get an available API key for making requests.

        Returns:
            Tuple of (api_key, key_index) if available, None if all keys exhausted
        """
        if not self._api_keys:
            return None

        # Try each key starting from current index
        for attempt in range(len(self._api_keys)):
            key_index = (self._current_key_index + attempt) % len(self._api_keys)
            usage_today = self._get_key_usage_today(key_index)

            if usage_today < self.daily_limit:
                # Found an available key
                self._current_key_index = key_index
                api_key = self._api_keys[key_index]

                return api_key, key_index

        # All keys exhausted
        return None

    def record_usage(self, key_index: int) -> bool:
        """
        Record usage for a specific key.

        Args:
            key_index: Index of the key that was used

        Returns:
            bool: True if usage was recorded successfully
        """
        try:
            new_count = self._increment_key_usage(key_index)

            # If this key is now at limit, move to next key for future requests
            if new_count >= self.daily_limit:
                self._current_key_index = (key_index + 1) % len(self._api_keys)

            return True
        except Exception as e:
            return False

    def get_all_key_info(self) -> List[APIKeyInfo]:
        """Get usage information for all configured keys."""
        key_info = []

        for i, api_key in enumerate(self._api_keys):
            usage_today = self._get_key_usage_today(i)
            # Mask the API key for security (show only first 8 and last 4 characters)
            masked_key = (
                f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            )

            key_info.append(
                APIKeyInfo(
                    key=masked_key,
                    usage_today=usage_today,
                    daily_limit=self.daily_limit,
                    key_index=i,
                )
            )

        return key_info

    def get_total_available_requests(self) -> int:
        """Get total remaining requests across all keys today."""
        total_remaining = 0
        for i in range(len(self._api_keys)):
            usage_today = self._get_key_usage_today(i)
            remaining = max(0, self.daily_limit - usage_today)
            total_remaining += remaining

        return total_remaining

    def reset_current_key_index(self):
        """Reset to first key (useful for testing or manual reset)."""
        self._current_key_index = 0
