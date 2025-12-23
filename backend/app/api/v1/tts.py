from fastapi import APIRouter, Depends
from app.models.tts import TTSRequest, TTSResponse
from app.core.security import get_current_subject
from app.services import tts

router = APIRouter()


@router.post("", response_model=TTSResponse)
async def tts_endpoint(
    payload: TTSRequest,
    subject: str = Depends(get_current_subject),
):
    audio_url = await tts.synthesize_tts(payload.text, payload.voice, payload.locale)
    return TTSResponse(
        audio_url=audio_url,
        fallback_hint="use_local_tts" if audio_url is None else None,
        request_id="tts-placeholder",
    )

