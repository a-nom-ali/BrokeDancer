"""
Multi-Workflow Concurrency Example

Demonstrates running multiple workflows concurrently with shared infrastructure:
- Multiple bot instances running simultaneously
- Shared event bus for all workflow events
- Shared emergency controller
- Concurrent execution with asyncio.gather
- Event tracking across all workflows
- Performance metrics

This example shows how the system handles concurrent trading workflows
across different strategies and market pairs.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor


# Simple workflow template
def create_workflow(pair: str):
    """Create a workflow for a given trading pair"""
    return {
        "blocks": [
            {
                "id": f"price_{pair.lower()}",
                "name": f"{pair} Price Feed",
                "category": "providers",
                "type": "price_feed",
                "properties": {},
                "config": {"pair": pair},
                "inputs": {},
                "outputs": ["price"],
                "timeout": 10.0
            },
            {
                "id": f"check_{pair.lower()}",
                "name": f"{pair} Opportunity Check",
                "category": "conditions",
                "type": "opportunity",
                "properties": {},
                "config": {},
                "inputs": {
                    "price": f"price_{pair.lower()}.price"
                },
                "outputs": ["is_profitable"],
                "timeout": 5.0
            },
            {
                "id": f"trade_{pair.lower()}",
                "name": f"{pair} Trade Execution",
                "category": "actions",
                "type": "trade",
                "properties": {},
                "config": {},
                "inputs": {
                    "should_trade": f"check_{pair.lower()}.is_profitable"
                },
                "outputs": ["trade_id"],
                "timeout": 30.0
            }
        ]
    }


class ConcurrencyMonitor:
    """Monitor multiple concurrent workflows"""

    def __init__(self):
        self.events_by_workflow = {}
        self.start_time = time.time()

    async def handle_event(self, event: dict):
        """Handle workflow event"""
        workflow_id = event.get("workflow_id")
        if workflow_id not in self.events_by_workflow:
            self.events_by_workflow[workflow_id] = []
        self.events_by_workflow[workflow_id].append(event)

    def get_summary(self):
        """Get summary of all workflows"""
        summary = {
            "total_workflows": len(self.events_by_workflow),
            "total_events": sum(len(events) for events in self.events_by_workflow.values()),
            "workflows": {}
        }

        for workflow_id, events in self.events_by_workflow.items():
            started = next((e for e in events if e["type"] == "execution_started"), None)
            completed = next((e for e in events if e["type"] == "execution_completed"), None)

            summary["workflows"][workflow_id] = {
                "events": len(events),
                "status": completed.get("status") if completed else "running",
                "duration_ms": completed.get("duration_ms") if completed else None,
                "bot_id": started.get("bot_id") if started else None,
                "strategy_id": started.get("strategy_id") if started else None
            }

        return summary


async def execute_workflow(
    infra: Infrastructure,
    workflow_id: str,
    bot_id: str,
    strategy_id: str,
    pair: str,
    delay: float = 0.0
):
    """Execute a single workflow"""
    # Optional delay for staggered starts
    if delay > 0:
        await asyncio.sleep(delay)

    # Create workflow
    workflow = create_workflow(pair)

    # Create executor
    executor = EnhancedWorkflowExecutor(
        workflow=workflow,
        infra=infra,
        workflow_id=workflow_id,
        bot_id=bot_id,
        strategy_id=strategy_id
    )

    # Initialize
    await executor.initialize()

    # Mock provider data
    from unittest.mock import patch

    price_map = {
        "BTC/USD": 50234.56,
        "ETH/USD": 3456.78,
        "SOL/USD": 123.45,
        "MATIC/USD": 0.89,
        "AVAX/USD": 45.67
    }

    async def mock_price_feed(*args, **kwargs):
        await asyncio.sleep(0.05 + (hash(pair) % 10) / 100)  # Variable latency
        return {"price": price_map.get(pair, 1.0)}

    # Execute with mocked data
    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=mock_price_feed
    ):
        result = await executor.execute()

    return {
        "workflow_id": workflow_id,
        "bot_id": bot_id,
        "strategy_id": strategy_id,
        "pair": pair,
        "result": result
    }


async def demo_concurrent_execution():
    """Demonstrate concurrent workflow execution"""
    print("\n" + "="*70)
    print("DEMO: Concurrent Workflow Execution")
    print("="*70 + "\n")

    # Create shared infrastructure
    print("📦 Initializing shared infrastructure...")
    infra = await Infrastructure.create("development")
    print("✅ Infrastructure initialized\n")

    # Create monitor
    monitor = ConcurrencyMonitor()
    await infra.events.subscribe("workflow_events", monitor.handle_event)
    print("📡 Event monitor subscribed\n")

    # Define workflows to execute
    workflows = [
        ("btc_arb_001", "bot_btc_001", "strategy_btc_arb", "BTC/USD", 0.0),
        ("eth_arb_001", "bot_eth_001", "strategy_eth_arb", "ETH/USD", 0.1),
        ("sol_arb_001", "bot_sol_001", "strategy_sol_arb", "SOL/USD", 0.2),
        ("matic_arb_001", "bot_matic_001", "strategy_matic_arb", "MATIC/USD", 0.3),
        ("avax_arb_001", "bot_avax_001", "strategy_avax_arb", "AVAX/USD", 0.4),
    ]

    print(f"🚀 Launching {len(workflows)} concurrent workflows...\n")
    print("Trading Pairs:")
    for _, _, _, pair, delay in workflows:
        print(f"  - {pair} (delay: {delay}s)")
    print()

    # Execute all workflows concurrently
    start_time = time.time()

    tasks = [
        execute_workflow(infra, wf_id, bot_id, strategy_id, pair, delay)
        for wf_id, bot_id, strategy_id, pair, delay in workflows
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    total_duration = end_time - start_time

    # Wait for events to be processed
    await asyncio.sleep(0.5)

    # Display results
    print("\n" + "="*70)
    print("📊 EXECUTION RESULTS")
    print("="*70 + "\n")

    successful = 0
    failed = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Workflow {i+1}: FAILED - {result}")
            failed += 1
        else:
            status = result["result"]["status"]
            duration = result["result"]["duration"]
            print(f"✅ {result['pair']}: {status} ({duration:.2f}ms)")
            successful += 1

    print(f"\nSummary:")
    print(f"  Total: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total Time: {total_duration:.2f}s")
    print(f"  Avg Time per Workflow: {total_duration/len(results):.2f}s")
    print()

    # Display event summary
    summary = monitor.get_summary()
    print("="*70)
    print("📈 EVENT SUMMARY")
    print("="*70)
    print(f"Total Workflows: {summary['total_workflows']}")
    print(f"Total Events: {summary['total_events']}")
    print(f"\nPer-Workflow Breakdown:")
    for wf_id, wf_data in summary['workflows'].items():
        print(f"\n  {wf_id}:")
        print(f"    Bot: {wf_data['bot_id']}")
        print(f"    Strategy: {wf_data['strategy_id']}")
        print(f"    Events: {wf_data['events']}")
        print(f"    Status: {wf_data['status']}")
        if wf_data['duration_ms']:
            print(f"    Duration: {wf_data['duration_ms']:.2f}ms")
    print("="*70 + "\n")


async def demo_shared_emergency_control():
    """Demonstrate shared emergency controller across workflows"""
    print("\n" + "="*70)
    print("DEMO: Shared Emergency Controller")
    print("="*70 + "\n")

    # Create shared infrastructure
    print("📦 Initializing shared infrastructure...")
    infra = await Infrastructure.create("development")
    print("✅ Infrastructure initialized\n")

    # Define workflows
    workflows_to_run = [
        ("wf1", "bot_1", "strategy_1", "BTC/USD"),
        ("wf2", "bot_2", "strategy_2", "ETH/USD"),
        ("wf3", "bot_3", "strategy_3", "SOL/USD"),
    ]

    # Start workflows concurrently
    print(f"🚀 Starting {len(workflows_to_run)} workflows...\n")

    async def run_with_emergency_check(wf_id, bot_id, strategy_id, pair):
        try:
            # Add a small delay to simulate staggered execution
            await asyncio.sleep(0.1)

            result = await execute_workflow(infra, wf_id, bot_id, strategy_id, pair)
            return result
        except Exception as e:
            return {"workflow_id": wf_id, "error": str(e)}

    # Start workflows
    task1 = asyncio.create_task(run_with_emergency_check(*workflows_to_run[0]))
    task2 = asyncio.create_task(run_with_emergency_check(*workflows_to_run[1]))
    task3 = asyncio.create_task(run_with_emergency_check(*workflows_to_run[2]))

    # Let them start
    await asyncio.sleep(0.2)

    # Trigger emergency halt
    print("🛑 TRIGGERING EMERGENCY HALT...\n")
    await infra.emergency.halt("Shared emergency halt - affects all workflows")

    # Wait for completion
    await asyncio.sleep(0.5)

    results = await asyncio.gather(task1, task2, task3, return_exceptions=True)

    # Check results
    print("="*70)
    print("📊 RESULTS AFTER EMERGENCY HALT")
    print("="*70 + "\n")

    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Workflow errored: {result}")
        elif "error" in result:
            print(f"❌ {result['workflow_id']}: {result['error']}")
        else:
            print(f"✅ {result['workflow_id']}: {result['result']['status']}")

    print("\n" + "="*70)
    print("Note: Workflows started before halt completed successfully.")
    print("Workflows starting after halt were blocked by emergency controller.")
    print("="*70 + "\n")


async def main():
    """Run all concurrency demonstrations"""
    print("\n" + "="*70)
    print("Multi-Workflow Concurrency Demonstrations")
    print("="*70)

    try:
        # Demo 1: Concurrent execution
        await demo_concurrent_execution()

        # Demo 2: Shared emergency control
        await demo_shared_emergency_control()

        print("\n" + "="*70)
        print("✅ All Demonstrations Completed Successfully")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}\n")
        import traceback
        traceback.print_exc()
