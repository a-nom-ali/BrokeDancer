"""
Resilience Infrastructure

Provides retry logic, circuit breakers, and error handling patterns.

Features:
- Exponential backoff retries
- Circuit breaker pattern
- Timeout handling
- Error classification
- Failure tracking

Usage:
    # Retry decorator
    from src.infrastructure.resilience import with_retry

    @with_retry(max_attempts=3, retry_on=(ConnectionError, TimeoutError))
    async def fetch_price(symbol: str):
        return await exchange.get_price(symbol)

    # Circuit breaker
    from src.infrastructure.resilience import CircuitBreaker

    breaker = CircuitBreaker("exchange_api", failure_threshold=5)

    async def call_api():
        return await breaker.call(exchange.get_price, "BTC-USDT")

    # Timeout wrapper
    from src.infrastructure.resilience import with_timeout

    @with_timeout(seconds=5)
    async def slow_operation():
        # Will raise TimeoutError if takes > 5 seconds
        pass
"""

from .retry import (
    with_retry,
    RetryConfig,
    RetryExhausted,
    with_retry_config,
    retry_async
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState
)
from .timeout import (
    with_timeout,
    TimeoutError,
    with_timeout_async,
    TimeoutContext,
    wait_for_any,
    wait_for_all
)

__all__ = [
    # Retry
    "with_retry",
    "RetryConfig",
    "RetryExhausted",
    "with_retry_config",
    "retry_async",

    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitBreakerState",

    # Timeout
    "with_timeout",
    "TimeoutError",
    "with_timeout_async",
    "TimeoutContext",
    "wait_for_any",
    "wait_for_all",
]
