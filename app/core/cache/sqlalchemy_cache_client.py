"""
SQLAlchemy-based cache client.
Uses the main database instead of a separate cache database.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import IntegrityError

from app.core.cache.models import Cache
from app.core.db.engine import run_db

logger = logging.getLogger(__name__)


class SQLAlchemyCacheClient:
    """SQLAlchemy-based cache client with TTL support."""

    def __init__(self):
        pass

    @property
    def is_connected(self) -> bool:
        return True

    def _cleanup_expired_sync(self, db: Session):
        """Remove expired entries from cache (sync)."""
        try:
            now = datetime.now(timezone.utc)
            db.execute(
                delete(Cache).where(
                    Cache.expires_at.isnot(None),
                    Cache.expires_at < now
                )
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to cleanup expired entries: {e}")
            db.rollback()

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        def _set(db: Session) -> bool:
            try:
                expires_at = None
                if ttl:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

                result = db.execute(
                    select(Cache).where(Cache.key == key)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=value, expires_at=expires_at)
                    )
                else:
                    cache_entry = Cache(
                        key=key,
                        value=value,
                        expires_at=expires_at,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

                db.commit()

                import random
                if random.randint(1, 100) == 1:
                    self._cleanup_expired_sync(db)

                return True

            except Exception as e:
                logger.error(f"Failed to set cache key {key}: {e}")
                db.rollback()
                return False

        return await run_db(_set)

    async def get(self, key: str) -> Optional[str]:
        def _get(db: Session) -> Optional[str]:
            try:
                now = datetime.now(timezone.utc)
                result = db.execute(
                    select(Cache.value)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to get cache key {key}: {e}")
                return None

        return await run_db(_get)

    async def delete(self, key: str) -> int:
        def _delete(db: Session) -> int:
            try:
                result = db.execute(
                    delete(Cache).where(Cache.key == key)
                )
                db.commit()
                return result.rowcount or 0
            except Exception as e:
                logger.error(f"Failed to delete cache key {key}: {e}")
                db.rollback()
                return 0

        return await run_db(_delete)

    async def exists(self, key: str) -> int:
        def _exists(db: Session) -> int:
            try:
                now = datetime.now(timezone.utc)
                result = db.execute(
                    select(func.count())
                    .select_from(Cache)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                return result.scalar_one()
            except Exception as e:
                logger.error(f"Failed to check existence of key {key}: {e}")
                return 0

        return await run_db(_exists)

    async def keys(self, pattern: str) -> list[str]:
        def _keys(db: Session) -> list[str]:
            try:
                sql_pattern = pattern.replace("*", "%").replace("?", "_")
                now = datetime.now(timezone.utc)
                result = db.execute(
                    select(Cache.key)
                    .where(Cache.key.like(sql_pattern))
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f"Failed to get keys with pattern {pattern}: {e}")
                return []

        return await run_db(_keys)

    async def expire(self, key: str, ttl: int) -> int:
        def _expire(db: Session) -> int:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
                result = db.execute(
                    update(Cache)
                    .where(Cache.key == key)
                    .values(expires_at=expires_at)
                )
                db.commit()
                return 1 if result.rowcount > 0 else 0
            except Exception as e:
                logger.error(f"Failed to set expiration for key {key}: {e}")
                db.rollback()
                return 0

        return await run_db(_expire)

    async def incr(self, key: str) -> Optional[int]:
        def _incr(db: Session) -> Optional[int]:
            try:
                now = datetime.now(timezone.utc)
                result = db.execute(
                    select(Cache.value, Cache.expires_at)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                row = result.one_or_none()

                if row:
                    current_value = int(row[0])
                    new_value = current_value + 1
                    db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=str(new_value))
                    )
                else:
                    new_value = 1
                    cache_entry = Cache(
                        key=key,
                        value=str(new_value),
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

                db.commit()
                return new_value

            except Exception as e:
                logger.error(f"Failed to increment key {key}: {e}")
                db.rollback()
                return None

        return await run_db(_incr)

    async def incrby(self, key: str, amount: int) -> Optional[int]:
        def _incrby(db: Session) -> Optional[int]:
            try:
                now = datetime.now(timezone.utc)
                result = db.execute(
                    select(Cache.value, Cache.expires_at)
                    .where(Cache.key == key)
                    .where(
                        (Cache.expires_at.is_(None)) | (Cache.expires_at > now)
                    )
                )
                row = result.one_or_none()

                if row:
                    current_value = int(row[0])
                    new_value = current_value + amount
                    db.execute(
                        update(Cache)
                        .where(Cache.key == key)
                        .values(value=str(new_value))
                    )
                else:
                    new_value = amount
                    cache_entry = Cache(
                        key=key,
                        value=str(new_value),
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(cache_entry)

                db.commit()
                return new_value

            except Exception as e:
                logger.error(f"Failed to increment key {key} by {amount}: {e}")
                db.rollback()
                return None

        return await run_db(_incrby)
