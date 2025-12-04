"""Circuit breaker pattern for external service calls."""
from enum import Enum
from typing import Callable, Optional
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.last_failure_time:
                    time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                    if time_since_failure >= self.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                        logger.info("Circuit breaker entering HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker is OPEN. Service unavailable.")
            
            # Try to execute function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - reset failure count
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker recovered. Entering CLOSED state.")
                elif self.state == CircuitState.CLOSED:
                    self.failure_count = 0
                
                return result
                
            except self.expected_exception as e:
                # Failure - increment failure count
                self.failure_count += 1
                self.last_failure_time = datetime.utcnow()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
                
                raise e


# Global circuit breakers for different services
patient_service_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

database_circuit_breaker = CircuitBreaker(
    failure_threshold=10,
    recovery_timeout=30,
    expected_exception=Exception
)

