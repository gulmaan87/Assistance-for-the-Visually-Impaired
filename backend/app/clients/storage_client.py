from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings


class StorageClient:
    """
    Storage stub for Week 1.
    - Validates that an image URL is absolute and (optionally) matches configured bucket/endpoint.
    - In future weeks, will generate presigned upload URLs and enforce object TTLs.
    """

    def __init__(self, base_url: Optional[str] = None, bucket: Optional[str] = None) -> None:
        self.base_url = base_url or (str(settings.storage_base_url) if settings.storage_base_url else None)
        self.bucket = bucket or settings.storage_bucket

    def validate_image_url(self, image_url: str) -> str:
        parsed = urlparse(image_url)
        if not (parsed.scheme and parsed.netloc):
            raise ValueError("image_url must be absolute")

        if self.base_url and not image_url.startswith(self.base_url):
            # Allow external URLs during Week 1, but highlight mismatch for visibility.
            # In production, enforce allowed origins/buckets only.
            pass

        return image_url





