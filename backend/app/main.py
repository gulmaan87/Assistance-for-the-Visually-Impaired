"""
FastAPI application entrypoint.
Sets up request ID middleware, JWT stub authentication, Redis dependency wiring,
and routes for Week 1 (OCR + TTS skeleton) and Week 2 (object detection, scene captioning, multimodal LLM).
"""
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

from app.api.v1 import ocr, tts, upload, object_detection, scene_caption, multimodal_llm, async_job
from app.core.config import settings
from app.core.logging import configure_logging


def _request_id_middleware():
    async def dispatch(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    return dispatch


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Accessibility Assistant API",
        version="0.1.0",
        root_path=settings.api_root_path,
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=_request_id_middleware())

    app.include_router(ocr.router, prefix="/v1/ocr", tags=["ocr"])
    app.include_router(tts.router, prefix="/v1/tts", tags=["tts"])
    app.include_router(upload.router, prefix="/v1/upload-url", tags=["upload"])
    
    # Week 2 endpoints
    app.include_router(
        object_detection.router, prefix="/v1/object-detection", tags=["object-detection"]
    )
    app.include_router(
        scene_caption.router, prefix="/v1/scene-caption", tags=["scene-caption"]
    )
    app.include_router(
        multimodal_llm.router, prefix="/v1/multimodal-llm", tags=["multimodal-llm"]
    )
    
    # Week 3: Async job processing
    app.include_router(
        async_job.router, prefix="/v1/async-jobs", tags=["async-jobs"]
    )
    
    return app


app = create_app()
