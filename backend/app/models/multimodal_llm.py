from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any


class MultimodalLLMRequest(BaseModel):
    image_url: HttpUrl
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    idempotency_key: Optional[str] = None


class MultimodalLLMResponse(BaseModel):
    response: str
    confidence: Optional[float] = None
    request_id: str
    cache_hit: bool = False
    ttl_seconds: int


class NaturalLanguageQueryRequest(BaseModel):
    """Request for natural language queries about an image"""
    image_url: HttpUrl
    question: str
    max_tokens: Optional[int] = 256
    idempotency_key: Optional[str] = None


class NaturalLanguageQueryResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None
    request_id: str
    cache_hit: bool = False
    ttl_seconds: int


