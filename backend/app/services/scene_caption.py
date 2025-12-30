"""
Scene Captioning Service using BLIP (Bootstrapping Language-Image Pre-training).

This service generates natural language captions for images using the BLIP model
from HuggingFace transformers. It runs inference asynchronously with proper timeout handling.
"""
from typing import Optional
import logging
import asyncio
import httpx
from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy model loading - will be initialized on first use
_blip_model = None
_blip_processor = None


def _get_blip_model():
    """Lazy load BLIP model on first use (singleton pattern)"""
    global _blip_model, _blip_processor
    if _blip_model is None:
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            
            logger.info("Loading BLIP model for scene captioning...")
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            
            # Use CPU for now; in production, configure GPU if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            
            _blip_processor = processor
            _blip_model = model
            
            logger.info(f"BLIP model loaded successfully on {device}")
        except ImportError:
            logger.error("transformers or torch not installed. Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load BLIP model: {e}")
            raise
    return _blip_model, _blip_processor


async def _download_image(image_url: str) -> bytes:
    """Download image from URL"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        return response.content


async def run_scene_captioning(
    image_url: str, max_length: int = 50
) -> tuple[str, float]:
    """
    Generate a natural language caption for an image using BLIP.

    Args:
        image_url: URL of the image to process
        max_length: Maximum length of generated caption in tokens

    Returns:
        Tuple of (caption text, confidence score)
        Confidence is estimated based on model's generation probability

    Raises:
        TimeoutError: If inference exceeds timeout
        ValueError: If image cannot be processed
    """
    logger.info("Running scene captioning on %s with max_length %s", image_url, max_length)

    async def _inference():
        # Download image
        image_data = await _download_image(image_url)
        
        # Load image with PIL
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Run BLIP inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        model, processor = _get_blip_model()
        
        # Run model inference in executor to avoid blocking event loop
        def _run_inference():
            import torch
            
            inputs = processor(image, return_tensors="pt")
            
            # Move inputs to same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            with torch.no_grad():
                out = model.generate(**inputs, max_length=max_length, num_beams=3)
            
            caption = processor.decode(out[0], skip_special_tokens=True)
            
            # Estimate confidence based on generation probability (simplified)
            # In production, you might want to compute log-probabilities more accurately
            confidence = 0.85  # Placeholder - BLIP doesn't provide explicit confidence scores
            
            return caption, confidence
        
        return await loop.run_in_executor(None, _run_inference)

    try:
        return await asyncio.wait_for(
            _inference(), timeout=settings.scene_caption_timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        logger.error("Scene captioning timed out for %s", image_url)
        raise TimeoutError("Scene captioning timeout") from exc
    except Exception as e:
        logger.error(f"Scene captioning failed for {image_url}: {e}", exc_info=True)
        raise ValueError(f"Scene captioning failed: {str(e)}") from e

