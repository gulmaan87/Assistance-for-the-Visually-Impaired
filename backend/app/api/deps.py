from typing import AsyncIterator
from app.clients.redis_client import get_redis


async def redis_dep() -> AsyncIterator:
    """
    FastAPI dependency that yields a Redis client.
    The client uses a connection pool; no per-request cleanup needed.
    """
    redis = get_redis()
    yield redis

