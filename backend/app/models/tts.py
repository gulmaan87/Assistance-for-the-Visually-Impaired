from pydantic import BaseModel
from typing import Optional


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    locale: Optional[str] = None


class TTSResponse(BaseModel):
    audio_url: Optional[str] = None
    fallback_hint: Optional[str] = None
    request_id: str

