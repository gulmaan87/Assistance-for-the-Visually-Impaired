from typing import AsyncIterator
from contextlib import asynccontextmanager
from app.clients.redis_client import get_redis


@asynccontextmanager
async def redis_dep() -> AsyncIterator:
    redis = get_redis()
    try:
        yield redis
    finally:
        # aioredis uses connection pools; explicit close not required per request.
        pass

