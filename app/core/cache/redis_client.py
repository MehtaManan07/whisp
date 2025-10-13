from upstash_redis import Redis
from app.core.config import config
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for connection and initialization."""

    def __init__(self):
        self._client = None
        self._initialize()

    def _initialize(self):
        """Initialize Redis connection."""
        try:
            if not config.redis_url or not config.redis_token:
                logger.warning(
                    "Redis URL or token not configured. Redis functionality will be disabled."
                )
                return

            self._client = Redis(url=config.redis_url, token=config.redis_token)

            # Test connection
            self._client.ping()

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._client = None

    @property
    def client(self) -> Redis:
        """Get the Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client is not initialized")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if Redis client is connected."""
        return self._client is not None

    def reconnect(self):
        """Reconnect to Redis."""
        self._initialize()
