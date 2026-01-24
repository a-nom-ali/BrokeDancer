"""
Circuit Breaker Pattern

Prevents cascading failures by failing fast when a service is unhealthy.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Any
import asyncio
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open (failing fast)"""

    def __init__(self, name: str, failures: int, state: CircuitBreakerState):
        self.name = name
        self.failures = failures
        self.state = state
        super().__init__(
            f"Circuit breaker '{name}' is {state.value}. "
            f"Recent failures: {failures}"
        )


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in half-open before closing
        timeout_seconds: Seconds to wait before trying half-open
        window_seconds: Time window for counting failures

    Example:
        config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout_seconds=60,
            window_seconds=120
        )
    """
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    window_seconds: float = 120.0

    def __post_init__(self):
        """Validate configuration"""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.timeout_seconds < 0:
            raise ValueError("timeout_seconds must be >= 0")
        if self.window_seconds < 0:
            raise ValueError("window_seconds must be >= 0")


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests pass through

    State transitions:
    - CLOSED → OPEN: After failure_threshold failures in window
    - OPEN → HALF_OPEN: After timeout_seconds
    - HALF_OPEN → CLOSED: After success_threshold successes
    - HALF_OPEN → OPEN: On any failure

    Usage:
        # Create circuit breaker
        breaker = CircuitBreaker(
            "exchange_api",
            failure_threshold=5,
            timeout_seconds=60
        )

        # Use circuit breaker
        try:
            result = await breaker.call(exchange.get_price, "BTC-USDT")
        except CircuitBreakerOpen:
            # Service is down, use cached data
            result = get_cached_price("BTC-USDT")

        # Manual state control
        await breaker.force_open()  # Emergency stop
        await breaker.force_close()  # Force resume
        await breaker.reset()  # Clear all state
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 60.0,
        window_seconds: float = 120.0
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker identifier (for logging)
            failure_threshold: Failures before opening (default: 5)
            success_threshold: Successes in half-open before closing (default: 2)
            timeout_seconds: Seconds before trying half-open (default: 60)
            window_seconds: Time window for failure counting (default: 120)
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout_seconds=timeout_seconds,
            window_seconds=window_seconds
        )

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

        # Track failures in time window
        self._recent_failures: list[datetime] = []

        logger.info(
            "circuit_breaker_created",
            name=name,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds
        )

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)"""
        return self._state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self._state == CircuitBreakerState.HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of func(*args, **kwargs)

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from func

        Usage:
            result = await breaker.call(exchange.get_price, "BTC-USDT")
        """
        async with self._lock:
            # Check if we should transition to half-open
            await self._maybe_attempt_reset()

            # If open, fail fast
            if self._state == CircuitBreakerState.OPEN:
                logger.warning(
                    "circuit_breaker_open",
                    name=self.name,
                    failures=self._failure_count
                )
                raise CircuitBreakerOpen(self.name, self._failure_count, self._state)

        # Try the call
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                logger.info(
                    "circuit_breaker_success",
                    name=self.name,
                    successes=self._success_count,
                    threshold=self.config.success_threshold
                )

                # Close circuit if enough successes
                if self._success_count >= self.config.success_threshold:
                    await self._close()

    async def _on_failure(self, exception: Exception):
        """Handle failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            self._recent_failures.append(datetime.utcnow())

            # Clean old failures outside window
            cutoff = datetime.utcnow() - timedelta(seconds=self.config.window_seconds)
            self._recent_failures = [
                f for f in self._recent_failures if f > cutoff
            ]

            logger.warning(
                "circuit_breaker_failure",
                name=self.name,
                failures=self._failure_count,
                recent_failures=len(self._recent_failures),
                threshold=self.config.failure_threshold,
                error=str(exception),
                error_type=type(exception).__name__
            )

            # If half-open, any failure reopens circuit
            if self._state == CircuitBreakerState.HALF_OPEN:
                await self._open()
                return

            # Check if we should open circuit
            if len(self._recent_failures) >= self.config.failure_threshold:
                await self._open()

    async def _maybe_attempt_reset(self):
        """Check if we should attempt reset (transition to half-open)"""
        if self._state != CircuitBreakerState.OPEN:
            return

        if not self._opened_at:
            return

        # Check if timeout has elapsed
        elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
        if elapsed >= self.config.timeout_seconds:
            await self._half_open()

    async def _close(self):
        """Transition to CLOSED state"""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._recent_failures = []
        self._opened_at = None

        logger.info(
            "circuit_breaker_closed",
            name=self.name,
            message="Circuit breaker closed - normal operation resumed"
        )

    async def _open(self):
        """Transition to OPEN state"""
        self._state = CircuitBreakerState.OPEN
        self._opened_at = datetime.utcnow()
        self._success_count = 0

        logger.error(
            "circuit_breaker_opened",
            name=self.name,
            failures=self._failure_count,
            recent_failures=len(self._recent_failures),
            timeout_seconds=self.config.timeout_seconds,
            message="Circuit breaker opened - failing fast"
        )

    async def _half_open(self):
        """Transition to HALF_OPEN state"""
        self._state = CircuitBreakerState.HALF_OPEN
        self._success_count = 0

        logger.info(
            "circuit_breaker_half_open",
            name=self.name,
            message="Circuit breaker half-open - testing recovery"
        )

    async def force_open(self):
        """
        Force circuit breaker to OPEN state (emergency stop).

        Use this when you need to immediately stop traffic to a service.

        Usage:
            await breaker.force_open()
        """
        async with self._lock:
            await self._open()
            logger.warning(
                "circuit_breaker_forced_open",
                name=self.name,
                message="Circuit breaker manually opened"
            )

    async def force_close(self):
        """
        Force circuit breaker to CLOSED state (force resume).

        Use this when you know a service has recovered.

        Usage:
            await breaker.force_close()
        """
        async with self._lock:
            await self._close()
            logger.info(
                "circuit_breaker_forced_close",
                name=self.name,
                message="Circuit breaker manually closed"
            )

    async def reset(self):
        """
        Reset circuit breaker to initial state.

        Clears all failure counts and transitions to CLOSED.

        Usage:
            await breaker.reset()
        """
        async with self._lock:
            await self._close()
            logger.info(
                "circuit_breaker_reset",
                name=self.name,
                message="Circuit breaker reset"
            )

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with current state and stats

        Usage:
            stats = breaker.get_stats()
            print(f"State: {stats['state']}, Failures: {stats['failures']}")
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "recent_failures": len(self._recent_failures),
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "window_seconds": self.config.window_seconds
            }
        }
