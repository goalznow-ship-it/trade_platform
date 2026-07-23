import json
import logging
from typing import Any
from redis.exceptions import RedisError
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


def _cache_unavailable(operation: str, exc: Exception) -> None:
    logger.warning("Redis cache %s unavailable: %s", operation, exc)


class CacheSerializer:
    @staticmethod
    def serialize(data: Any) -> str:
        return json.dumps(data, default=str)

    @staticmethod
    def deserialize(data: str) -> Any:
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data


async def cache_get(key: str) -> Any:
    try:
        data = await redis_client.get(key)
    except (RedisError, RuntimeError, OSError) as exc:
        _cache_unavailable("get", exc)
        return None
    if data is None:
        return None
    return CacheSerializer.deserialize(data)


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    serialized = CacheSerializer.serialize(value)
    try:
        await redis_client.setex(key, ttl, serialized)
    except (RedisError, RuntimeError, OSError) as exc:
        _cache_unavailable("set", exc)


async def cache_delete(key: str) -> None:
    try:
        await redis_client.delete(key)
    except (RedisError, RuntimeError, OSError) as exc:
        _cache_unavailable("delete", exc)


async def cache_exists(key: str) -> bool:
    try:
        return await redis_client.exists(key) > 0
    except (RedisError, RuntimeError, OSError) as exc:
        _cache_unavailable("exists", exc)
        return False


async def cache_clear_pattern(pattern: str) -> int:
    cursor = 0
    deleted = 0
    while True:
        try:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern)
        except (RedisError, RuntimeError, OSError) as exc:
            _cache_unavailable("scan", exc)
            return deleted
        if keys:
            deleted += await redis_client.delete(*keys)
        if cursor == 0:
            break
    return deleted
