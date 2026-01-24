"""
Resilience Demo

Demonstrates retry logic, circuit breakers, and timeout handling.

Run with:
    python examples/resilience_demo.py
"""

import asyncio
import random
from src.infrastructure.resilience import (
    with_retry,
    RetryConfig,
    RetryExhausted,
    CircuitBreaker,
    CircuitBreakerOpen,
    with_timeout,
    TimeoutError,
    TimeoutContext,
    wait_for_any
)
from src.infrastructure.logging import configure_logging, get_logger

logger = get_logger(__name__)


# ============================================================================
# Retry Demos
# ============================================================================

def demo_basic_retry():
    """Demonstrate basic retry with exponential backoff"""
    print("\n=== Basic Retry Demo ===\n")

    call_count = 0

    @with_retry(max_attempts=3, min_wait_seconds=0.5, max_wait_seconds=5)
    async def flaky_api_call():
        nonlocal call_count
        call_count += 1
        logger.info("api_call_attempt", attempt=call_count)

        # Fail first 2 times, succeed on 3rd
        if call_count < 3:
            raise ConnectionError(f"Network error (attempt {call_count})")

        return {"price": 50234.56}

    async def run():
        try:
            result = await flaky_api_call()
            logger.info("api_call_succeeded", result=result, total_attempts=call_count)
        except RetryExhausted as e:
            logger.error("api_call_failed", error=str(e))

    asyncio.run(run())
    print(f"\n  ✓ API call succeeded after {call_count} attempts\n")


def demo_retry_config():
    """Demonstrate retry with shared configuration"""
    print("\n=== Retry Config Demo ===\n")

    # Shared retry config for all API calls
    api_retry_config = RetryConfig(
        max_attempts=5,
        min_wait_seconds=1,
        max_wait_seconds=30,
        multiplier=2,
        retry_on=(ConnectionError, TimeoutError)
    )

    @with_retry(
        max_attempts=api_retry_config.max_attempts,
        min_wait_seconds=api_retry_config.min_wait_seconds,
        retry_on=api_retry_config.retry_on
    )
    async def fetch_price(symbol: str):
        logger.info("fetching_price", symbol=symbol)
        # Simulate 50% failure rate
        if random.random() < 0.5:
            raise ConnectionError("Network error")
        return {symbol: random.uniform(1000, 60000)}

    async def run():
        try:
            result = await fetch_price("BTC-USDT")
            logger.info("price_fetched", result=result)
        except RetryExhausted as e:
            logger.error("price_fetch_failed", error=str(e))

    asyncio.run(run())
    print("  ✓ Price fetch completed (may have retried)\n")


def demo_selective_retry():
    """Demonstrate retrying only specific exceptions"""
    print("\n=== Selective Retry Demo ===\n")

    @with_retry(
        max_attempts=3,
        retry_on=(ConnectionError, TimeoutError),  # Only retry these
        min_wait_seconds=0.5
    )
    async def validate_and_fetch():
        # Validation errors should NOT be retried
        if random.random() < 0.3:
            logger.warning("validation_error", reason="Invalid symbol")
            raise ValueError("Invalid symbol format")  # Won't retry

        # Network errors WILL be retried
        if random.random() < 0.3:
            logger.warning("network_error", reason="Connection failed")
            raise ConnectionError("Network error")  # Will retry

        return {"status": "success"}

    async def run():
        try:
            result = await validate_and_fetch()
            logger.info("operation_succeeded", result=result)
        except ValueError as e:
            logger.error("validation_failed", error=str(e))
        except RetryExhausted as e:
            logger.error("operation_failed_after_retries", error=str(e))

    asyncio.run(run())
    print("  ✓ Selective retry completed\n")


# ============================================================================
# Circuit Breaker Demos
# ============================================================================

def demo_circuit_breaker_basic():
    """Demonstrate circuit breaker preventing cascading failures"""
    print("\n=== Circuit Breaker Demo ===\n")

    breaker = CircuitBreaker(
        "exchange_api",
        failure_threshold=3,
        timeout_seconds=2,
        window_seconds=10
    )

    call_count = 0

    async def unreliable_api():
        nonlocal call_count
        call_count += 1
        # Fail for first 5 calls
        if call_count <= 5:
            raise ConnectionError("API is down")
        return {"status": "ok"}

    async def run():
        # First 3 calls will fail and open circuit
        for i in range(3):
            try:
                await breaker.call(unreliable_api)
            except ConnectionError:
                logger.warning("api_call_failed", attempt=i+1)

        logger.info("circuit_breaker_state", state=breaker.state.value)

        # Next calls will fail fast (circuit is open)
        try:
            await breaker.call(unreliable_api)
        except CircuitBreakerOpen as e:
            logger.warning("circuit_breaker_open", message=str(e))

        print(f"\n  Circuit State: {breaker.state.value.upper()}")
        print(f"  Failures: {breaker._failure_count}")
        print("  ✓ Circuit breaker prevented additional failed attempts\n")

    asyncio.run(run())


def demo_circuit_breaker_recovery():
    """Demonstrate circuit breaker recovery"""
    print("\n=== Circuit Breaker Recovery Demo ===\n")

    breaker = CircuitBreaker(
        "payment_api",
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=1,  # Short timeout for demo
        window_seconds=10
    )

    call_count = 0

    async def recovering_api():
        nonlocal call_count
        call_count += 1
        # Fail first 2 times, then succeed
        if call_count <= 2:
            raise ConnectionError("Service unavailable")
        return {"status": "ok", "call": call_count}

    async def run():
        # Open circuit (2 failures)
        for i in range(2):
            try:
                await breaker.call(recovering_api)
            except ConnectionError:
                logger.warning("api_failure", attempt=i+1)

        print(f"\n  Circuit opened after {call_count} failures")
        logger.info("circuit_state", state=breaker.state.value)

        # Wait for timeout (circuit goes half-open)
        await asyncio.sleep(1.5)
        print("  Waiting for timeout...")

        # Try again (should succeed and start closing)
        try:
            result = await breaker.call(recovering_api)
            logger.info("api_recovery_attempt_1", result=result)
            print("  First recovery attempt succeeded (half-open)")

            result = await breaker.call(recovering_api)
            logger.info("api_recovery_attempt_2", result=result)
            print("  Second recovery attempt succeeded")

        except CircuitBreakerOpen as e:
            logger.error("still_open", error=str(e))

        print(f"  Circuit State: {breaker.state.value.upper()}")
        print("  ✓ Circuit breaker recovered\n")

    asyncio.run(run())


def demo_circuit_breaker_stats():
    """Demonstrate circuit breaker statistics"""
    print("\n=== Circuit Breaker Stats Demo ===\n")

    breaker = CircuitBreaker("analytics_api", failure_threshold=5)

    async def api_call():
        if random.random() < 0.3:
            raise ConnectionError("Random failure")
        return {"data": "some data"}

    async def run():
        # Make some calls
        for i in range(10):
            try:
                await breaker.call(api_call)
                logger.info("call_succeeded", attempt=i+1)
            except ConnectionError:
                logger.warning("call_failed", attempt=i+1)
            except CircuitBreakerOpen:
                logger.warning("circuit_open", attempt=i+1)
                break

        # Get stats
        stats = breaker.get_stats()
        print(f"\n  Circuit Breaker: {stats['name']}")
        print(f"  State: {stats['state']}")
        print(f"  Total Failures: {stats['failure_count']}")
        print(f"  Recent Failures: {stats['recent_failures']}")
        print(f"  Threshold: {stats['config']['failure_threshold']}")
        print("  ✓ Stats retrieved\n")

    asyncio.run(run())


# ============================================================================
# Timeout Demos
# ============================================================================

def demo_basic_timeout():
    """Demonstrate basic timeout"""
    print("\n=== Basic Timeout Demo ===\n")

    @with_timeout(2.0, operation_name="price_fetch")
    async def fetch_with_timeout():
        logger.info("starting_fetch")
        # Simulate slow operation
        await asyncio.sleep(0.5)
        logger.info("fetch_completed")
        return {"price": 50234.56}

    async def run():
        try:
            result = await fetch_with_timeout()
            logger.info("operation_succeeded", result=result)
            print("  ✓ Operation completed within timeout\n")
        except TimeoutError as e:
            logger.error("operation_timeout", error=str(e))
            print(f"  ✗ Operation timed out: {e}\n")

    asyncio.run(run())


def demo_timeout_exceeded():
    """Demonstrate timeout being exceeded"""
    print("\n=== Timeout Exceeded Demo ===\n")

    @with_timeout(0.5, operation_name="slow_blockchain_sync")
    async def slow_operation():
        logger.info("starting_sync")
        await asyncio.sleep(2.0)  # Will timeout
        return {"status": "synced"}

    async def run():
        try:
            result = await slow_operation()
            logger.info("sync_completed", result=result)
        except TimeoutError as e:
            logger.warning("sync_timeout", error=str(e), timeout=e.seconds)
            print(f"  ✗ Operation timed out after {e.seconds}s")
            print("  ✓ Timeout detected and handled\n")

    asyncio.run(run())


def demo_timeout_context():
    """Demonstrate timeout context for multiple operations"""
    print("\n=== Timeout Context Demo ===\n")

    async def run():
        try:
            async with TimeoutContext(2.0, "multi_price_fetch"):
                logger.info("fetching_multiple_prices")

                # All operations must complete within 2 seconds total
                await asyncio.sleep(0.3)  # BTC
                logger.info("price_fetched", symbol="BTC")

                await asyncio.sleep(0.3)  # ETH
                logger.info("price_fetched", symbol="ETH")

                await asyncio.sleep(0.3)  # SOL
                logger.info("price_fetched", symbol="SOL")

                print("  ✓ All prices fetched within timeout\n")

        except TimeoutError as e:
            logger.error("batch_fetch_timeout", error=str(e))
            print(f"  ✗ Batch operation timed out\n")

    asyncio.run(run())


def demo_race_condition():
    """Demonstrate racing multiple API calls"""
    print("\n=== Race Condition Demo (wait_for_any) ===\n")

    async def fetch_from_binance():
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"exchange": "binance", "price": 50234.56}

    async def fetch_from_coinbase():
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"exchange": "coinbase", "price": 50245.12}

    async def fetch_from_kraken():
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"exchange": "kraken", "price": 50221.34}

    async def run():
        logger.info("starting_race", exchanges=3)

        tasks = [
            asyncio.create_task(fetch_from_binance()),
            asyncio.create_task(fetch_from_coinbase()),
            asyncio.create_task(fetch_from_kraken())
        ]

        # Use whichever responds first
        result, remaining = await wait_for_any(tasks, timeout_seconds=3.0)

        logger.info("race_winner", result=result)
        print(f"\n  Winner: {result['exchange']}")
        print(f"  Price: ${result['price']:,.2f}")
        print("  ✓ Used fastest API response\n")

        # Cancel remaining
        for task in remaining:
            task.cancel()

    asyncio.run(run())


# ============================================================================
# Integration Demos
# ============================================================================

def demo_full_resilience_stack():
    """Demonstrate combining retry, circuit breaker, and timeout"""
    print("\n=== Full Resilience Stack Demo ===\n")

    breaker = CircuitBreaker(
        "resilient_api",
        failure_threshold=3,
        timeout_seconds=5,
        window_seconds=30
    )

    call_count = 0

    @with_retry(max_attempts=2, min_wait_seconds=0.5)
    @with_timeout(3.0, operation_name="api_call")
    async def fully_protected_api_call():
        nonlocal call_count
        call_count += 1

        logger.info("api_call_attempt", attempt=call_count)

        # Simulate flaky API
        if call_count == 1:
            raise ConnectionError("Network blip")  # Will retry

        # Simulate slow response (but within timeout)
        await asyncio.sleep(0.5)

        return {"status": "success", "data": "important data"}

    async def run():
        try:
            result = await breaker.call(fully_protected_api_call)
            logger.info("api_call_succeeded", result=result, total_attempts=call_count)

            print("\n  Resilience Stack Applied:")
            print(f"    ✓ Retry: {call_count} attempts")
            print(f"    ✓ Timeout: Operation completed in time")
            print(f"    ✓ Circuit Breaker: {breaker.state.value}")
            print("\n  ✓ Full resilience stack working\n")

        except Exception as e:
            logger.error("api_call_failed", error=str(e))
            print(f"\n  ✗ Operation failed: {e}\n")

    asyncio.run(run())


def demo_realistic_trading_scenario():
    """Demonstrate realistic trading bot scenario"""
    print("\n=== Realistic Trading Scenario ===\n")

    price_breaker = CircuitBreaker("price_api", failure_threshold=5, timeout_seconds=30)
    order_breaker = CircuitBreaker("order_api", failure_threshold=3, timeout_seconds=60)

    @with_retry(max_attempts=3, min_wait_seconds=1, retry_on=(ConnectionError,))
    @with_timeout(5.0)
    async def fetch_price(symbol: str):
        await asyncio.sleep(0.2)  # Simulate API call
        if random.random() < 0.1:  # 10% failure rate
            raise ConnectionError("Price API unavailable")
        return random.uniform(40000, 60000)

    @with_retry(max_attempts=2, min_wait_seconds=2, retry_on=(ConnectionError,))
    @with_timeout(10.0)
    async def place_order(symbol: str, side: str, quantity: float):
        await asyncio.sleep(0.5)  # Simulate order placement
        if random.random() < 0.05:  # 5% failure rate
            raise ConnectionError("Order API unavailable")
        return {
            "order_id": f"order_{random.randint(1000, 9999)}",
            "status": "filled",
            "symbol": symbol,
            "side": side,
            "quantity": quantity
        }

    async def execute_trade():
        try:
            # 1. Fetch price with resilience
            logger.info("fetching_price", symbol="BTC-USDT")
            price = await price_breaker.call(fetch_price, "BTC-USDT")
            logger.info("price_received", price=price)

            # 2. Place order with resilience
            logger.info("placing_order", side="buy", quantity=0.1)
            order = await order_breaker.call(place_order, "BTC-USDT", "buy", 0.1)
            logger.info("order_placed", order=order)

            return {"price": price, "order": order}

        except CircuitBreakerOpen as e:
            logger.error("circuit_breaker_open", error=str(e))
            return None
        except TimeoutError as e:
            logger.error("operation_timeout", error=str(e))
            return None
        except RetryExhausted as e:
            logger.error("retry_exhausted", error=str(e))
            return None

    async def run():
        result = await execute_trade()

        if result:
            print("\n  ✓ Trade executed successfully")
            print(f"    Price: ${result['price']:,.2f}")
            print(f"    Order: {result['order']['order_id']}")
        else:
            print("\n  ✗ Trade failed (handled gracefully)")

        print(f"\n  Circuit Breaker States:")
        print(f"    Price API: {price_breaker.state.value}")
        print(f"    Order API: {order_breaker.state.value}\n")

    asyncio.run(run())


def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("Resilience Infrastructure Demo")
    print("="*60)

    # Configure logging
    configure_logging(level="INFO", format="console")

    # Retry demos
    demo_basic_retry()
    demo_retry_config()
    demo_selective_retry()

    # Circuit breaker demos
    demo_circuit_breaker_basic()
    demo_circuit_breaker_recovery()
    demo_circuit_breaker_stats()

    # Timeout demos
    demo_basic_timeout()
    demo_timeout_exceeded()
    demo_timeout_context()
    demo_race_condition()

    # Integration demos
    demo_full_resilience_stack()
    demo_realistic_trading_scenario()

    print("="*60)
    print("Demo Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
