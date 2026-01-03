"""
Multimodal LLM API endpoints.

Handles multimodal LLM requests (general prompts) and natural language queries
with caching, rate limiting, idempotency, and distributed locking.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from app.models.multimodal_llm import (
    MultimodalLLMRequest,
    MultimodalLLMResponse,
    NaturalLanguageQueryRequest,
    NaturalLanguageQueryResponse,
)
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.clients.storage_client import StorageClient
from app.services import cache, multimodal_llm as mm_llm_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=MultimodalLLMResponse)
async def run_multimodal_llm_endpoint(
    payload: MultimodalLLMRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    """
    Generate a response to a prompt about an image using a multimodal LLM.
    
    This endpoint allows arbitrary prompts about images and returns
    natural language responses based on the image content.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Multimodal LLM request for image_url={payload.image_url}, "
        f"prompt={payload.prompt[:50]}..., subject={subject}, idempotency_key={idem_key}"
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
        import json
        prior_data = json.loads(prior)
        return MultimodalLLMResponse(
            response=prior_data["response"],
            confidence=prior_data.get("confidence"),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_multimodal_llm_seconds,
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
    if cached := await cache.get_cached_multimodal_llm(
        redis,
        validated_url,
        payload.prompt,
        payload.max_tokens,
        payload.temperature,
    ):
        logger.info(f"[{request_id}] Cache hit for image_url={validated_url}")
        return MultimodalLLMResponse(
            response=cached["response"],
            confidence=cached.get("confidence"),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    # Acquire lock and run inference
    lock_key = cache.multimodal_llm_lock_key(validated_url, payload.prompt)
    result = await cache.with_lock(
        redis,
        lock_key,
        settings.lock_ttl_seconds,
        mm_llm_service.run_multimodal_llm(
            validated_url,
            payload.prompt,
            payload.max_tokens,
            payload.temperature,
        ),
    )
    
    # If lock not acquired, check cache again
    if result is None:
        logger.info(f"[{request_id}] Lock not acquired, checking cache again")
        if cached := await cache.get_cached_multimodal_llm(
            redis,
            validated_url,
            payload.prompt,
            payload.max_tokens,
            payload.temperature,
        ):
            return MultimodalLLMResponse(
                response=cached["response"],
                confidence=cached.get("confidence"),
                request_id=request_id,
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        logger.warning(f"[{request_id}] Lock unavailable and cache miss, returning 503")
        raise HTTPException(status_code=503, detail="Please retry")

    response_text, confidence = result
    logger.info(
        f"[{request_id}] Multimodal LLM completed: response_length={len(response_text)}, confidence={confidence}"
    )
    
    # Cache results
    ttl = await cache.set_cached_multimodal_llm(
        redis,
        validated_url,
        payload.prompt,
        payload.max_tokens,
        payload.temperature,
        response_text,
        confidence,
    )
    
    # Store idempotency result
    if idem_key:
        import json
        idem_value = json.dumps({"response": response_text, "confidence": confidence})
        await cache.set_idempotency(redis, idem_key, idem_value, ttl)
        logger.info(f"[{request_id}] Stored idempotency key for future replay")

    return MultimodalLLMResponse(
        response=response_text,
        confidence=confidence,
        request_id=request_id,
        cache_hit=False,
        ttl_seconds=ttl,
    )


@router.post("/query", response_model=NaturalLanguageQueryResponse)
async def natural_language_query_endpoint(
    payload: NaturalLanguageQueryRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    """
    Answer a natural language question about an image.
    
    This is a convenience endpoint that wraps the multimodal LLM with
    a question-answering interface. The question is passed as a prompt
    to the underlying multimodal model.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Natural language query for image_url={payload.image_url}, "
        f"question={payload.question[:50]}..., subject={subject}, idempotency_key={idem_key}"
    )
    
    # Convert question to a prompt format suitable for the model
    # This is a simple format - in production, you might want to use
    # a more sophisticated prompt template
    prompt = f"Question: {payload.question}\nAnswer:"
    
    # Delegate to multimodal LLM endpoint logic
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
        import json
        prior_data = json.loads(prior)
        return NaturalLanguageQueryResponse(
            answer=prior_data["answer"],
            confidence=prior_data.get("confidence"),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_multimodal_llm_seconds,
        )

    # Rate limiting
    allowed = await cache.rate_limit(redis, subject)
    if not allowed:
        logger.warning(f"[{request_id}] Rate limit exceeded for subject={subject}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    # Check cache (use the question as part of the cache key)
    if cached := await cache.get_cached_multimodal_llm(
        redis,
        validated_url,
        prompt,
        payload.max_tokens,
        0.7,  # Default temperature for Q&A
    ):
        logger.info(f"[{request_id}] Cache hit for image_url={validated_url}")
        return NaturalLanguageQueryResponse(
            answer=cached["response"],
            confidence=cached.get("confidence"),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    # Acquire lock and run inference
    lock_key = cache.multimodal_llm_lock_key(validated_url, prompt)
    result = await cache.with_lock(
        redis,
        lock_key,
        settings.lock_ttl_seconds,
        mm_llm_service.run_multimodal_llm(
            validated_url,
            prompt,
            payload.max_tokens,
            0.7,  # Default temperature for Q&A
        ),
    )
    
    # If lock not acquired, check cache again
    if result is None:
        logger.info(f"[{request_id}] Lock not acquired, checking cache again")
        if cached := await cache.get_cached_multimodal_llm(
            redis,
            validated_url,
            prompt,
            payload.max_tokens,
            0.7,
        ):
            return NaturalLanguageQueryResponse(
                answer=cached["response"],
                confidence=cached.get("confidence"),
                request_id=request_id,
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        logger.warning(f"[{request_id}] Lock unavailable and cache miss, returning 503")
        raise HTTPException(status_code=503, detail="Please retry")

    answer_text, confidence = result
    logger.info(
        f"[{request_id}] Natural language query completed: answer_length={len(answer_text)}, confidence={confidence}"
    )
    
    # Cache results
    ttl = await cache.set_cached_multimodal_llm(
        redis,
        validated_url,
        prompt,
        payload.max_tokens,
        0.7,
        answer_text,
        confidence,
    )
    
    # Store idempotency result
    if idem_key:
        import json
        idem_value = json.dumps({"answer": answer_text, "confidence": confidence})
        await cache.set_idempotency(redis, idem_key, idem_value, ttl)
        logger.info(f"[{request_id}] Stored idempotency key for future replay")

    return NaturalLanguageQueryResponse(
        answer=answer_text,
        confidence=confidence,
        request_id=request_id,
        cache_hit=False,
        ttl_seconds=ttl,
    )


