"""
Async job processing service with Redis-backed state tracking.
Handles job creation, status tracking, and result storage.
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from app.core.config import settings
from app.models.async_job import JobStatus, JobType


def job_key(job_id: str) -> str:
    """Generate Redis key for job state."""
    return f"job:{job_id}"


def job_status_key(job_id: str) -> str:
    """Generate Redis key for job status (for quick lookups)."""
    return f"job:status:{job_id}"


async def create_job(
    redis,
    job_type: JobType,
    image_url: str,
    parameters: dict[str, Any],
    estimated_duration_seconds: int = 30,
) -> str:
    """
    Create a new async job and store initial state in Redis.
    Returns the job ID.
    """
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Job state structure
    job_state = {
        "job_id": job_id,
        "job_type": job_type.value,
        "image_url": image_url,
        "parameters": json.dumps(parameters),
        "status": JobStatus.PENDING.value,
        "created_at": now,
        "estimated_completion_seconds": estimated_duration_seconds,
        "progress_percent": 0,
    }
    
    # Store job state (TTL: estimated duration + buffer)
    ttl = estimated_duration_seconds + 300  # 5 minute buffer
    key = job_key(job_id)
    await redis.hset(key, mapping=job_state)
    await redis.expire(key, ttl)
    
    # Also store status for quick lookup
    status_key = job_status_key(job_id)
    await redis.setex(status_key, ttl, JobStatus.PENDING.value)
    
    return job_id


async def get_job_status(redis, job_id: str) -> Optional[dict[str, Any]]:
    """
    Get current job status from Redis.
    Returns None if job doesn't exist or has expired.
    """
    key = job_key(job_id)
    data = await redis.hgetall(key)
    
    if not data:
        return None
    
    # Parse JSON parameters
    parameters = {}
    if data.get("parameters"):
        try:
            parameters = json.loads(data["parameters"])
        except json.JSONDecodeError:
            pass
    
    return {
        "job_id": data.get("job_id", job_id),
        "job_type": data.get("job_type"),
        "image_url": data.get("image_url"),
        "parameters": parameters,
        "status": data.get("status"),
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
        "result": json.loads(data["result"]) if data.get("result") else None,
        "error": data.get("error"),
        "progress_percent": int(data.get("progress_percent", 0)),
        "estimated_completion_seconds": int(data.get("estimated_completion_seconds", 30)),
    }


async def update_job_status(
    redis,
    job_id: str,
    status: JobStatus,
    progress_percent: Optional[int] = None,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    Update job status in Redis.
    """
    key = job_key(job_id)
    updates = {"status": status.value}
    
    if progress_percent is not None:
        updates["progress_percent"] = progress_percent
    
    if result is not None:
        updates["result"] = json.dumps(result)
        updates["completed_at"] = datetime.utcnow().isoformat()
    
    if error is not None:
        updates["error"] = error
        updates["completed_at"] = datetime.utcnow().isoformat()
    
    await redis.hset(key, mapping=updates)
    
    # Update status key
    status_key = job_status_key(job_id)
    await redis.setex(status_key, 3600, status.value)  # 1 hour TTL for completed jobs


async def process_job_background(
    redis,
    job_id: str,
    job_type: JobType,
    image_url: str,
    parameters: dict[str, Any],
) -> None:
    """
    Background task to process a job.
    This would typically call the appropriate ML service and update job status.
    """
    try:
        # Update status to processing
        await update_job_status(redis, job_id, JobStatus.PROCESSING, progress_percent=10)
        
        # Simulate processing with progress updates
        # In production, this would call actual ML services
        await asyncio.sleep(1)  # Simulate work
        await update_job_status(redis, job_id, JobStatus.PROCESSING, progress_percent=50)
        
        await asyncio.sleep(1)  # Simulate more work
        await update_job_status(redis, job_id, JobStatus.PROCESSING, progress_percent=90)
        
        # Simulate result (in production, this would be actual ML output)
        result = {
            "text": "Sample result from async processing",
            "confidence": 0.95,
            "job_type": job_type.value,
        }
        
        # Mark as completed
        await update_job_status(
            redis,
            job_id,
            JobStatus.COMPLETED,
            progress_percent=100,
            result=result,
        )
    except Exception as e:
        # Mark as failed
        await update_job_status(
            redis,
            job_id,
            JobStatus.FAILED,
            error=str(e),
        )

