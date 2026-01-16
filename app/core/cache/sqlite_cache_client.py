"""
SQLite-based cache client to replace Redis.
Provides similar functionality with local persistence.
"""

import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import os

logger = logging.getLogger(__name__)


class SQLiteCacheClient:
    """SQLite-based cache client with TTL support."""

    def __init__(self, db_path: str = "whisp_cache.db"):
        """
        Initialize SQLite cache client.

        Args:
            db_path: Path to SQLite database file for cache
        """
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize the cache database and create tables if needed."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at TEXT,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON cache(expires_at)
                    """
                )
                await db.commit()

            self._initialized = True
            logger.info(f"SQLite cache initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize SQLite cache: {e}")
            self._initialized = False

    @property
    def is_connected(self) -> bool:
        """Check if cache is initialized."""
        return self._initialized

    async def _ensure_initialized(self):
        """Ensure cache is initialized before operations."""
        if not self._initialized:
            await self.initialize()

    async def _cleanup_expired(self, db: aiosqlite.Connection):
        """Remove expired entries from cache."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """
                DELETE FROM cache 
                WHERE expires_at IS NOT NULL 
                AND expires_at < ?
                """,
                (now,),
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup expired entries: {e}")

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in cache.

        Args:
            key: Cache key
            value: Value to store (should be string/serialized)
            ttl: Time to live in seconds (optional)

        Returns:
            bool: True if successful
        """
        await self._ensure_initialized()

        try:
            expires_at = None
            if ttl:
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=ttl)
                ).isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, value, expires_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, value, expires_at),
                )
                await db.commit()

                # Periodically cleanup expired entries (every 100th set)
                import random

                if random.randint(1, 100) == 1:
                    await self._cleanup_expired(db)

            return True

        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[str]: Value if found and not expired, None otherwise
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                now = datetime.now(timezone.utc).isoformat()
                cursor = await db.execute(
                    """
                    SELECT value FROM cache
                    WHERE key = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (key, now),
                )
                row = await cursor.fetchone()

                if row:
                    return row[0]

            return None

        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    async def delete(self, key: str) -> int:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            int: Number of rows deleted
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM cache WHERE key = ?", (key,)
                )
                await db.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return 0

    async def exists(self, key: str) -> int:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            int: 1 if exists and not expired, 0 otherwise
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                now = datetime.now(timezone.utc).isoformat()
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) FROM cache
                    WHERE key = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (key, now),
                )
                row = await cursor.fetchone()
                return row[0] if row else 0

        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return 0

    async def keys(self, pattern: str) -> list[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*")
                    Uses SQL LIKE syntax internally

        Returns:
            list[str]: List of matching keys
        """
        await self._ensure_initialized()

        try:
            # Convert Redis pattern to SQL LIKE pattern
            # Redis: "user:*" -> SQL: "user:%"
            sql_pattern = pattern.replace("*", "%").replace("?", "_")

            async with aiosqlite.connect(self.db_path) as db:
                now = datetime.now(timezone.utc).isoformat()
                cursor = await db.execute(
                    """
                    SELECT key FROM cache
                    WHERE key LIKE ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (sql_pattern, now),
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []

    async def expire(self, key: str, ttl: int) -> int:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            int: 1 if successful, 0 otherwise
        """
        await self._ensure_initialized()

        try:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=ttl)
            ).isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    UPDATE cache
                    SET expires_at = ?
                    WHERE key = ?
                    """,
                    (expires_at, key),
                )
                await db.commit()
                return 1 if cursor.rowcount > 0 else 0

        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return 0

    async def incr(self, key: str) -> Optional[int]:
        """
        Increment a numeric key by 1.

        Args:
            key: Cache key

        Returns:
            Optional[int]: New value after increment, None on error
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get current value
                now = datetime.now(timezone.utc).isoformat()
                cursor = await db.execute(
                    """
                    SELECT value, expires_at FROM cache
                    WHERE key = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (key, now),
                )
                row = await cursor.fetchone()

                if row:
                    # Increment existing value
                    current_value = int(row[0])
                    new_value = current_value + 1
                    expires_at = row[1]

                    await db.execute(
                        """
                        UPDATE cache
                        SET value = ?
                        WHERE key = ?
                        """,
                        (str(new_value), key),
                    )
                else:
                    # Initialize to 1
                    new_value = 1
                    await db.execute(
                        """
                        INSERT INTO cache (key, value)
                        VALUES (?, ?)
                        """,
                        (key, str(new_value)),
                    )

                await db.commit()
                return new_value

        except Exception as e:
            logger.error(f"Failed to increment key {key}: {e}")
            return None

    async def incrby(self, key: str, amount: int) -> Optional[int]:
        """
        Increment a numeric key by specified amount.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            Optional[int]: New value after increment, None on error
        """
        await self._ensure_initialized()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get current value
                now = datetime.now(timezone.utc).isoformat()
                cursor = await db.execute(
                    """
                    SELECT value, expires_at FROM cache
                    WHERE key = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (key, now),
                )
                row = await cursor.fetchone()

                if row:
                    # Increment existing value
                    current_value = int(row[0])
                    new_value = current_value + amount
                    expires_at = row[1]

                    await db.execute(
                        """
                        UPDATE cache
                        SET value = ?
                        WHERE key = ?
                        """,
                        (str(new_value), key),
                    )
                else:
                    # Initialize to amount
                    new_value = amount
                    await db.execute(
                        """
                        INSERT INTO cache (key, value)
                        VALUES (?, ?)
                        """,
                        (key, str(new_value)),
                    )

                await db.commit()
                return new_value

        except Exception as e:
            logger.error(f"Failed to increment key {key} by {amount}: {e}")
            return None
