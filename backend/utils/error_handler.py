"""
Centralized Error Handler Utility

Provides error recovery mechanisms including:
- Exponential backoff calculation
- Task failure logging
- Circuit breaker pattern
- Telegram FloodWait handling
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half_open"
                logger.info(f"Circuit breaker entering half-open state for {func.__name__}")
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info(f"Circuit breaker closed for {func.__name__}")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened for {func.__name__} after {self.failure_count} failures")
            
            raise e


def calculate_exponential_backoff(attempt: int, base_delay: int = 1, max_delay: int = 300) -> int:
    """
    Calculate exponential backoff delay.
    
    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
    
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay


async def handle_telegram_flood_wait(wait_seconds: int, operation_name: str = "operation"):
    """
    Handle Telegram FloodWaitError with logging and scheduling.
    
    Args:
        wait_seconds: Required wait time in seconds
        operation_name: Name of the operation for logging
    """
    logger.warning(
        f"Telegram FloodWait triggered for '{operation_name}'. "
        f"Required wait: {wait_seconds}s (~{wait_seconds/60:.1f} minutes)"
    )
    
    # Log to task log if database is available
    try:
        from backend.database import SessionLocal
        from backend.models import TaskLog
        
        db = SessionLocal()
        log_entry = TaskLog(
            task_name=f"telegram_{operation_name}",
            status="flood_wait",
            message=f"FloodWait: {wait_seconds}s required",
            retry_after=datetime.now() + timedelta(seconds=wait_seconds)
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log FloodWait to database: {e}")
    
    # Wait the required time
    await asyncio.sleep(wait_seconds)


def async_retry_with_backoff(max_retries: int = 3, base_delay: int = 1):
    """
    Decorator for async functions to retry with exponential backoff.
    
    Usage:
        @async_retry_with_backoff(max_retries=3)
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    
                    delay = calculate_exponential_backoff(attempt, base_delay)
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator


async def safe_background_task(task_name: str, task_func: Callable, *args, **kwargs):
    """
    Wrapper for background tasks with error handling and logging.
    
    Args:
        task_name: Name of the task for logging
        task_func: Async function to execute
        *args, **kwargs: Arguments to pass to task_func
    """
    try:
        logger.info(f"Starting background task: {task_name}")
        result = await task_func(*args, **kwargs)
        logger.info(f"Successfully completed background task: {task_name}")
        
        # Log success to database
        try:
            from backend.database import SessionLocal
            from backend.models import TaskLog
            
            db = SessionLocal()
            log_entry = TaskLog(
                task_name=task_name,
                status="success",
                message="Task completed successfully"
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as log_error:
            logger.warning(f"Failed to log task success: {log_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Background task '{task_name}' failed: {e}", exc_info=True)
        
        # Log failure to database
        try:
            from backend.database import SessionLocal
            from backend.models import TaskLog
            
            db = SessionLocal()
            log_entry = TaskLog(
                task_name=task_name,
                status="failed",
                message=f"Error: {str(e)[:500]}"
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as log_error:
            logger.warning(f"Failed to log task failure: {log_error}")
        
        # Don't re-raise to prevent task from stopping
        return None
