"""Retry mechanism with exponential backoff."""
import asyncio
from typing import Callable, Optional, Type, Tuple
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry mechanism."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delay
            retryable_exceptions: Exceptions that should trigger retry
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
):
    """
    Execute function with retry and exponential backoff.
    
    Args:
        func: Function to execute
        *args: Function arguments
        config: Retry configuration
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retry attempts fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_attempts - 1:
                # Calculate delay with exponential backoff
                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                
                # Add jitter if enabled
                if config.jitter:
                    jitter_amount = delay * 0.1 * random.random()
                    delay += jitter_amount
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay:.2f}s. "
                    f"Error: {str(e)}"
                )
                
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {config.max_attempts} retry attempts failed")
                raise last_exception
    
    raise last_exception

