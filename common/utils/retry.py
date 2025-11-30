"""
Retry Utilities using Tenacity.

This module provides retry decorators for handling transient failures.
"""

from functools import wraps
from typing import Callable, Any
from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from common.logging.logger_config import get_logger


logger = get_logger(__name__)


def retry_on_db_error(max_attempts: int = 3) -> Callable:
    """
    Retry decorator for database operations.

    :param max_attempts: Maximum number of retry attempts
    :return: Decorator function
    """
    return tenacity_retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_database_operation",
            attempt=retry_state.attempt_number,
            max_attempts=max_attempts,
        ),
    )


def retry_on_api_error(
    max_attempts: int = 3, exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator for external API calls.

    :param max_attempts: Maximum number of retry attempts
    :param exceptions: Tuple of exception types to retry on
    :return: Decorator function
    """
    return tenacity_retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_api_call",
            attempt=retry_state.attempt_number,
            max_attempts=max_attempts,
        ),
    )


def retry_with_backoff(
    max_attempts: int = 3, min_wait: int = 1, max_wait: int = 10
) -> Callable:
    """
    Generic retry decorator with exponential backoff.

    :param max_attempts: Maximum number of retry attempts
    :param min_wait: Minimum wait time in seconds
    :param max_wait: Maximum wait time in seconds
    :return: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            before_sleep=lambda retry_state: logger.warning(
                "retrying_operation",
                function=func.__name__,
                attempt=retry_state.attempt_number,
                max_attempts=max_attempts,
            ),
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @wraps(func)
        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            before_sleep=lambda retry_state: logger.warning(
                "retrying_operation",
                function=func.__name__,
                attempt=retry_state.attempt_number,
                max_attempts=max_attempts,
            ),
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
