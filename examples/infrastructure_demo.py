"""
Infrastructure Demo

Demonstrates how to use the state store abstraction with both
in-memory and Redis backends.

Run with:
    # In-memory (no dependencies)
    python examples/infrastructure_demo.py --backend memory

    # Redis (requires docker-compose up)
    docker-compose -f docker-compose.infrastructure.yml up -d redis
    python examples/infrastructure_demo.py --backend redis
"""

import asyncio
import argparse
from datetime import timedelta
from src.infrastructure.state import create_state_store


async def demo_basic_operations(store):
    """Demonstrate basic state store operations"""
    print("\n=== Basic Operations ===")

    # Set and get
    print("\n1. Set and Get:")
    await store.set("user:123", {"name": "Alice", "balance": 1000.0})
    user = await store.get("user:123")
    print(f"   User: {user}")

    # Exists check
    print("\n2. Exists Check:")
    exists = await store.exists("user:123")
    print(f"   user:123 exists: {exists}")
    exists = await store.exists("user:999")
    print(f"   user:999 exists: {exists}")

    # Delete
    print("\n3. Delete:")
    await store.delete("user:123")
    user = await store.get("user:123")
    print(f"   After delete: {user}")


async def demo_batch_operations(store):
    """Demonstrate batch operations"""
    print("\n=== Batch Operations ===")

    # Set many
    print("\n1. Set Many:")
    await store.set_many({
        "product:1": {"name": "Laptop", "price": 999.99},
        "product:2": {"name": "Mouse", "price": 29.99},
        "product:3": {"name": "Keyboard", "price": 79.99}
    })
    print("   Set 3 products")

    # Get many
    print("\n2. Get Many:")
    products = await store.get_many(["product:1", "product:2", "product:3"])
    for key, value in products.items():
        print(f"   {key}: {value['name']} - ${value['price']}")


async def demo_counters(store):
    """Demonstrate atomic counters"""
    print("\n=== Atomic Counters ===")

    # Increment
    print("\n1. Increment:")
    count = await store.increment("page_views")
    print(f"   Page views: {count}")

    count = await store.increment("page_views")
    print(f"   Page views: {count}")

    count = await store.increment("page_views", 10)
    print(f"   Page views (after +10): {count}")

    # Decrement
    print("\n2. Decrement:")
    await store.set("stock", 100)
    stock = await store.decrement("stock", 5)
    print(f"   Stock after sale: {stock}")


async def demo_ttl(store):
    """Demonstrate time-to-live"""
    print("\n=== Time-to-Live (TTL) ===")

    # Set with TTL
    print("\n1. Set with 3 second TTL:")
    await store.set("session:abc123", {"user_id": 123}, ttl=timedelta(seconds=3))
    session = await store.get("session:abc123")
    print(f"   Immediately after set: {session}")

    print("   Waiting 1 second...")
    await asyncio.sleep(1)
    session = await store.get("session:abc123")
    print(f"   After 1 second: {session}")

    print("   Waiting 3 more seconds...")
    await asyncio.sleep(3)
    session = await store.get("session:abc123")
    print(f"   After expiration: {session}")


async def demo_conditional_operations(store):
    """Demonstrate conditional operations"""
    print("\n=== Conditional Operations ===")

    # Set if not exists
    print("\n1. Set If Not Exists:")
    success = await store.set_if_not_exists("config:api_key", "secret123")
    print(f"   First set: {success}")

    success = await store.set_if_not_exists("config:api_key", "different")
    print(f"   Second set (should fail): {success}")

    value = await store.get("config:api_key")
    print(f"   Final value: {value}")

    # Get and delete (atomic)
    print("\n2. Get and Delete:")
    await store.set("temp_token", "xyz789")
    token = await store.get_and_delete("temp_token")
    print(f"   Retrieved token: {token}")

    exists = await store.exists("temp_token")
    print(f"   Token still exists: {exists}")

    # Get or default
    print("\n3. Get or Default:")
    value = await store.get_or_default("missing_key", "default_value")
    print(f"   Missing key returns: {value}")


async def demo_realistic_use_case(store):
    """Demonstrate realistic trading bot use case"""
    print("\n=== Realistic Use Case: Bot State Management ===")

    bot_id = "bot_001"
    strategy_id = "arb_btc"

    # 1. Store bot configuration
    print("\n1. Store Bot Configuration:")
    await store.set(f"bot:{bot_id}:config", {
        "name": "BTC Arbitrage Bot",
        "enabled": True,
        "capital": 10000.0,
        "max_position_size": 1000.0
    })
    print("   Bot config stored")

    # 2. Track strategy metrics
    print("\n2. Track Strategy Metrics:")
    await store.set(f"strategy:{strategy_id}:metrics", {
        "total_trades": 42,
        "successful_trades": 35,
        "total_pnl": 234.56,
        "win_rate": 0.833
    })
    print("   Strategy metrics stored")

    # 3. Increment trade counter
    print("\n3. Execute Trade (increment counter):")
    trades = await store.increment(f"strategy:{strategy_id}:trade_count")
    print(f"   Total trades: {trades}")

    # 4. Store execution state (with TTL for cleanup)
    print("\n4. Store Execution State:")
    execution_id = "exec_abc123"
    await store.set(
        f"execution:{execution_id}",
        {
            "bot_id": bot_id,
            "strategy_id": strategy_id,
            "started_at": "2024-01-24T10:00:00Z",
            "status": "running",
            "nodes_completed": ["price_check", "spread_calc"]
        },
        ttl=timedelta(hours=1)  # Auto-cleanup old executions
    )
    print(f"   Execution state stored (TTL: 1 hour)")

    # 5. Check daily loss limit
    print("\n5. Risk Management (daily loss tracking):")
    daily_loss = await store.get_or_default(
        f"risk:{bot_id}:daily_loss",
        0.0
    )
    print(f"   Daily loss: ${daily_loss}")

    # Simulate a losing trade
    new_loss = -50.0
    await store.set(
        f"risk:{bot_id}:daily_loss",
        daily_loss + new_loss,
        ttl=timedelta(days=1)  # Reset at midnight
    )
    print(f"   After losing trade: ${daily_loss + new_loss}")

    # 6. Retrieve all bot state
    print("\n6. Retrieve Complete Bot State:")
    state = await store.get_many([
        f"bot:{bot_id}:config",
        f"strategy:{strategy_id}:metrics",
        f"risk:{bot_id}:daily_loss"
    ])
    print(f"   Bot enabled: {state[f'bot:{bot_id}:config']['enabled']}")
    print(f"   Win rate: {state[f'strategy:{strategy_id}:metrics']['win_rate']:.1%}")
    print(f"   Daily loss: ${state[f'risk:{bot_id}:daily_loss']}")


async def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(description="Infrastructure Demo")
    parser.add_argument(
        "--backend",
        choices=["memory", "redis"],
        default="memory",
        help="State store backend to use"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Infrastructure Demo - {args.backend.upper()} Backend")
    print(f"{'='*60}")

    # Create state store
    if args.backend == "redis":
        store = create_state_store("redis", url="redis://localhost:6379/0")

        # Test connection
        try:
            if not await store.ping():
                print("\n❌ Error: Cannot connect to Redis")
                print("   Make sure Redis is running:")
                print("   docker-compose -f docker-compose.infrastructure.yml up -d redis")
                return
            print("\n✅ Connected to Redis")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Make sure Redis is running:")
            print("   docker-compose -f docker-compose.infrastructure.yml up -d redis")
            return
    else:
        store = create_state_store("memory")
        print("\n✅ Using in-memory store")

    try:
        # Run demos
        await demo_basic_operations(store)
        await demo_batch_operations(store)
        await demo_counters(store)
        await demo_ttl(store)
        await demo_conditional_operations(store)
        await demo_realistic_use_case(store)

        print(f"\n{'='*60}")
        print("Demo Complete!")
        print(f"{'='*60}\n")

    finally:
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
