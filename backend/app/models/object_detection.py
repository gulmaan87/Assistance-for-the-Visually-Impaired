from pydantic import BaseModel, HttpUrl
from typing import Optional, List


class BoundingBox(BaseModel):
    """Bounding box coordinates (normalized 0-1)"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectedObject(BaseModel):
    """Detected object with class, confidence, and location"""
    class_name: str
    confidence: float
    bbox: BoundingBox


class ObjectDetectionRequest(BaseModel):
    image_url: HttpUrl
    confidence_threshold: Optional[float] = 0.25  # YOLOv8 default
    idempotency_key: Optional[str] = None


class ObjectDetectionResponse(BaseModel):
    objects: List[DetectedObject]
    total_objects: int
    request_id: str
    cache_hit: bool = False
    ttl_seconds: int

