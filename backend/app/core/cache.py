import json
from typing import Any, Optional
from app.core.redis import redis_client


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
    data = await redis_client.get(key)
    if data is None:
        return None
    return CacheSerializer.deserialize(data)


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    serialized = CacheSerializer.serialize(value)
    await redis_client.setex(key, ttl, serialized)


async def cache_delete(key: str) -> None:
    await redis_client.delete(key)


async def cache_exists(key: str) -> bool:
    return await redis_client.exists(key) > 0


async def cache_clear_pattern(pattern: str) -> int:
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern)
        if keys:
            deleted += await redis_client.delete(*keys)
        if cursor == 0:
            break
    return deleted
