"""
Object Detection Service using YOLOv8.

This service detects objects in images using the YOLOv8 model from Ultralytics.
It runs inference asynchronously with proper timeout handling and error management.
"""
from typing import List, Optional
import logging
import asyncio
import httpx
from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy model loading - will be initialized on first use
_yolo_model = None


def _get_yolo_model():
    """Lazy load YOLOv8 model on first use (singleton pattern)"""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Use YOLOv8n (nano) for faster inference, can upgrade to YOLOv8s/m/l/x for better accuracy
            logger.info("Loading YOLOv8 model...")
            _yolo_model = YOLO("yolov8n.pt")  # Downloads on first run if not present
            logger.info("YOLOv8 model loaded successfully")
        except ImportError:
            logger.error("ultralytics not installed. Install with: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise
    return _yolo_model


async def _download_image(image_url: str) -> bytes:
    """Download image from URL"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        return response.content


async def run_object_detection(
    image_url: str, confidence_threshold: float = 0.25
) -> tuple[List[dict], int]:
    """
    Run object detection on an image using YOLOv8.

    Args:
        image_url: URL of the image to process
        confidence_threshold: Minimum confidence score (0-1) for detections

    Returns:
        Tuple of (list of detected objects, total count)
        Each object is a dict with: class_name, confidence, bbox (x_min, y_min, x_max, y_max)

    Raises:
        TimeoutError: If inference exceeds timeout
        ValueError: If image cannot be processed
    """
    logger.info("Running object detection on %s with confidence threshold %s", image_url, confidence_threshold)

    async def _inference():
        # Download image
        image_data = await _download_image(image_url)
        
        # Load image with PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Run YOLOv8 inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        model = _get_yolo_model()
        
        # Run model inference in executor to avoid blocking event loop
        def _run_inference():
            results = model(image, conf=confidence_threshold, verbose=False)
            return results[0]  # Get first (and only) result
        
        result = await loop.run_in_executor(None, _run_inference)
        
        # Extract detections
        detections = []
        if result.boxes is not None:
            boxes = result.boxes
            for i in range(len(boxes)):
                # Get class name, confidence, and bounding box
                class_id = int(boxes.cls[i])
                class_name = model.names[class_id]
                confidence = float(boxes.conf[i])
                
                # Get normalized bbox coordinates (xyxy format)
                bbox = boxes.xyxy[i].cpu().numpy()
                x_min, y_min, x_max, y_max = bbox[0], bbox[1], bbox[2], bbox[3]
                
                # Normalize coordinates to 0-1 range (YOLOv8 returns pixel coordinates)
                width, height = image.size
                x_min_norm = x_min / width
                y_min_norm = y_min / height
                x_max_norm = x_max / width
                y_max_norm = y_max / height
                
                detections.append({
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": {
                        "x_min": float(x_min_norm),
                        "y_min": float(y_min_norm),
                        "x_max": float(x_max_norm),
                        "y_max": float(y_max_norm),
                    }
                })
        
        return detections, len(detections)

    try:
        return await asyncio.wait_for(
            _inference(), timeout=settings.object_detection_timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        logger.error("Object detection timed out for %s", image_url)
        raise TimeoutError("Object detection timeout") from exc
    except Exception as e:
        logger.error(f"Object detection failed for {image_url}: {e}", exc_info=True)
        raise ValueError(f"Object detection failed: {str(e)}") from e


