"""
Unit tests for Circuit Breaker implementation.

Tests state transitions, failure thresholds, recovery timeout, and half-open probing.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker,
    with_circuit_breaker,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    def test_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        breaker = CircuitBreaker(
            name="test-breaker",
            failure_threshold=3,
            recovery_timeout=10.0,
        )

        assert breaker.name == "test-breaker"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 10.0
        assert breaker._failure_count == 0

    def test_successful_call_sync(self):
        """Test successful synchronous call keeps circuit CLOSED."""
        breaker = CircuitBreaker(name="test-sync", failure_threshold=3)

        def success_func():
            return "success"

        result = breaker.call_sync(success_func)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 1

    @pytest.mark.asyncio
    async def test_successful_call_async(self):
        """Test successful async call keeps circuit CLOSED."""
        breaker = CircuitBreaker(name="test-async", failure_threshold=3)

        async def success_func():
            return "async success"

        result = await breaker.call_async(success_func)

        assert result == "async success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 1

    def test_failure_increments_count(self):
        """Test failures increment failure count."""
        breaker = CircuitBreaker(name="test-failures", failure_threshold=3)

        def failing_func():
            raise Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            breaker.call_sync(failing_func)

        assert breaker._failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker(name="test-open", failure_threshold=3)

        def failing_func():
            raise Exception("Test error")

        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker._failure_count == 3

    def test_open_circuit_fails_fast(self):
        """Test OPEN circuit rejects calls immediately."""
        breaker = CircuitBreaker(name="test-fast-fail", failure_threshold=2)

        def failing_func():
            raise Exception("Test error")

        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenError):
            breaker.call_sync(lambda: "should not execute")

    def test_half_open_state_after_timeout(self):
        """Test circuit moves to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(
            name="test-half-open",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        def failing_func():
            raise Exception("Test error")

        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        time.sleep(0.15)

        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        """Test successful call in HALF_OPEN state closes circuit."""
        breaker = CircuitBreaker(
            name="test-recovery",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        def failing_func():
            raise Exception("Test error")

        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        result = breaker.call_sync(lambda: "recovered")

        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN state reopens circuit."""
        breaker = CircuitBreaker(
            name="test-reopen",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        def failing_func():
            raise Exception("Test error")

        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        with pytest.raises(Exception):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker._failure_count == 3

    def test_manual_reset(self):
        """Test manual reset closes circuit."""
        breaker = CircuitBreaker(name="test-reset", failure_threshold=2)

        def failing_func():
            raise Exception("Test error")

        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_get_stats(self):
        """Test statistics retrieval."""
        breaker = CircuitBreaker(name="test-stats", failure_threshold=5)

        breaker.call_sync(lambda: "success")
        breaker.call_sync(lambda: "success")

        stats = breaker.get_stats()

        assert stats["name"] == "test-stats"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 0
        assert stats["total_calls"] == 2
        assert stats["failure_threshold"] == 5

    @pytest.mark.asyncio
    async def test_async_circuit_breaker_decorator(self):
        """Test circuit breaker decorator with async function."""

        @with_circuit_breaker(
            name="decorator-test",
            failure_threshold=2,
            recovery_timeout=0.1,
        )
        async def api_call(should_fail: bool = False):
            if should_fail:
                raise Exception("API Error")
            return "success"

        result = await api_call(should_fail=False)
        assert result == "success"

        with pytest.raises(Exception, match="API Error"):
            await api_call(should_fail=True)

        with pytest.raises(Exception, match="API Error"):
            await api_call(should_fail=True)

        breaker = get_circuit_breaker("decorator-test")
        assert breaker.state == CircuitState.OPEN

    def test_sync_circuit_breaker_decorator(self):
        """Test circuit breaker decorator with sync function."""

        @with_circuit_breaker(
            name="sync-decorator-test",
            failure_threshold=3,
        )
        def database_query(should_fail: bool = False):
            if should_fail:
                raise Exception("DB Error")
            return "data"

        result = database_query(should_fail=False)
        assert result == "data"

        for _ in range(3):
            with pytest.raises(Exception, match="DB Error"):
                database_query(should_fail=True)

        breaker = get_circuit_breaker("sync-decorator-test")
        assert breaker.state == CircuitState.OPEN

    def test_custom_exception_type(self):
        """Test circuit breaker with custom exception type."""

        class CustomError(Exception):
            pass

        breaker = CircuitBreaker(
            name="custom-error-test",
            failure_threshold=2,
            expected_exception=CustomError,
        )

        def failing_func():
            raise CustomError("Custom error")

        with pytest.raises(CustomError):
            breaker.call_sync(failing_func)

        assert breaker._failure_count == 1

        def different_error():
            raise ValueError("Different error")

        with pytest.raises(ValueError):
            breaker.call_sync(different_error)

        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(self):
        """Test circuit breaker with concurrent async calls."""
        breaker = CircuitBreaker(name="concurrent-test", failure_threshold=5)

        call_count = 0

        async def api_call():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count

        results = await asyncio.gather(
            *[breaker.call_async(api_call) for _ in range(10)]
        )

        assert len(results) == 10
        assert breaker._success_count == 10
        assert breaker.state == CircuitState.CLOSED

    def test_get_circuit_breaker_singleton(self):
        """Test get_circuit_breaker returns same instance."""
        breaker1 = get_circuit_breaker("singleton-test", failure_threshold=3)
        breaker2 = get_circuit_breaker("singleton-test", failure_threshold=5)

        assert breaker1 is breaker2
        assert breaker1.failure_threshold == 3


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with retry logic."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker combined with retry decorator."""
        from common.utils.retry import retry_on_api_error

        call_count = 0

        @retry_on_api_error(
            max_attempts=3,
            exceptions=(Exception,),
            circuit_breaker_name="retry-integration",
            failure_threshold=2,
        )
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            raise Exception("Service unavailable")

        with pytest.raises(Exception):
            await flaky_service()

        assert call_count == 3

        breaker = get_circuit_breaker("retry-integration")
        assert breaker._failure_count >= 1
