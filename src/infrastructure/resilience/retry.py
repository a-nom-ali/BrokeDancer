"""
Retry Logic

Provides exponential backoff retries for handling transient failures.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Tuple, Type, Any
from functools import wraps
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted"""

    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts
        min_wait_seconds: Minimum wait time between retries
        max_wait_seconds: Maximum wait time between retries
        multiplier: Exponential backoff multiplier
        retry_on: Tuple of exception types to retry on

    Example:
        config = RetryConfig(
            max_attempts=5,
            min_wait_seconds=1,
            max_wait_seconds=60,
            multiplier=2,
            retry_on=(ConnectionError, TimeoutError)
        )
    """
    max_attempts: int = 3
    min_wait_seconds: float = 1.0
    max_wait_seconds: float = 60.0
    multiplier: float = 2.0
    retry_on: Tuple[Type[Exception], ...] = (Exception,)

    def __post_init__(self):
        """Validate configuration"""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.min_wait_seconds < 0:
            raise ValueError("min_wait_seconds must be >= 0")
        if self.max_wait_seconds < self.min_wait_seconds:
            raise ValueError("max_wait_seconds must be >= min_wait_seconds")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")


def with_retry(
    max_attempts: int = 3,
    min_wait_seconds: float = 1.0,
    max_wait_seconds: float = 60.0,
    multiplier: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    raise_on_exhausted: bool = True
):
    """
    Decorator to add exponential backoff retries to async functions.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait_seconds: Minimum wait time between retries (default: 1.0s)
        max_wait_seconds: Maximum wait time between retries (default: 60.0s)
        multiplier: Exponential backoff multiplier (default: 2.0)
        retry_on: Tuple of exception types to retry on (default: all exceptions)
        raise_on_exhausted: Raise RetryExhausted instead of last exception (default: True)

    Returns:
        Decorated function with retry logic

    Usage:
        @with_retry(max_attempts=3, retry_on=(ConnectionError, TimeoutError))
        async def fetch_price(symbol: str):
            return await exchange.get_price(symbol)

        # With custom backoff
        @with_retry(
            max_attempts=5,
            min_wait_seconds=2,
            max_wait_seconds=120,
            multiplier=3
        )
        async def critical_operation():
            # Will retry with: 2s, 6s, 18s, 54s, 120s (capped)
            pass

    Retry Schedule Examples:
        Default (min=1s, max=60s, mult=2):
            Attempt 1: immediate
            Attempt 2: wait 1s
            Attempt 3: wait 2s
            Total time: ~3s

        Aggressive (min=2s, max=120s, mult=3):
            Attempt 1: immediate
            Attempt 2: wait 2s
            Attempt 3: wait 6s
            Attempt 4: wait 18s
            Attempt 5: wait 54s
            Total time: ~80s
    """

    def decorator(func: Callable) -> Callable:
        # Create tenacity retry decorator
        retry_decorator = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                min=min_wait_seconds,
                max=max_wait_seconds,
                multiplier=multiplier
            ),
            retry=retry_if_exception_type(retry_on),
            reraise=True
        )

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            try:
                # Apply tenacity retry
                retrying_func = retry_decorator(func)
                result = await retrying_func(*args, **kwargs)
                return result
            except Exception as e:
                # Check if this is an exception we should have retried
                if isinstance(e, retry_on):
                    # This is a retryable exception that exhausted retries
                    last_exception = e

                    # Log final failure
                    logger.error(
                        "retry_exhausted",
                        function=func.__name__,
                        max_attempts=max_attempts,
                        error=str(e),
                        error_type=type(e).__name__
                    )

                    if raise_on_exhausted:
                        raise RetryExhausted(max_attempts, last_exception) from e
                    else:
                        raise
                else:
                    # This is not a retryable exception, pass through
                    raise

        return wrapper

    return decorator


def with_retry_config(config: RetryConfig, raise_on_exhausted: bool = True):
    """
    Decorator that accepts a RetryConfig instance.

    This is useful when you want to share retry configuration across multiple functions.

    Args:
        config: RetryConfig instance
        raise_on_exhausted: Raise RetryExhausted instead of last exception

    Returns:
        Decorated function with retry logic

    Usage:
        # Define shared config
        api_retry_config = RetryConfig(
            max_attempts=5,
            min_wait_seconds=1,
            max_wait_seconds=30,
            retry_on=(ConnectionError, TimeoutError)
        )

        # Use across multiple functions
        @with_retry_config(api_retry_config)
        async def fetch_price(symbol: str):
            return await exchange.get_price(symbol)

        @with_retry_config(api_retry_config)
        async def place_order(order: Order):
            return await exchange.place_order(order)
    """
    return with_retry(
        max_attempts=config.max_attempts,
        min_wait_seconds=config.min_wait_seconds,
        max_wait_seconds=config.max_wait_seconds,
        multiplier=config.multiplier,
        retry_on=config.retry_on,
        raise_on_exhausted=raise_on_exhausted
    )


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    min_wait_seconds: float = 1.0,
    max_wait_seconds: float = 60.0,
    multiplier: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Retry an async function without using a decorator.

    This is useful when you can't use decorators or want to retry
    a function dynamically.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_attempts: Maximum retry attempts
        min_wait_seconds: Minimum wait between retries
        max_wait_seconds: Maximum wait between retries
        multiplier: Exponential backoff multiplier
        retry_on: Exception types to retry on
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)

    Raises:
        RetryExhausted: If all retry attempts fail

    Usage:
        # Retry a function dynamically
        result = await retry_async(
            exchange.get_price,
            "BTC-USDT",
            max_attempts=5,
            retry_on=(ConnectionError,)
        )

        # With keyword arguments
        result = await retry_async(
            exchange.place_order,
            order=my_order,
            timeout=30,
            max_attempts=3
        )
    """

    @with_retry(
        max_attempts=max_attempts,
        min_wait_seconds=min_wait_seconds,
        max_wait_seconds=max_wait_seconds,
        multiplier=multiplier,
        retry_on=retry_on
    )
    async def _retry_wrapper():
        return await func(*args, **kwargs)

    return await _retry_wrapper()


# Pre-configured retry decorators for common use cases

# Network operations (connection errors, timeouts)
with_network_retry = with_retry(
    max_attempts=3,
    min_wait_seconds=1,
    max_wait_seconds=10,
    retry_on=(ConnectionError, TimeoutError, OSError)
)

# API calls (rate limits, server errors)
with_api_retry = with_retry(
    max_attempts=5,
    min_wait_seconds=2,
    max_wait_seconds=60,
    multiplier=2,
    retry_on=(ConnectionError, TimeoutError)
)

# Database operations (connection errors)
with_db_retry = with_retry(
    max_attempts=3,
    min_wait_seconds=0.5,
    max_wait_seconds=5,
    retry_on=(ConnectionError,)
)

# Critical operations (many retries, long backoff)
with_critical_retry = with_retry(
    max_attempts=10,
    min_wait_seconds=5,
    max_wait_seconds=300,  # 5 minutes max
    multiplier=2
)
