"""
Scene Captioning API endpoint.

Handles scene captioning requests with caching, rate limiting, idempotency,
and distributed locking following the same patterns as OCR endpoint.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from app.models.scene_caption import SceneCaptionRequest, SceneCaptionResponse
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.clients.storage_client import StorageClient
from app.services import cache, scene_caption as scene_caption_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=SceneCaptionResponse)
async def run_scene_caption_endpoint(
    payload: SceneCaptionRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    """
    Generate a natural language caption for an image using BLIP.
    
    Returns a descriptive caption of the scene in the image.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Scene caption request for image_url={payload.image_url}, "
        f"max_length={payload.max_length}, subject={subject}, idempotency_key={idem_key}"
    )
    
    storage = StorageClient()
    try:
        validated_url = storage.validate_image_url(str(payload.image_url))
    except ValueError as exc:
        logger.warning(f"[{request_id}] Invalid image URL: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    # Check idempotency
    if idem_key and (prior := await cache.idempotency_check(redis, idem_key)):
        logger.info(f"[{request_id}] Idempotency hit for key={idem_key}")
        # Parse prior result
        import json
        prior_data = json.loads(prior)
        return SceneCaptionResponse(
            caption=prior_data["caption"],
            confidence=prior_data.get("confidence", 0.85),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_scene_caption_seconds,
        )

    # Rate limiting
    allowed = await cache.rate_limit(redis, subject)
    if not allowed:
        logger.warning(f"[{request_id}] Rate limit exceeded for subject={subject}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    # Check cache
    if cached := await cache.get_cached_scene_caption(
        redis, validated_url, payload.max_length
    ):
        logger.info(f"[{request_id}] Cache hit for image_url={validated_url}")
        return SceneCaptionResponse(
            caption=cached["caption"],
            confidence=cached["confidence"],
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    # Acquire lock and run inference
    lock_key = cache.scene_caption_lock_key(validated_url)
    result = await cache.with_lock(
        redis,
        lock_key,
        settings.lock_ttl_seconds,
        scene_caption_service.run_scene_captioning(validated_url, payload.max_length),
    )
    
    # If lock not acquired, check cache again
    if result is None:
        logger.info(f"[{request_id}] Lock not acquired, checking cache again")
        if cached := await cache.get_cached_scene_caption(
            redis, validated_url, payload.max_length
        ):
            return SceneCaptionResponse(
                caption=cached["caption"],
                confidence=cached["confidence"],
                request_id=request_id,
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        logger.warning(f"[{request_id}] Lock unavailable and cache miss, returning 503")
        raise HTTPException(status_code=503, detail="Please retry")

    caption, confidence = result
    logger.info(
        f"[{request_id}] Scene caption completed: caption_length={len(caption)}, confidence={confidence}"
    )
    
    # Cache results
    ttl = await cache.set_cached_scene_caption(
        redis, validated_url, payload.max_length, caption, confidence
    )
    
    # Store idempotency result
    if idem_key:
        import json
        idem_value = json.dumps({"caption": caption, "confidence": confidence})
        await cache.set_idempotency(redis, idem_key, idem_value, ttl)
        logger.info(f"[{request_id}] Stored idempotency key for future replay")

    return SceneCaptionResponse(
        caption=caption,
        confidence=confidence,
        request_id=request_id,
        cache_hit=False,
        ttl_seconds=ttl,
    )


