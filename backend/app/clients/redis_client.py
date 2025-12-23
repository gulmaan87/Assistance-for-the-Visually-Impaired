import aioredis
from functools import lru_cache
from app.core.config import settings


@lru_cache
def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)

