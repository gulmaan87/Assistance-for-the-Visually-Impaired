from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import uuid4
from app.core.security import get_current_subject
from app.core.config import settings

router = APIRouter()

class UploadUrlRequest(BaseModel):
    content_type: str = "image/jpeg"
    suffix: str = "jpg"

class UploadUrlResponse(BaseModel):
    upload_url: str
    image_url: str
    expiration: int  # Expiry seconds

@router.post("", response_model=UploadUrlResponse)
async def get_upload_url(
    params: UploadUrlRequest,
    subject: str = Depends(get_current_subject),
):
    # For Week 1, mock presigned URL with a predictable S3 pattern
    if not settings.storage_base_url or not settings.storage_bucket:
        raise HTTPException(
            status_code=500,
            detail="Storage not configured"
        )

    object_id = f"capture/{subject}/{uuid4()}.{params.suffix}"
    base_url = str(settings.storage_base_url).rstrip("/")
    bucket = settings.storage_bucket
    # Compose URLs; in prod, you'd generate real signatures
    image_url = f"{base_url}/{bucket}/{object_id}"
    upload_url = image_url  # In real impl., signed PUT URL
    expiration = 300  # 5 min expiry hint

    return UploadUrlResponse(
        upload_url=upload_url,
        image_url=image_url,
        expiration=expiration,
    )

