"""
Retry Utilities using Tenacity.

This module provides retry decorators for handling transient failures.
"""

import asyncio
from functools import wraps
from typing import TYPE_CHECKING, Optional, Any, Callable

from tenacity import (
    retry as tenacity_retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.logging.logger_config import get_logger
from common.utils.circuit_breaker import (
    CircuitBreakerOpenError,
    with_circuit_breaker,
)


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
    max_attempts: int = 3,
    exceptions: tuple = (Exception,),
    circuit_breaker_name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> Callable:
    """
    Retry decorator for external API calls with optional circuit breaker.

    :param max_attempts: Maximum number of retry attempts
    :param exceptions: Tuple of exception types to retry on
    :param circuit_breaker_name: Optional circuit breaker name for protection
    :param failure_threshold: Circuit breaker failure threshold
    :param recovery_timeout: Circuit breaker recovery timeout in seconds
    :return: Decorator function
    """
    base_decorator = tenacity_retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            "retrying_api_call",
            attempt=retry_state.attempt_number,
            max_attempts=max_attempts,
        ),
    )

    if circuit_breaker_name:

        circuit_decorator = with_circuit_breaker(
            name=circuit_breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=exceptions[0] if exceptions else Exception,
        )

        def combined_decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    circuit_protected = circuit_decorator(func)
                    retry_protected = base_decorator(circuit_protected)
                    return await retry_protected(*args, **kwargs)
                except CircuitBreakerOpenError:
                    logger.error(
                        "circuit_breaker_open",
                        circuit=circuit_breaker_name,
                        message="Service unavailable - circuit open",
                    )
                    raise exceptions[0](f"Service unavailable: {circuit_breaker_name}")

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    circuit_protected = circuit_decorator(func)
                    retry_protected = base_decorator(circuit_protected)
                    return retry_protected(*args, **kwargs)
                except CircuitBreakerOpenError:
                    logger.error(
                        "circuit_breaker_open",
                        circuit=circuit_breaker_name,
                        message="Service unavailable - circuit open",
                    )
                    raise exceptions[0](f"Service unavailable: {circuit_breaker_name}")

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return combined_decorator
    else:
        return base_decorator


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

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
