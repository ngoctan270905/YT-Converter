import redis.asyncio as redis
import redis
from app.core.config import settings

_async_redis_client = None
_sync_redis_client = None

def get_redis_client():
    """Get async Redis client."""
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _async_redis_client


def get_sync_redis_client():
    """Get sync Redis client for Celery tasks."""
    global _sync_redis_client
    if _sync_redis_client is None:
        _sync_redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _sync_redis_client
