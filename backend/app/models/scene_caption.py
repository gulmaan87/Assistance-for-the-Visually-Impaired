from pydantic import BaseModel, HttpUrl
from typing import Optional


class SceneCaptionRequest(BaseModel):
    image_url: HttpUrl
    max_length: Optional[int] = 50  # Maximum caption length
    idempotency_key: Optional[str] = None


class SceneCaptionResponse(BaseModel):
    caption: str
    confidence: float
    request_id: str
    cache_hit: bool = False
    ttl_seconds: int

