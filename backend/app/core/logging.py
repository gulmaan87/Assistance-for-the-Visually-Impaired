import logging
import sys
import time
from functools import wraps
from typing import Callable, Any


def configure_logging() -> None:
    """Configure structured logging with request IDs and metrics."""
    if logging.getLogger().handlers:
        return
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def log_edge_cloud_metrics(
    source: str,
    duration_ms: float,
    cache_hit: bool = False,
    fallback_used: bool = False,
) -> None:
    """
    Log metrics for edge-cloud intelligence decisions.
    
    Args:
        source: 'cloud' or 'local'
        duration_ms: Processing duration in milliseconds
        cache_hit: Whether result came from cache
        fallback_used: Whether fallback was triggered
    """
    logger = logging.getLogger("edge_cloud_metrics")
    logger.info(
        f"edge_cloud_decision source={source} duration_ms={duration_ms:.2f} "
        f"cache_hit={cache_hit} fallback_used={fallback_used}"
    )


def log_async_job_metrics(
    job_type: str,
    status: str,
    duration_ms: float,
    success: bool,
) -> None:
    """
    Log metrics for async job processing.
    
    Args:
        job_type: Type of job (ocr, object_detection, etc.)
        status: Final job status
        duration_ms: Total processing duration in milliseconds
        success: Whether job completed successfully
    """
    logger = logging.getLogger("async_job_metrics")
    logger.info(
        f"async_job job_type={job_type} status={status} "
        f"duration_ms={duration_ms:.2f} success={success}"
    )


def timed_log(func: Callable) -> Callable:
    """
    Decorator to log function execution time.
    Useful for monitoring ML inference performance.
    """
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            logger = logging.getLogger(func.__module__)
            logger.debug(f"{func.__name__} completed in {duration_ms:.2f}ms")
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} failed after {duration_ms:.2f}ms: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            logger = logging.getLogger(func.__module__)
            logger.debug(f"{func.__name__} completed in {duration_ms:.2f}ms")
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} failed after {duration_ms:.2f}ms: {e}")
            raise
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

