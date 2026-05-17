import pytest
import fakeredis.aioredis
from core.data.redis_cache import RedisCache


@pytest.fixture
def fake_cache():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    cache = RedisCache()
    cache.client = client
    return cache


@pytest.mark.asyncio
async def test_set_and_get(fake_cache):
    await fake_cache.set("test_key", {"foo": "bar"})
    result = await fake_cache.get("test_key")
    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_hset_and_hgetall(fake_cache):
    await fake_cache.hset("test_hash", {"field1": "val1", "field2": "val2"})
    result = await fake_cache.hgetall("test_hash")
    assert result["field1"] == "val1"
