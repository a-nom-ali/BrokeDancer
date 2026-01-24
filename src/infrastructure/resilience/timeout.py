"""
Timeout Handling

Provides timeout wrappers for async operations.
"""

import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class TimeoutError(Exception):
    """Raised when an operation exceeds its timeout"""

    def __init__(self, seconds: float, operation: str = None):
        self.seconds = seconds
        self.operation = operation
        message = f"Operation timed out after {seconds}s"
        if operation:
            message = f"{operation} timed out after {seconds}s"
        super().__init__(message)


def with_timeout(seconds: float, operation_name: Optional[str] = None):
    """
    Decorator to add timeout to async functions.

    Args:
        seconds: Timeout duration in seconds
        operation_name: Optional operation name for logging

    Returns:
        Decorated function with timeout

    Raises:
        TimeoutError: If operation exceeds timeout

    Usage:
        @with_timeout(5.0)
        async def fetch_price(symbol: str):
            # Will raise TimeoutError if takes > 5 seconds
            return await exchange.get_price(symbol)

        @with_timeout(30.0, operation_name="blockchain_sync")
        async def sync_blockchain():
            # Will raise TimeoutError with operation name
            await sync_all_blocks()

    Benefits:
        - Prevents operations from hanging indefinitely
        - Provides clear timeout errors with operation context
        - Integrates with logging for timeout tracking
        - Works seamlessly with async/await
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__

            try:
                # Use asyncio.wait_for for timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
                return result

            except asyncio.TimeoutError as e:
                # Log timeout
                logger.warning(
                    "operation_timeout",
                    operation=op_name,
                    timeout_seconds=seconds,
                    function=func.__name__
                )

                # Raise custom TimeoutError
                raise TimeoutError(seconds, op_name) from e

        return wrapper

    return decorator


async def with_timeout_async(
    func: Callable,
    *args,
    timeout_seconds: float,
    operation_name: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Execute an async function with a timeout (without decorator).

    This is useful when you can't use decorators or want to apply
    timeouts dynamically.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        timeout_seconds: Timeout duration in seconds
        operation_name: Optional operation name for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)

    Raises:
        TimeoutError: If operation exceeds timeout

    Usage:
        # Apply timeout dynamically
        result = await with_timeout_async(
            exchange.get_price,
            "BTC-USDT",
            timeout_seconds=5.0,
            operation_name="fetch_price"
        )

        # With keyword arguments
        result = await with_timeout_async(
            exchange.place_order,
            timeout_seconds=30.0,
            order=my_order,
            operation_name="place_order"
        )
    """
    op_name = operation_name or func.__name__

    try:
        result = await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=timeout_seconds
        )
        return result

    except asyncio.TimeoutError as e:
        logger.warning(
            "operation_timeout",
            operation=op_name,
            timeout_seconds=timeout_seconds,
            function=func.__name__
        )
        raise TimeoutError(timeout_seconds, op_name) from e


class TimeoutContext:
    """
    Context manager for timeout operations.

    This is useful when you want to apply a timeout to a block of code
    rather than a single function.

    Usage:
        async with TimeoutContext(5.0, "price_fetch"):
            price_btc = await exchange.get_price("BTC-USDT")
            price_eth = await exchange.get_price("ETH-USDT")
            # Both calls must complete within 5 seconds total

        # Handle timeout
        try:
            async with TimeoutContext(10.0, "order_execution"):
                await prepare_order()
                await place_order()
                await confirm_order()
        except TimeoutError as e:
            logger.error("Order execution timed out", error=str(e))
    """

    def __init__(self, seconds: float, operation_name: str = "operation"):
        """
        Initialize timeout context.

        Args:
            seconds: Timeout duration in seconds
            operation_name: Operation name for logging
        """
        self.seconds = seconds
        self.operation_name = operation_name
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Enter context"""
        # Create task for timeout
        self._task = asyncio.create_task(asyncio.sleep(self.seconds))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        # Cancel timeout task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # If task completed (timeout occurred), raise TimeoutError
        if self._task and self._task.done() and not self._task.cancelled():
            logger.warning(
                "operation_timeout",
                operation=self.operation_name,
                timeout_seconds=self.seconds
            )
            raise TimeoutError(self.seconds, self.operation_name)

        return False


async def wait_for_any(
    tasks: list[asyncio.Task],
    timeout_seconds: Optional[float] = None,
    operation_name: str = "wait_for_any"
) -> tuple[Any, list[asyncio.Task]]:
    """
    Wait for any task to complete (with optional timeout).

    Returns the first completed task result and cancels remaining tasks.

    Args:
        tasks: List of asyncio tasks
        timeout_seconds: Optional timeout in seconds
        operation_name: Operation name for logging

    Returns:
        Tuple of (result, remaining_tasks)

    Raises:
        TimeoutError: If timeout occurs before any task completes

    Usage:
        # Race multiple API calls
        tasks = [
            asyncio.create_task(binance.get_price("BTC-USDT")),
            asyncio.create_task(coinbase.get_price("BTC-USDT")),
            asyncio.create_task(kraken.get_price("BTC-USDT"))
        ]

        # Use whichever responds first
        result, remaining = await wait_for_any(tasks, timeout_seconds=5.0)

        # Cancel remaining tasks
        for task in remaining:
            task.cancel()
    """
    try:
        done, pending = await asyncio.wait(
            tasks,
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED
        )

        if not done:
            # Timeout occurred
            logger.warning(
                "operation_timeout",
                operation=operation_name,
                timeout_seconds=timeout_seconds,
                pending_tasks=len(pending)
            )
            raise TimeoutError(timeout_seconds, operation_name)

        # Get first completed result
        completed_task = list(done)[0]
        result = completed_task.result()

        return result, list(pending)

    except asyncio.TimeoutError as e:
        logger.warning(
            "operation_timeout",
            operation=operation_name,
            timeout_seconds=timeout_seconds
        )
        raise TimeoutError(timeout_seconds, operation_name) from e


async def wait_for_all(
    tasks: list[asyncio.Task],
    timeout_seconds: Optional[float] = None,
    operation_name: str = "wait_for_all"
) -> list[Any]:
    """
    Wait for all tasks to complete (with optional timeout).

    Args:
        tasks: List of asyncio tasks
        timeout_seconds: Optional timeout in seconds
        operation_name: Operation name for logging

    Returns:
        List of results from all tasks

    Raises:
        TimeoutError: If timeout occurs before all tasks complete

    Usage:
        # Wait for all price fetches
        tasks = [
            asyncio.create_task(fetch_price("BTC-USDT")),
            asyncio.create_task(fetch_price("ETH-USDT")),
            asyncio.create_task(fetch_price("SOL-USDT"))
        ]

        # All must complete within 10 seconds
        results = await wait_for_all(tasks, timeout_seconds=10.0)
        btc_price, eth_price, sol_price = results
    """
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=timeout_seconds
        )
        return results

    except asyncio.TimeoutError as e:
        logger.warning(
            "operation_timeout",
            operation=operation_name,
            timeout_seconds=timeout_seconds,
            total_tasks=len(tasks)
        )
        raise TimeoutError(timeout_seconds, operation_name) from e


# Pre-configured timeout decorators for common use cases

# Quick operations (1 second)
with_quick_timeout = with_timeout(1.0)

# Normal operations (5 seconds)
with_normal_timeout = with_timeout(5.0)

# Slow operations (30 seconds)
with_slow_timeout = with_timeout(30.0)

# API calls (10 seconds)
with_api_timeout = with_timeout(10.0)

# Database queries (5 seconds)
with_db_timeout = with_timeout(5.0)

# Network operations (15 seconds)
with_network_timeout = with_timeout(15.0)
