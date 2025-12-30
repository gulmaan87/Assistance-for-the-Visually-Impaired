import asyncio
import hashlib
import json
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


# Object Detection Cache Functions
def object_detection_cache_key(image_url: str, confidence_threshold: float) -> str:
    """Generate cache key for object detection results"""
    cache_input = f"{image_url}:{confidence_threshold}"
    digest = hashlib.sha256(cache_input.encode("utf-8")).hexdigest()
    return f"cache:obj_det:{digest}"


def object_detection_lock_key(image_url: str) -> str:
    """Generate lock key for object detection"""
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    return f"lock:obj_det:{digest}"


async def get_cached_object_detection(redis, image_url: str, confidence_threshold: float) -> Optional[dict[str, Any]]:
    """Retrieve cached object detection results"""
    key = object_detection_cache_key(image_url, confidence_threshold)
    data = await redis.get(key)
    if data:
        return {**json.loads(data), "ttl": await redis.ttl(key)}
    return None


async def set_cached_object_detection(redis, image_url: str, confidence_threshold: float, objects: list[dict]) -> int:
    """Cache object detection results"""
    key = object_detection_cache_key(image_url, confidence_threshold)
    ttl = settings.cache_ttl_object_detection_seconds
    await redis.set(key, json.dumps({"objects": objects}), ex=ttl)
    return ttl


# Scene Caption Cache Functions
def scene_caption_cache_key(image_url: str, max_length: int) -> str:
    """Generate cache key for scene caption results"""
    cache_input = f"{image_url}:{max_length}"
    digest = hashlib.sha256(cache_input.encode("utf-8")).hexdigest()
    return f"cache:scene_cap:{digest}"


def scene_caption_lock_key(image_url: str) -> str:
    """Generate lock key for scene captioning"""
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    return f"lock:scene_cap:{digest}"


async def get_cached_scene_caption(redis, image_url: str, max_length: int) -> Optional[dict[str, Any]]:
    """Retrieve cached scene caption results"""
    key = scene_caption_cache_key(image_url, max_length)
    data = await redis.hgetall(key)
    if data:
        return {
            "caption": data.get("caption", ""),
            "confidence": float(data.get("confidence", "0")),
            "ttl": await redis.ttl(key),
        }
    return None


async def set_cached_scene_caption(redis, image_url: str, max_length: int, caption: str, confidence: float) -> int:
    """Cache scene caption results"""
    key = scene_caption_cache_key(image_url, max_length)
    ttl = settings.cache_ttl_scene_caption_seconds
    await redis.hset(key, mapping={"caption": caption, "confidence": confidence})
    await redis.expire(key, ttl)
    return ttl


# Multimodal LLM Cache Functions
def multimodal_llm_cache_key(image_url: str, prompt: str, max_tokens: int, temperature: float) -> str:
    """Generate cache key for multimodal LLM results"""
    cache_input = f"{image_url}:{prompt}:{max_tokens}:{temperature}"
    digest = hashlib.sha256(cache_input.encode("utf-8")).hexdigest()
    return f"cache:mm_llm:{digest}"


def multimodal_llm_lock_key(image_url: str, prompt: str) -> str:
    """Generate lock key for multimodal LLM"""
    cache_input = f"{image_url}:{prompt}"
    digest = hashlib.sha256(cache_input.encode("utf-8")).hexdigest()
    return f"lock:mm_llm:{digest}"


async def get_cached_multimodal_llm(
    redis, image_url: str, prompt: str, max_tokens: int, temperature: float
) -> Optional[dict[str, Any]]:
    """Retrieve cached multimodal LLM results"""
    key = multimodal_llm_cache_key(image_url, prompt, max_tokens, temperature)
    data = await redis.hgetall(key)
    if data:
        return {
            "response": data.get("response", ""),
            "confidence": float(data.get("confidence", "0")) if data.get("confidence") else None,
            "ttl": await redis.ttl(key),
        }
    return None


async def set_cached_multimodal_llm(
    redis, image_url: str, prompt: str, max_tokens: int, temperature: float, response: str, confidence: Optional[float] = None
) -> int:
    """Cache multimodal LLM results"""
    key = multimodal_llm_cache_key(image_url, prompt, max_tokens, temperature)
    ttl = settings.cache_ttl_multimodal_llm_seconds
    mapping = {"response": response}
    if confidence is not None:
        mapping["confidence"] = confidence
    await redis.hset(key, mapping=mapping)
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

