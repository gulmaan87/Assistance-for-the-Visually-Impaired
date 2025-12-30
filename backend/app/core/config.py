from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_root_path: str = ""
    redis_url: AnyUrl = "redis://localhost:6379/0"
    storage_base_url: AnyUrl | None = None  # S3-compatible endpoint (optional)
    storage_bucket: str | None = None
    ocr_timeout_seconds: float = 8.0
    jwt_secret: str = "change-me"  # placeholder; replace via env
    jwt_algorithm: str = "HS256"
    cache_ttl_ocr_seconds: int = 1800  # 30 minutes
    cache_ttl_object_detection_seconds: int = 1800  # 30 minutes
    cache_ttl_scene_caption_seconds: int = 1800  # 30 minutes
    cache_ttl_multimodal_llm_seconds: int = 3600  # 1 hour for LLM responses
    lock_ttl_seconds: int = 30
    rate_limit_window_seconds: int = 60
    rate_limit_requests: int = 30
    # Week 2: ML model timeouts
    object_detection_timeout_seconds: float = 10.0
    scene_caption_timeout_seconds: float = 15.0
    multimodal_llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

