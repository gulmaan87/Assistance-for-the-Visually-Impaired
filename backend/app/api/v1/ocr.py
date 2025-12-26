import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from app.models.ocr import OCRRequest, OCRResponse
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.clients.storage_client import StorageClient
from app.services import cache, ocr
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=OCRResponse)
async def run_ocr_endpoint(
    payload: OCRRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"[{request_id}] OCR request for image_url={payload.image_url}, subject={subject}, idempotency_key={idem_key}")
    storage = StorageClient()
    try:
        validated_url = storage.validate_image_url(str(payload.image_url))
    except ValueError as exc:
        logger.warning(f"[{request_id}] Invalid image URL: {exc}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if idem_key and (prior := await cache.idempotency_check(redis, idem_key)):
        logger.info(f"[{request_id}] Idempotency hit for key={idem_key}")
        return OCRResponse(
            text=prior,
            confidence=1.0,
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_ocr_seconds,
        )

    allowed = await cache.rate_limit(redis, subject)
    if not allowed:
        logger.warning(f"[{request_id}] Rate limit exceeded for subject={subject}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    if cached := await cache.get_cached_ocr(redis, validated_url):
        logger.info(f"[{request_id}] Cache hit for image_url={validated_url}")
        return OCRResponse(
            text=cached["text"],
            confidence=cached["confidence"],
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    lock_key = cache.ocr_lock_key(validated_url)
    result = await cache.with_lock(
        redis, lock_key, settings.lock_ttl_seconds, ocr.run_ocr(validated_url, payload.locale)
    )
    # If lock not acquired, check cache again
    if result is None:
        logger.info(f"[{request_id}] Lock not acquired, checking cache again")
        if cached := await cache.get_cached_ocr(redis, validated_url):
            return OCRResponse(
                text=cached["text"],
                confidence=cached["confidence"],
                request_id=request_id,
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        logger.warning(f"[{request_id}] Lock unavailable and cache miss, returning 503")
        raise HTTPException(status_code=503, detail="Please retry")

    text, confidence = result
    logger.info(f"[{request_id}] OCR completed: text_length={len(text)}, confidence={confidence}")
    ttl = await cache.set_cached_ocr(redis, validated_url, text, confidence)
    if idem_key:
        await cache.set_idempotency(redis, idem_key, text, ttl)
        logger.info(f"[{request_id}] Stored idempotency key for future replay")

    return OCRResponse(
        text=text,
        confidence=confidence,
        request_id=request_id,
        cache_hit=False,
        ttl_seconds=ttl,
    )

