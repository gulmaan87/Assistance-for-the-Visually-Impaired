from fastapi import APIRouter, Depends, HTTPException, status, Header
from app.models.ocr import OCRRequest, OCRResponse
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.clients.storage_client import StorageClient
from app.services import cache, ocr
from app.core.config import settings

router = APIRouter()


@router.post("", response_model=OCRResponse)
async def run_ocr_endpoint(
    payload: OCRRequest,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    storage = StorageClient()
    try:
        validated_url = storage.validate_image_url(str(payload.image_url))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if idem_key and (prior := await cache.idempotency_check(redis, idem_key)):
        return OCRResponse(
            text=prior,
            confidence=1.0,
            request_id="replay",
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_ocr_seconds,
        )

    allowed = await cache.rate_limit(redis, subject)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    if cached := await cache.get_cached_ocr(redis, validated_url):
        return OCRResponse(
            text=cached["text"],
            confidence=cached["confidence"],
            request_id="cache",
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    lock_key = cache.ocr_lock_key(validated_url)
    result = await cache.with_lock(
        redis, lock_key, settings.lock_ttl_seconds, ocr.run_ocr(validated_url, payload.locale)
    )
    # If lock not acquired, check cache again
    if result is None:
        if cached := await cache.get_cached_ocr(redis, str(payload.image_url)):
            return OCRResponse(
                text=cached["text"],
                confidence=cached["confidence"],
                request_id="cache",
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        raise HTTPException(status_code=503, detail="Please retry")

    text, confidence = result
    ttl = await cache.set_cached_ocr(redis, validated_url, text, confidence)
    if idem_key:
        await cache.set_idempotency(redis, idem_key, text, ttl)

    return OCRResponse(
        text=text,
        confidence=confidence,
        request_id="run",
        cache_hit=False,
        ttl_seconds=ttl,
    )

