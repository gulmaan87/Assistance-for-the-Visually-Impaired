"""
Async job processing endpoints.
Allows clients to submit long-running ML tasks and poll for results.
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.models.async_job import (
    AsyncJobRequest,
    AsyncJobResponse,
    JobStatus,
    JobStatusResponse,
    JobType,
)
from app.core.security import get_current_subject
from app.api.deps import redis_dep
from app.services import async_job as job_service

router = APIRouter()
logger = logging.getLogger(__name__)


# Estimated durations for different job types (in seconds)
JOB_ESTIMATED_DURATIONS = {
    JobType.OCR: 10,
    JobType.OBJECT_DETECTION: 15,
    JobType.SCENE_CAPTION: 20,
    JobType.MULTIMODAL_LLM: 30,
}


@router.post("", response_model=AsyncJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_async_job(
    payload: AsyncJobRequest,
    request: Request,
    subject: str = Depends(get_current_subject),
    redis=Depends(redis_dep),
):
    """
    Create a new async job for ML processing.
    Returns job ID and initial status immediately.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Creating async job: type={payload.job_type}, "
        f"image_url={payload.image_url}, subject={subject}"
    )
    
    # Validate job type
    if payload.job_type not in JOB_ESTIMATED_DURATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported job type: {payload.job_type}",
        )
    
    # Get estimated duration
    estimated_duration = JOB_ESTIMATED_DURATIONS[payload.job_type]
    
    # Create job
    job_id = await job_service.create_job(
        redis=redis,
        job_type=payload.job_type,
        image_url=payload.image_url,
        parameters=payload.parameters,
        estimated_duration_seconds=estimated_duration,
    )
    
    # Start background processing
    asyncio.create_task(
        job_service.process_job_background(
            redis=redis,
            job_id=job_id,
            job_type=payload.job_type,
            image_url=payload.image_url,
            parameters=payload.parameters,
        )
    )
    
    logger.info(f"[{request_id}] Created async job: job_id={job_id}")
    
    return AsyncJobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=await _get_job_created_at(redis, job_id),
        estimated_completion_seconds=estimated_duration,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status_endpoint(
    job_id: str,
    request: Request,
    subject: str = Depends(get_current_subject),
    redis=Depends(redis_dep),
):
    """
    Get the current status of an async job.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"[{request_id}] Checking job status: job_id={job_id}, subject={subject}")
    
    job_data = await job_service.get_job_status(redis, job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found or expired",
        )
    
    return JobStatusResponse(
        job_id=job_data["job_id"],
        status=JobStatus(job_data["status"]),
        created_at=job_data["created_at"],
        completed_at=job_data.get("completed_at"),
        result=job_data.get("result"),
        error=job_data.get("error"),
        progress_percent=job_data.get("progress_percent"),
    )


async def _get_job_created_at(redis, job_id: str) -> str:
    """Helper to get job creation timestamp."""
    job_data = await job_service.get_job_status(redis, job_id)
    return job_data["created_at"] if job_data else ""

