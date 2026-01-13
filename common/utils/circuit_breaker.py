"""
Circuit Breaker Pattern Implementation.

Simple circuit breaker without external dependencies for preventing cascading
failures in distributed systems.

States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is broken, requests fail fast without calling service
    - HALF_OPEN: Testing if service recovered, allow limited requests

Inspired by Martin Fowler's Circuit Breaker pattern:
https://martinfowler.com/bliki/CircuitBreaker.html
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from threading import Lock
from typing import TYPE_CHECKING, Type, Any, Callable, Dict, Optional

from common.logging.logger_config import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker is OPEN for {service_name}")


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault tolerance.

    Prevents cascading failures by failing fast when a service is unavailable.
    Automatically recovers by testing the service after a timeout period.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        :param name: Identifier for this circuit breaker
        :param failure_threshold: Number of failures before opening circuit
        :param recovery_timeout: Seconds before attempting recovery (HALF_OPEN)
        :param expected_exception: Exception type that counts as failure
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED
        self._lock = Lock()
        self._success_count = 0
        self._total_calls = 0

        logger.info(
            "circuit_breaker_initialized",
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """
        Get current circuit state.

        :return: Current state (CLOSED, OPEN, or HALF_OPEN)
        """
        with self._lock:
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    message="Attempting recovery",
                )
            return self._state

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.

        :return: True if should try HALF_OPEN state
        """
        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _record_success(self) -> None:
        """Record successful call and reset failure count."""
        with self._lock:
            self._failure_count = 0
            self._success_count += 1
            self._last_failure_time = None

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(
                    "circuit_breaker_closed",
                    name=self.name,
                    message="Service recovered",
                )

    def _record_failure(self) -> None:
        """Record failed call and potentially open circuit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "circuit_breaker_opened",
                        name=self.name,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold,
                    )

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute async function with circuit breaker protection.

        :param func: Async function to call
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        :return: Function result
        :raises CircuitBreakerOpenError: If circuit is OPEN
        """
        self._total_calls += 1
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(self.name)

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception:
            self._record_failure()
            raise

    def call_sync(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute sync function with circuit breaker protection.

        :param func: Sync function to call
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        :return: Function result
        :raises CircuitBreakerOpenError: If circuit is OPEN
        """
        self._total_calls += 1
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(self.name)

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception:
            self._record_failure()
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics.

        :return: Dictionary with state, counts, and metrics
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_calls": self._total_calls,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "last_failure_time": (
                    datetime.fromtimestamp(self._last_failure_time).isoformat()
                    if self._last_failure_time
                    else None
                ),
            }

    def reset(self) -> None:
        """
        Manually reset circuit breaker to CLOSED state.

        Should be called by operations staff when issue is resolved.
        """
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = None
            self._state = CircuitState.CLOSED
            logger.info("circuit_breaker_reset", name=self.name)


_circuit_breakers: Dict[str, CircuitBreaker] = {}
_breaker_lock = Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.

    :param name: Circuit breaker identifier
    :param failure_threshold: Failures before opening
    :param recovery_timeout: Seconds before retry
    :param expected_exception: Exception type to catch
    :return: CircuitBreaker instance
    """
    with _breaker_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
            )
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """
    Get all registered circuit breakers.

    :return: Dictionary of circuit breaker instances
    """
    with _breaker_lock:
        return _circuit_breakers.copy()


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception,
) -> Callable:
    """
    Decorator to wrap function with circuit breaker.

    :param name: Circuit breaker identifier
    :param failure_threshold: Failures before opening
    :param recovery_timeout: Seconds before retry
    :param expected_exception: Exception type to catch
    :return: Decorated function
    """
    breaker = get_circuit_breaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.call_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call_sync(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
