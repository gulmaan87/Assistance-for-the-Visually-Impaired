from pydantic import BaseModel, HttpUrl
from typing import Optional


class OCRRequest(BaseModel):
    image_url: HttpUrl
    locale: Optional[str] = None
    idempotency_key: Optional[str] = None


class OCRResponse(BaseModel):
    text: str
    confidence: float
    request_id: str
    cache_hit: bool = False
    ttl_seconds: int

