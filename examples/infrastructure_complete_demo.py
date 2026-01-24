"""
Complete Infrastructure Demo

Demonstrates the full infrastructure stack working together.

Run with:
    # Development environment
    python examples/infrastructure_complete_demo.py

    # Production environment
    ENV=production python examples/infrastructure_complete_demo.py
"""

import asyncio
import random
from src.infrastructure.factory import create_infrastructure
from src.infrastructure.logging import get_logger, set_correlation_id

logger = get_logger(__name__)


async def demo_infrastructure_creation():
    """Demonstrate creating infrastructure for different environments"""
    print("\n=== Infrastructure Creation Demo ===\n")

    # Development infrastructure (in-memory, fast)
    print("Creating development infrastructure...")
    dev_infra = await create_infrastructure("development")
    print(f"  Environment: {dev_infra.config.env.value}")
    print(f"  State backend: {dev_infra.config.state.backend}")
    print(f"  Events backend: {dev_infra.config.events.backend}")
    print(f"  Log format: {dev_infra.config.logging.format}")
    await dev_infra.close()

    print("\n✓ Development infrastructure created\n")


async def demo_state_and_events():
    """Demonstrate state and events working together"""
    print("\n=== State & Events Integration Demo ===\n")

    infra = await create_infrastructure("development")

    # Subscribe to events
    events_received = []

    async def price_handler(event):
        logger.info("price_event_received", event=event)
        events_received.append(event)

    await infra.events.subscribe("prices", price_handler)

    # Store state and publish events
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

    for symbol in symbols:
        price = random.uniform(1000, 60000)

        # Store in state
        await infra.state.set(f"price:{symbol}", price)
        logger.info("price_stored", symbol=symbol, price=price)

        # Publish event
        await infra.events.publish("prices", {
            "symbol": symbol,
            "price": price,
            "timestamp": "2024-01-24T10:00:00Z"
        })

    # Wait for events
    await asyncio.sleep(0.1)

    # Retrieve from state
    btc_price = await infra.state.get("price:BTC-USDT")
    print(f"\nRetrieved BTC price from state: ${btc_price:,.2f}")
    print(f"Received {len(events_received)} price events")

    print("\n✓ State and events working together\n")

    await infra.close()


async def demo_emergency_controls():
    """Demonstrate emergency controls and risk limits"""
    print("\n=== Emergency Controls Demo ===\n")

    infra = await create_infrastructure("development")

    # Subscribe to emergency events
    async def on_emergency_event(event):
        logger.critical(
            "emergency_event",
            previous_state=event.previous_state.value,
            new_state=event.new_state.value,
            reason=event.reason
        )

    await infra.emergency.subscribe(on_emergency_event)

    # Normal operation
    print("Checking if can trade...")
    if infra.emergency.can_trade():
        print("  ✓ Trading allowed (NORMAL state)")

    # Check risk limit (within bounds)
    print("\nChecking risk limit (within bounds)...")
    await infra.emergency.check_risk_limit(
        "daily_loss",
        -250.0,  # Current loss
        -500.0,  # Limit
        auto_halt=False
    )
    print("  ✓ Within risk limits")

    # Trigger alert
    print("\nTriggering alert state...")
    await infra.emergency.alert("High API latency detected")
    print(f"  State: {infra.emergency.state.value}")
    print(f"  Can trade: {infra.emergency.can_trade()}")

    # Simulate approaching risk limit
    print("\nSimulating risk limit approach...")
    try:
        await infra.emergency.check_risk_limit(
            "daily_loss",
            -550.0,  # Exceeded limit
            -500.0,  # Limit
            auto_halt=True  # Will auto-halt
        )
    except Exception as e:
        print(f"  Risk limit exceeded: {e}")
        print(f"  State: {infra.emergency.state.value}")
        print(f"  Can trade: {infra.emergency.can_trade()}")

    # Get status
    status = infra.emergency.get_status()
    print(f"\nEmergency Controller Status:")
    print(f"  State: {status['state']}")
    print(f"  Can trade: {status['can_trade']}")
    print(f"  Risk limits tracked: {len(status['risk_limits'])}")

    print("\n✓ Emergency controls working\n")

    await infra.close()


async def demo_circuit_breakers():
    """Demonstrate circuit breakers protecting services"""
    print("\n=== Circuit Breaker Demo ===\n")

    infra = await create_infrastructure("development")

    # Create circuit breaker for external API
    api_breaker = infra.create_circuit_breaker("exchange_api")

    call_count = 0

    async def flaky_api_call():
        nonlocal call_count
        call_count += 1

        # Fail first 5 times
        if call_count <= 5:
            logger.warning("api_call_failed", attempt=call_count)
            raise ConnectionError("API unavailable")

        logger.info("api_call_succeeded", attempt=call_count)
        return {"price": 50234.56}

    # Make calls through circuit breaker
    print("Making API calls through circuit breaker...")

    for i in range(8):
        try:
            result = await api_breaker.call(flaky_api_call)
            print(f"  Call {i+1}: Success - {result}")
        except ConnectionError as e:
            print(f"  Call {i+1}: Failed - {e}")
        except Exception as e:
            print(f"  Call {i+1}: Circuit breaker open - {type(e).__name__}")

    print(f"\nCircuit breaker state: {api_breaker.state.value}")
    print("✓ Circuit breaker protected against cascading failures\n")

    await infra.close()


async def demo_realistic_trading_flow():
    """Demonstrate realistic trading bot flow"""
    print("\n=== Realistic Trading Flow Demo ===\n")

    infra = await create_infrastructure("development")

    # Set correlation ID for request tracing
    execution_id = "exec_abc123"
    set_correlation_id(execution_id)

    logger.info("execution_started", execution_id=execution_id)

    # 1. Check emergency state
    print("1. Checking emergency state...")
    try:
        await infra.emergency.assert_can_trade()
        print("   ✓ Trading allowed")
    except Exception as e:
        print(f"   ✗ Trading halted: {e}")
        return

    # 2. Check risk limits
    print("\n2. Checking risk limits...")
    try:
        await infra.emergency.check_risk_limit(
            "daily_loss",
            -350.0,
            -500.0,
            auto_halt=False
        )
        print("   ✓ Within risk limits (70% utilized)")
    except Exception as e:
        print(f"   ✗ Risk limit exceeded: {e}")
        return

    # 3. Create circuit breaker for API
    print("\n3. Creating circuit breaker for exchange API...")
    api_breaker = infra.create_circuit_breaker(
        "exchange_api",
        failure_threshold=3
    )
    print("   ✓ Circuit breaker ready")

    # 4. Fetch prices with resilience
    print("\n4. Fetching prices (with retry + circuit breaker + timeout)...")

    from src.infrastructure.resilience import with_retry, with_timeout

    @with_retry(max_attempts=2, min_wait_seconds=0.5)
    @with_timeout(5.0)
    async def fetch_price(symbol: str):
        # Simulate 20% failure rate
        if random.random() < 0.2:
            raise ConnectionError("Network error")

        await asyncio.sleep(0.1)
        return random.uniform(40000, 60000)

    try:
        btc_price = await api_breaker.call(fetch_price, "BTC-USDT")
        logger.info("price_fetched", symbol="BTC-USDT", price=btc_price)
        print(f"   ✓ BTC price: ${btc_price:,.2f}")

        # Store in state
        await infra.state.set("price:BTC-USDT", btc_price)

        # Publish event
        await infra.events.publish("prices", {
            "symbol": "BTC-USDT",
            "price": btc_price
        })

    except Exception as e:
        logger.error("price_fetch_failed", error=str(e))
        print(f"   ✗ Failed to fetch price: {e}")
        return

    # 5. Execute trade (simulated)
    print("\n5. Executing trade...")
    logger.info("trade_executed", symbol="BTC-USDT", side="buy", quantity=0.1)
    print("   ✓ Trade executed successfully")

    # 6. Update risk tracking
    print("\n6. Updating risk tracking...")
    new_daily_loss = -380.0  # Slightly worse
    await infra.state.set("daily_loss", new_daily_loss)
    print(f"   Daily loss: ${new_daily_loss:,.2f}")

    logger.info("execution_completed", execution_id=execution_id)

    print("\n✓ Complete trading flow executed successfully\n")

    await infra.close()


async def demo_health_check():
    """Demonstrate infrastructure health check"""
    print("\n=== Health Check Demo ===\n")

    infra = await create_infrastructure("development")

    # Perform health check
    health = await infra.health_check()

    print(f"Overall status: {health['status'].upper()}")
    print("\nComponent health:")
    for component, status in health['components'].items():
        if isinstance(status, dict):
            print(f"  {component}:")
            for key, value in status.items():
                print(f"    {key}: {value}")
        else:
            print(f"  {component}: {status}")

    print("\n✓ Health check complete\n")

    await infra.close()


async def demo_state_persistence():
    """Demonstrate emergency state persistence"""
    print("\n=== State Persistence Demo ===\n")

    # Create infrastructure
    infra1 = await create_infrastructure("development", controller_id="persistent_bot")

    # Set emergency state
    print("Setting emergency halt...")
    await infra1.emergency.halt("Simulating system issue")
    await infra1.emergency.check_risk_limit("daily_loss", -450.0, -500.0, auto_halt=False)

    # Persist state
    print("Persisting emergency state...")
    await infra1.emergency.persist_state(infra1.state)
    print(f"  State: {infra1.emergency.state.value}")
    print(f"  Halt reason: {infra1.emergency._halt_reason}")

    await infra1.close()

    # Simulate restart - create new infrastructure
    print("\nSimulating restart...")
    infra2 = await create_infrastructure("development", controller_id="persistent_bot")

    # Restore state
    restored = await infra2.emergency.restore_state(infra2.state)
    print(f"\nState restored: {restored}")
    print(f"  State: {infra2.emergency.state.value}")
    print(f"  Halt reason: {infra2.emergency._halt_reason}")
    print(f"  Can trade: {infra2.emergency.can_trade()}")

    print("\n✓ State persistence working\n")

    await infra2.close()


async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("Complete Infrastructure Demo")
    print("="*60)

    await demo_infrastructure_creation()
    await demo_state_and_events()
    await demo_emergency_controls()
    await demo_circuit_breakers()
    await demo_realistic_trading_flow()
    await demo_health_check()
    await demo_state_persistence()

    print("="*60)
    print("Demo Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
