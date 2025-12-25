from functools import lru_cache
import redis.asyncio as redis
from app.core.config import settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)

