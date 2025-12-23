from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def run_ocr(image_url: str, locale: Optional[str] = None) -> tuple[str, float]:
    """
    Placeholder for OCR inference.
    In production, invoke PaddleOCR/Tesseract; ensure timeouts and resource isolation.
    """
    logger.info("Running OCR (placeholder) on %s locale=%s", image_url, locale)
    # Placeholder deterministic response.
    return "placeholder text", 0.42

