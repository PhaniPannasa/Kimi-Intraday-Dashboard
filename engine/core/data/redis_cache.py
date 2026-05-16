import json
import redis.asyncio as redis
from config import settings


class RedisCache:
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    async def ping(self):
        return await self.client.ping()

    async def get(self, key: str):
        val = await self.client.get(key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return None

    async def set(self, key: str, value, ex: int = None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=ex)

    async def hgetall(self, key: str):
        return await self.client.hgetall(key)

    async def hset(self, key: str, mapping: dict):
        await self.client.hset(key, mapping=mapping)

    async def hget(self, key: str, field: str):
        return await self.client.hget(key, field)

    async def delete(self, key: str):
        await self.client.delete(key)

    async def zadd(self, key: str, mapping: dict):
        await self.client.zadd(key, mapping)

    async def zrevrange(self, key: str, start: int, end: int, withscores: bool = False):
        return await self.client.zrevrange(key, start, end, withscores=withscores)

    async def sadd(self, key: str, *members):
        await self.client.sadd(key, *members)

    async def smembers(self, key: str):
        return await self.client.smembers(key)


cache = RedisCache()
