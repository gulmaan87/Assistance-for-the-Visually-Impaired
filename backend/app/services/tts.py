from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def synthesize_tts(text: str, voice: Optional[str] = None, locale: Optional[str] = None) -> Optional[str]:
    """
    Placeholder TTS synthesis.
    Returns None to signal mobile should use local/offline TTS for Week 1.
    """
    logger.info("TTS placeholder text len=%s voice=%s locale=%s", len(text), voice, locale)
    return None

