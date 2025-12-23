"""
FastAPI application entrypoint.
Sets up request ID middleware, JWT stub authentication, Redis dependency wiring,
and routes for Week 1 scope (OCR + TTS skeleton).
"""
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

from app.api.v1 import ocr, tts
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
    return app


app = create_app()

