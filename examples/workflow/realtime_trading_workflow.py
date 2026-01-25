"""
Real-Time Trading Workflow Example

Demonstrates a complete trading workflow using the Enhanced Workflow Executor
with full infrastructure integration:
- Event emission to event bus
- Correlation ID tracking
- Emergency halt checks
- State persistence
- Circuit breakers and retry logic
- Real-time monitoring via WebSocket

This example simulates a BTC arbitrage trading workflow between two exchanges.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from datetime import datetime


# Sample trading workflow definition
ARBITRAGE_WORKFLOW = {
    "blocks": [
        {
            "id": "price_binance",
            "name": "Binance BTC Price",
            "category": "providers",
            "type": "price_feed",
            "properties": {
                "exchange": "binance",
                "symbol": "BTC/USDT"
            },
            "config": {},
            "inputs": {},
            "outputs": ["price", "timestamp"],
            "timeout": 10.0
        },
        {
            "id": "price_coinbase",
            "name": "Coinbase BTC Price",
            "category": "providers",
            "type": "price_feed",
            "properties": {
                "exchange": "coinbase",
                "symbol": "BTC/USD"
            },
            "config": {},
            "inputs": {},
            "outputs": ["price", "timestamp"],
            "timeout": 10.0
        },
        {
            "id": "calculate_spread",
            "name": "Calculate Spread",
            "category": "risk",
            "type": "calculate",
            "properties": {},
            "config": {
                "formula": "abs(price_binance - price_coinbase)"
            },
            "inputs": {
                "price_binance": "price_binance.price",
                "price_coinbase": "price_coinbase.price"
            },
            "outputs": ["spread", "spread_percent"],
            "timeout": 5.0
        },
        {
            "id": "check_threshold",
            "name": "Check Arbitrage Threshold",
            "category": "conditions",
            "type": "threshold",
            "properties": {},
            "config": {
                "threshold": 0.5,  # 0.5% spread
                "operator": "greater_than"
            },
            "inputs": {
                "value": "calculate_spread.spread_percent"
            },
            "outputs": ["is_profitable"],
            "timeout": 5.0
        },
        {
            "id": "execute_trade",
            "name": "Execute Arbitrage Trade",
            "category": "actions",
            "type": "trade",
            "properties": {},
            "config": {
                "amount": 0.01,  # BTC
                "max_slippage": 0.1
            },
            "inputs": {
                "should_execute": "check_threshold.is_profitable",
                "buy_exchange": "price_binance",
                "sell_exchange": "price_coinbase"
            },
            "outputs": ["trade_id", "status", "profit"],
            "timeout": 30.0
        }
    ]
}


class WorkflowEventMonitor:
    """Monitor and display workflow events in real-time"""

    def __init__(self):
        self.events = []
        self.start_time = datetime.utcnow()

    async def handle_event(self, event: dict):
        """Handle incoming workflow event"""
        self.events.append(event)
        event_type = event.get("type")
        timestamp = datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat()))
        elapsed = (timestamp - self.start_time).total_seconds()

        # Format event for display
        if event_type == "execution_started":
            print(f"\n{'='*70}")
            print(f"🚀 EXECUTION STARTED")
            print(f"{'='*70}")
            print(f"Workflow ID: {event.get('workflow_id')}")
            print(f"Execution ID: {event.get('execution_id')}")
            print(f"Bot ID: {event.get('bot_id')}")
            print(f"Strategy ID: {event.get('strategy_id')}")
            print(f"Nodes: {event.get('node_count')}")
            print(f"{'='*70}\n")

        elif event_type == "node_started":
            print(f"[{elapsed:6.2f}s] ▶️  Starting: {event.get('node_name')} ({event.get('node_id')})")

        elif event_type == "node_completed":
            duration_ms = event.get('duration_ms', 0)
            outputs = event.get('outputs', {})
            print(f"[{elapsed:6.2f}s] ✅ Completed: {event.get('node_name')} ({duration_ms:.0f}ms)")
            if outputs:
                print(f"           Outputs: {outputs}")

        elif event_type == "node_failed":
            error = event.get('error', 'Unknown error')
            error_type = event.get('error_type', 'Error')
            print(f"[{elapsed:6.2f}s] ❌ Failed: {event.get('node_name')}")
            print(f"           Error: {error_type}: {error}")

        elif event_type == "execution_completed":
            duration_ms = event.get('duration_ms', 0)
            status = event.get('status', 'unknown')
            print(f"\n{'='*70}")
            print(f"🏁 EXECUTION COMPLETED")
            print(f"{'='*70}")
            print(f"Status: {status}")
            print(f"Duration: {duration_ms:.2f}ms ({duration_ms/1000:.2f}s)")
            print(f"{'='*70}\n")

        elif event_type == "execution_failed":
            error = event.get('error', 'Unknown error')
            print(f"\n{'='*70}")
            print(f"💥 EXECUTION FAILED")
            print(f"{'='*70}")
            print(f"Error: {error}")
            print(f"{'='*70}\n")

        elif event_type == "execution_halted":
            reason = event.get('reason', 'Unknown reason')
            print(f"\n{'='*70}")
            print(f"🛑 EXECUTION HALTED")
            print(f"{'='*70}")
            print(f"Reason: {reason}")
            print(f"{'='*70}\n")

    def get_summary(self):
        """Get summary of all events"""
        event_counts = {}
        for event in self.events:
            event_type = event.get("type")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_events": len(self.events),
            "event_counts": event_counts,
            "events": self.events
        }


async def main():
    """Run real-time trading workflow example"""
    print("\n" + "="*70)
    print("Real-Time Trading Workflow Example")
    print("BTC Arbitrage: Binance vs Coinbase")
    print("="*70 + "\n")

    # Create infrastructure
    print("📦 Initializing infrastructure...")
    infra = await Infrastructure.create("development")
    print("✅ Infrastructure initialized\n")

    # Create event monitor
    monitor = WorkflowEventMonitor()

    # Subscribe to workflow events
    await infra.events.subscribe("workflow_events", monitor.handle_event)
    print("📡 Subscribed to workflow events\n")

    # Create enhanced workflow executor
    executor = EnhancedWorkflowExecutor(
        workflow=ARBITRAGE_WORKFLOW,
        infra=infra,
        workflow_id="btc_arbitrage_001",
        bot_id="arbitrage_bot_001",
        strategy_id="binance_coinbase_btc"
    )

    # Initialize executor
    print("🔧 Initializing workflow executor...")
    await executor.initialize()
    print("✅ Executor initialized\n")

    # Check emergency state
    emergency_status = infra.emergency.get_status()
    print(f"🚨 Emergency Status: {emergency_status['state']} (can_trade: {emergency_status['can_trade']})\n")

    # Execute workflow
    print("⚡ Executing workflow...\n")

    # Mock the provider nodes to return simulated data
    from unittest.mock import patch

    async def mock_binance_price(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate API latency
        return {
            "price": 50234.56,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def mock_coinbase_price(*args, **kwargs):
        await asyncio.sleep(0.15)  # Simulate API latency
        return {
            "price": 50189.23,
            "timestamp": datetime.utcnow().isoformat()
        }

    # Patch the base executor's provider node execution
    async def mock_provider(node, inputs):
        if node['id'] == 'price_binance':
            return await mock_binance_price()
        elif node['id'] == 'price_coinbase':
            return await mock_coinbase_price()
        return {}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=mock_provider
    ):
        try:
            result = await executor.execute()

            # Wait for events to be processed
            await asyncio.sleep(0.5)

            # Display results
            print("\n" + "="*70)
            print("📊 EXECUTION RESULTS")
            print("="*70)
            print(f"Status: {result['status']}")
            print(f"Duration: {result['duration']:.2f}ms")
            print(f"Nodes Executed: {len(result.get('results', []))}")
            print(f"Errors: {len(result.get('errors', []))}")
            print("="*70 + "\n")

            # Display node results
            if result.get('results'):
                print("Node Results:")
                for node_result in result['results']:
                    print(f"  - {node_result['nodeName']}: {node_result.get('output', {})}")
                print()

            # Display errors
            if result.get('errors'):
                print("Errors:")
                for error in result['errors']:
                    print(f"  - {error['nodeId']}: {error['error']}")
                print()

        except Exception as e:
            print(f"\n❌ Execution failed: {e}\n")
            import traceback
            traceback.print_exc()

    # Display event summary
    summary = monitor.get_summary()
    print("="*70)
    print("📈 EVENT SUMMARY")
    print("="*70)
    print(f"Total Events: {summary['total_events']}")
    print(f"Event Breakdown:")
    for event_type, count in summary['event_counts'].items():
        print(f"  - {event_type}: {count}")
    print("="*70 + "\n")

    # Display execution history
    history = await executor.get_execution_history()
    if history:
        print("="*70)
        print("📜 EXECUTION HISTORY")
        print("="*70)
        for execution in history:
            print(f"  - {execution['execution_id']}: {execution['status']}")
        print("="*70 + "\n")

    print("✅ Example completed successfully!\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ Example failed: {e}\n")
        import traceback
        traceback.print_exc()
