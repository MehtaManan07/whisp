"""
SQLAlchemy-based cache client.
Uses the main database instead of a separate cache database.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import IntegrityError

from app.core.cache.models import Cache

logger = logging.getLogger(__name__)


class SQLAlchemyCacheClient:
    """SQLAlchemy-based cache client with TTL support."""

    def __init__(self, db_session_factory):
        """
        Initialize SQLAlchemy cache client.

        Args:
            db_session_factory: Factory function to get database sessions
        """
        self.db_session_factory = db_session_factory

    @property
    def is_connected(self) -> bool:
        """Cache is always available when database is available."""
        return True

    async def _cleanup_expired(self, db: AsyncSession):
        """Remove expired entries from cache."""
        try:
            now = datetime.now(timezone.utc)
            await db.execute(
                delete(Cache).where(
                    Cache.expires_at.isnot(None),
                    Cache.expires_at < now
                )
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to cleanup expired entries: {e}")
            await db.rollback()

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
        try:
            expires_at = None
            if ttl:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            async with self.db_session_factory() as db:
                # Check if key exists
                result = await db.execute(
                    select(Cache).where(Cache.key == key)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    await db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=value, expires_at=expires_at)
                    )
                else:
                    # Insert new
                    cache_entry = Cache(
                        key=key,
                        value=value,
                        expires_at=expires_at,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

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
        try:
            async with self.db_session_factory() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(Cache.value)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                row = result.scalar_one_or_none()
                return row

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
        try:
            async with self.db_session_factory() as db:
                result = await db.execute(
                    delete(Cache).where(Cache.key == key)
                )
                await db.commit()
                return result.rowcount or 0

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
        try:
            async with self.db_session_factory() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(func.count())
                    .select_from(Cache)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                count = result.scalar_one()
                return count

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
        try:
            # Convert Redis pattern to SQL LIKE pattern
            sql_pattern = pattern.replace("*", "%").replace("?", "_")

            async with self.db_session_factory() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(Cache.key)
                    .where(Cache.key.like(sql_pattern))
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                rows = result.scalars().all()
                return list(rows)

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
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            async with self.db_session_factory() as db:
                result = await db.execute(
                    update(Cache)
                    .where(Cache.key == key)
                    .values(expires_at=expires_at)
                )
                await db.commit()
                return 1 if result.rowcount > 0 else 0

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
        try:
            async with self.db_session_factory() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(Cache.value, Cache.expires_at)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                row = result.one_or_none()

                if row:
                    # Increment existing value
                    current_value = int(row[0])
                    new_value = current_value + 1

                    await db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=str(new_value))
                    )
                else:
                    # Initialize to 1
                    new_value = 1
                    cache_entry = Cache(
                        key=key,
                        value=str(new_value),
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

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
        try:
            async with self.db_session_factory() as db:
                now = datetime.now(timezone.utc)
                result = await db.execute(
                    select(Cache.value, Cache.expires_at)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                row = result.one_or_none()

                if row:
                    # Increment existing value
                    current_value = int(row[0])
                    new_value = current_value + amount

                    await db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=str(new_value))
                    )
                else:
                    # Initialize to amount
                    new_value = amount
                    cache_entry = Cache(
                        key=key,
                        value=str(new_value),
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

                await db.commit()
                return new_value

        except Exception as e:
            logger.error(f"Failed to increment key {key} by {amount}: {e}")
            return None
