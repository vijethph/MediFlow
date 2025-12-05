"""Redis caching utilities."""
from typing import Optional, Any
import json
import redis.asyncio as redis
from config import settings
import logging

logger = logging.getLogger(__name__)

# Redis connection pool
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = redis.from_url(
            f"redis://{getattr(settings, 'REDIS_HOST', 'localhost')}:{getattr(settings, 'REDIS_PORT', 6379)}",
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Caching disabled.")
        redis_client = None


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def get_cache(key: str) -> Optional[Any]:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None
    """
    if not redis_client:
        return None
    
    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def set_cache(key: str, value: Any, ttl: int = 3600):
    """
    Set value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 1 hour)
    """
    if not redis_client:
        return
    
    try:
        await redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
    except Exception as e:
        logger.error(f"Cache set error: {e}")


async def delete_cache(key: str):
    """
    Delete value from cache.
    
    Args:
        key: Cache key
    """
    if not redis_client:
        return
    
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Cache delete error: {e}")


async def delete_cache_pattern(pattern: str):
    """
    Delete all keys matching pattern.
    
    Args:
        pattern: Key pattern (e.g., "patient:*")
    """
    if not redis_client:
        return
    
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Cache delete pattern error: {e}")

