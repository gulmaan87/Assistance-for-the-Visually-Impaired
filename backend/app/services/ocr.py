from typing import Optional
import logging
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_ocr(image_url: str, locale: Optional[str] = None) -> tuple[str, float]:
    """
    Placeholder for OCR inference with timeout guard.
    In production, invoke PaddleOCR/Tesseract; ensure timeouts and resource isolation.
    """
    logger.info("Running OCR (placeholder) on %s locale=%s", image_url, locale)

    async def _inference():
        await asyncio.sleep(0.05)  # simulate small latency
        return "placeholder text", 0.42

    try:
        return await asyncio.wait_for(_inference(), timeout=settings.ocr_timeout_seconds)
    except asyncio.TimeoutError as exc:
        logger.error("OCR timed out for %s", image_url)
        raise TimeoutError("OCR timeout") from exc

