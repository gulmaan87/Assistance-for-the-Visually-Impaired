"""
Multimodal LLM Service for image understanding and natural language queries.

This service uses a vision-language model (e.g., BLIP-2, LLaVA, or Qwen-VL) to answer
questions about images and perform general image understanding tasks.
For Week 2, we implement a simplified version using BLIP-2 or a similar model.
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
_multimodal_model = None
_multimodal_processor = None


def _get_multimodal_model():
    """
    Lazy load multimodal LLM on first use (singleton pattern).
    
    Uses BLIP-2 for Week 2 as it's a good balance of capability and resource usage.
    In production, consider Qwen-VL, LLaVA, or GPT-4V for better performance.
    """
    global _multimodal_model, _multimodal_processor
    if _multimodal_model is None:
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            import torch
            
            logger.info("Loading BLIP-2 model for multimodal understanding...")
            processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            # Use GPU if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            
            _multimodal_processor = processor
            _multimodal_model = model
            
            logger.info(f"BLIP-2 model loaded successfully on {device}")
        except ImportError:
            logger.error("transformers or torch not installed. Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load multimodal model: {e}")
            # Fallback to simpler approach if BLIP-2 fails
            logger.warning("Falling back to basic BLIP model")
            try:
                from transformers import BlipProcessor, BlipForQuestionAnswering
                processor = BlipProcessor.from_pretrained("Salesforce/blip-vqa-capfilt-large")
                model = BlipForQuestionAnswering.from_pretrained("Salesforce/blip-vqa-capfilt-large")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                model.eval()
                _multimodal_processor = processor
                _multimodal_model = model
                logger.info(f"Fallback BLIP VQA model loaded on {device}")
            except Exception as fallback_error:
                logger.error(f"Fallback model also failed: {fallback_error}")
                raise
    return _multimodal_model, _multimodal_processor


async def _download_image(image_url: str) -> bytes:
    """Download image from URL"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        return response.content


async def run_multimodal_llm(
    image_url: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> tuple[str, Optional[float]]:
    """
    Generate a response to a prompt about an image using a multimodal LLM.

    Args:
        image_url: URL of the image to process
        prompt: Text prompt/question about the image
        max_tokens: Maximum number of tokens in response
        temperature: Sampling temperature (0-1, lower = more deterministic)

    Returns:
        Tuple of (response text, optional confidence score)

    Raises:
        TimeoutError: If inference exceeds timeout
        ValueError: If image or prompt cannot be processed
    """
    logger.info(
        "Running multimodal LLM on %s with prompt: %s (max_tokens=%s, temp=%s)",
        image_url, prompt[:50], max_tokens, temperature
    )

    async def _inference():
        # Download image
        image_data = await _download_image(image_url)
        
        # Load image with PIL
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Run multimodal inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        model, processor = _get_multimodal_model()
        
        # Run model inference in executor to avoid blocking event loop
        def _run_inference():
            import torch
            
            # Prepare inputs
            if hasattr(processor, "generate"):  # BLIP-2 style
                inputs = processor(image, prompt, return_tensors="pt")
            else:  # BLIP VQA style
                inputs = processor(image, prompt, return_tensors="pt")
            
            # Move inputs to same device as model
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
            
            with torch.no_grad():
                if hasattr(model, "generate"):  # Generation model
                    out = model.generate(
                        **inputs,
                        max_length=max_tokens,
                        temperature=temperature,
                        do_sample=temperature > 0,
                    )
                    response = processor.decode(out[0], skip_special_tokens=True)
                    # Remove the prompt from the response if it was included
                    if response.startswith(prompt):
                        response = response[len(prompt):].strip()
                else:  # VQA model
                    out = model.generate(**inputs, max_length=max_tokens)
                    response = processor.decode(out[0], skip_special_tokens=True)
            
            # Estimate confidence (placeholder - actual confidence calculation would require log-probs)
            confidence = 0.80
            
            return response, confidence
        
        return await loop.run_in_executor(None, _run_inference)

    try:
        return await asyncio.wait_for(
            _inference(), timeout=settings.multimodal_llm_timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        logger.error("Multimodal LLM timed out for %s", image_url)
        raise TimeoutError("Multimodal LLM timeout") from exc
    except Exception as e:
        logger.error(f"Multimodal LLM failed for {image_url}: {e}", exc_info=True)
        raise ValueError(f"Multimodal LLM failed: {str(e)}") from e


