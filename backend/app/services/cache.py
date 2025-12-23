import asyncio
import hashlib
from typing import Any, Optional
from app.core.config import settings


def ocr_cache_key(image_url: str) -> str:
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    return f"cache:ocr:{digest}"


def ocr_lock_key(image_url: str) -> str:
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    return f"lock:ocr:{digest}"


async def get_cached_ocr(redis, image_url: str) -> Optional[dict[str, Any]]:
    key = ocr_cache_key(image_url)
    data = await redis.hgetall(key)
    if data:
        return {
            "text": data.get("text", ""),
            "confidence": float(data.get("confidence", "0")),
            "ttl": await redis.ttl(key),
        }
    return None


async def set_cached_ocr(redis, image_url: str, text: str, confidence: float) -> int:
    key = ocr_cache_key(image_url)
    ttl = settings.cache_ttl_ocr_seconds
    await redis.hset(key, mapping={"text": text, "confidence": confidence})
    await redis.expire(key, ttl)
    return ttl


async def acquire_lock(redis, key: str, ttl: int) -> bool:
    return await redis.set(key, "1", ex=ttl, nx=True)


async def release_lock(redis, key: str) -> None:
    try:
        await redis.delete(key)
    except Exception:
        # Best-effort cleanup
        pass


async def rate_limit(redis, user_id: str) -> bool:
    key = f"rate:user:{user_id}"
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, settings.rate_limit_window_seconds)
    count, _ = await pipe.execute()
    return int(count) <= settings.rate_limit_requests


async def idempotency_check(redis, idem_key: str) -> Optional[str]:
    key = f"idem:{idem_key}"
    return await redis.get(key)


async def set_idempotency(redis, idem_key: str, value: str, ttl: int) -> None:
    await redis.set(f"idem:{idem_key}", value, ex=ttl)


async def with_lock(redis, key: str, ttl: int, coro):
    acquired = await acquire_lock(redis, key, ttl)
    if not acquired:
        # Wait briefly then return None to signal caller to retry/cache check.
        await asyncio.sleep(0.05)
        return None
    try:
        return await coro
    finally:
        await release_lock(redis, key)

