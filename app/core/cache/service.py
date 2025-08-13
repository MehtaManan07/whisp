from typing import Any, List, Optional
import json
import logging
from .redis_client import redis_client

logger = logging.getLogger(__name__)


def _ensure_redis_connected() -> bool:
    """Ensure Redis is connected, return False if not available."""
    if not redis_client.is_connected:
        logger.warning("Redis is not connected. Operation skipped.")
        return False
    return True


def set_key(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a key-value pair in Redis with optional TTL.
    
    Args:
        key: The key to set
        value: The value to store (will be JSON serialized)
        ttl: Time to live in seconds (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not _ensure_redis_connected():
        return False
    
    try:
        # Serialize value to JSON
        serialized_value = json.dumps(value)
        
        if ttl:
            redis_client.client.setex(key, ttl, serialized_value)
        else:
            redis_client.client.set(key, serialized_value)
        
        logger.debug(f"Set key '{key}' with TTL {ttl}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting key '{key}': {e}")
        return False


def get_key(key: str) -> Any:
    """
    Get a value from Redis by key.
    
    Args:
        key: The key to retrieve
    
    Returns:
        Any: The deserialized value, or None if key doesn't exist or error occurs
    """
    if not _ensure_redis_connected():
        return None
    
    try:
        value = redis_client.client.get(key)
        if value is None:
            return None
        
        # Deserialize from JSON
        return json.loads(value)
        
    except Exception as e:
        logger.error(f"Error getting key '{key}': {e}")
        return None


def delete_key(key: str) -> bool:
    """
    Delete a key from Redis.
    
    Args:
        key: The key to delete
    
    Returns:
        bool: True if key was deleted, False otherwise
    """
    if not _ensure_redis_connected():
        return False
    
    try:
        result = redis_client.client.delete(key)
        logger.debug(f"Deleted key '{key}', result: {result}")
        return result > 0
        
    except Exception as e:
        logger.error(f"Error deleting key '{key}': {e}")
        return False


def increment_key(key: str, amount: int = 1) -> Optional[int]:
    """
    Increment a numeric key by the specified amount.
    
    Args:
        key: The key to increment
        amount: The amount to increment by (default: 1)
    
    Returns:
        int: The new value after increment, or None if error occurs
    """
    if not _ensure_redis_connected():
        return None
    
    try:
        if amount == 1:
            result = redis_client.client.incr(key)
        else:
            result = redis_client.client.incrby(key, amount)
        
        logger.debug(f"Incremented key '{key}' by {amount}, new value: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error incrementing key '{key}': {e}")
        return None


def get_keys_by_pattern(pattern: str) -> List[str]:
    """
    Get all keys matching a pattern.
    
    Args:
        pattern: The pattern to match (e.g., "user:*", "session:*")
    
    Returns:
        List[str]: List of matching keys, empty list if error occurs
    """
    if not _ensure_redis_connected():
        return []
    
    try:
        keys = redis_client.client.keys(pattern)
        logger.debug(f"Found {len(keys)} keys matching pattern '{pattern}'")
        return keys
        
    except Exception as e:
        logger.error(f"Error getting keys by pattern '{pattern}': {e}")
        return []


def exists(key: str) -> bool:
    """
    Check if a key exists in Redis.
    
    Args:
        key: The key to check
    
    Returns:
        bool: True if key exists, False otherwise
    """
    if not _ensure_redis_connected():
        return False
    
    try:
        result = redis_client.client.exists(key)
        return result > 0
        
    except Exception as e:
        logger.error(f"Error checking existence of key '{key}': {e}")
        return False
