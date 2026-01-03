"""
Pydantic models for async job processing.
Jobs are used for long-running ML inference tasks that may exceed API timeout limits.
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of an async job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class JobType(str, Enum):
    """Type of async job."""
    OCR = "ocr"
    OBJECT_DETECTION = "object_detection"
    SCENE_CAPTION = "scene_caption"
    MULTIMODAL_LLM = "multimodal_llm"


class AsyncJobRequest(BaseModel):
    """Request to create an async job."""
    job_type: JobType = Field(..., description="Type of job to process")
    image_url: str = Field(..., description="URL of image to process")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Job-specific parameters (e.g., confidence_threshold, prompt)"
    )


class AsyncJobResponse(BaseModel):
    """Response containing job ID and status."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: str = Field(..., description="ISO timestamp of job creation")
    estimated_completion_seconds: Optional[int] = Field(
        None,
        description="Estimated time to completion (if processing)"
    )


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: str = Field(..., description="ISO timestamp of job creation")
    completed_at: Optional[str] = Field(
        None,
        description="ISO timestamp of job completion (if completed)"
    )
    result: Optional[dict[str, Any]] = Field(
        None,
        description="Job result (if completed successfully)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message (if failed)"
    )
    progress_percent: Optional[int] = Field(
        None,
        description="Progress percentage (0-100) if processing"
    )

