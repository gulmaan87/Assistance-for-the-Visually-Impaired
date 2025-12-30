"""
Object Detection API endpoint.

Handles object detection requests with caching, rate limiting, idempotency,
and distributed locking following the same patterns as OCR endpoint.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from app.models.object_detection import ObjectDetectionRequest, ObjectDetectionResponse, DetectedObject, BoundingBox
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.clients.storage_client import StorageClient
from app.services import cache, object_detection as obj_det_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ObjectDetectionResponse)
async def run_object_detection_endpoint(
    payload: ObjectDetectionRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    idem_key: str | None = Header(default=None, alias="idempotency-key"),
    redis=Depends(redis_dep),
):
    """
    Detect objects in an image using YOLOv8.
    
    Returns a list of detected objects with their classes, confidence scores,
    and bounding box coordinates.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Object detection request for image_url={payload.image_url}, "
        f"confidence_threshold={payload.confidence_threshold}, subject={subject}, "
        f"idempotency_key={idem_key}"
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
        # Parse prior result (stored as JSON string)
        import json
        prior_data = json.loads(prior)
        objects = [
            DetectedObject(
                class_name=obj["class_name"],
                confidence=obj["confidence"],
                bbox=BoundingBox(**obj["bbox"])
            )
            for obj in prior_data["objects"]
        ]
        return ObjectDetectionResponse(
            objects=objects,
            total_objects=prior_data["total_objects"],
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=settings.cache_ttl_object_detection_seconds,
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
    if cached := await cache.get_cached_object_detection(
        redis, validated_url, payload.confidence_threshold
    ):
        logger.info(f"[{request_id}] Cache hit for image_url={validated_url}")
        objects = [
            DetectedObject(
                class_name=obj["class_name"],
                confidence=obj["confidence"],
                bbox=BoundingBox(**obj["bbox"])
            )
            for obj in cached["objects"]
        ]
        return ObjectDetectionResponse(
            objects=objects,
            total_objects=len(objects),
            request_id=request_id,
            cache_hit=True,
            ttl_seconds=cached["ttl"],
        )

    # Acquire lock and run inference
    lock_key = cache.object_detection_lock_key(validated_url)
    result = await cache.with_lock(
        redis,
        lock_key,
        settings.lock_ttl_seconds,
        obj_det_service.run_object_detection(validated_url, payload.confidence_threshold),
    )
    
    # If lock not acquired, check cache again
    if result is None:
        logger.info(f"[{request_id}] Lock not acquired, checking cache again")
        if cached := await cache.get_cached_object_detection(
            redis, validated_url, payload.confidence_threshold
        ):
            objects = [
                DetectedObject(
                    class_name=obj["class_name"],
                    confidence=obj["confidence"],
                    bbox=BoundingBox(**obj["bbox"])
                )
                for obj in cached["objects"]
            ]
            return ObjectDetectionResponse(
                objects=objects,
                total_objects=len(objects),
                request_id=request_id,
                cache_hit=True,
                ttl_seconds=cached["ttl"],
            )
        logger.warning(f"[{request_id}] Lock unavailable and cache miss, returning 503")
        raise HTTPException(status_code=503, detail="Please retry")

    objects_list, total = result
    logger.info(
        f"[{request_id}] Object detection completed: detected {total} objects"
    )
    
    # Cache results
    ttl = await cache.set_cached_object_detection(
        redis, validated_url, payload.confidence_threshold, objects_list
    )
    
    # Store idempotency result
    if idem_key:
        import json
        idem_value = json.dumps({"objects": objects_list, "total_objects": total})
        await cache.set_idempotency(redis, idem_key, idem_value, ttl)
        logger.info(f"[{request_id}] Stored idempotency key for future replay")

    # Convert to response objects
    response_objects = [
        DetectedObject(
            class_name=obj["class_name"],
            confidence=obj["confidence"],
            bbox=BoundingBox(**obj["bbox"])
        )
        for obj in objects_list
    ]

    return ObjectDetectionResponse(
        objects=response_objects,
        total_objects=total,
        request_id=request_id,
        cache_hit=False,
        ttl_seconds=ttl,
    )

