import redis.asyncio as redis

from app.core.config import get_settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


async def check_redis() -> bool:
    try:
        return await get_redis().ping()
    except Exception:
        return False
