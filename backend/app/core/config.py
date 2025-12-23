from pydantic import BaseSettings, AnyUrl
from functools import lru_cache


class Settings(BaseSettings):
    api_root_path: str = ""
    redis_url: AnyUrl = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"  # placeholder; replace via env
    jwt_algorithm: str = "HS256"
    cache_ttl_ocr_seconds: int = 1800  # 30 minutes
    lock_ttl_seconds: int = 30
    rate_limit_window_seconds: int = 60
    rate_limit_requests: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

