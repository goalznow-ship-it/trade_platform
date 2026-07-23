import redis.asyncio as aioredis
from app.core.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

async def get_redis():
    return redis_client

async def cache_get(key: str):
    return await redis_client.get(key)

async def cache_set(key: str, value: str, ttl: int = 60):
    await redis_client.setex(key, ttl, value)

async def cache_delete(key: str):
    await redis_client.delete(key)

async def publish(channel: str, message: str):
    await redis_client.publish(channel, message)

async def subscribe(channel: str):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub
