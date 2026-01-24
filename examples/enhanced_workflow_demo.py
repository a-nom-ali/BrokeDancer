"""
Enhanced Workflow Executor Demo

Demonstrates workflow execution with full infrastructure integration:
- Real-time event emission
- Correlation ID tracking
- Emergency controls
- State persistence
- Circuit breakers

Run with:
    python examples/enhanced_workflow_demo.py
"""

import asyncio
from src.infrastructure.factory import create_infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


# Simple workflow definition
DEMO_WORKFLOW = {
    'blocks': [
        {
            'id': 'provider_1',
            'name': 'Polymarket Price Feed',
            'category': 'providers',
            'type': 'polymarket',
            'properties': {
                'profile_id': 'polymarket_main',
                'enabled_endpoints': ['price_feed', 'balance']
            },
            'outputs': [
                {'name': 'price_feed', 'type': 'float'},
                {'name': 'balance', 'type': 'float'}
            ]
        },
        {
            'id': 'condition_1',
            'name': 'Price Threshold Check',
            'category': 'conditions',
            'type': 'threshold',
            'inputs': [
                {'name': 'value', 'type': 'float'},
                {'name': 'min', 'type': 'float'},
                {'name': 'max', 'type': 'float'}
            ],
            'outputs': [
                {'name': 'pass', 'type': 'boolean'}
            ]
        },
        {
            'id': 'action_1',
            'name': 'Buy Order',
            'category': 'actions',
            'type': 'buy',
            'inputs': [
                {'name': 'signal', 'type': 'boolean'},
                {'name': 'amount', 'type': 'float'}
            ],
            'outputs': [
                {'name': 'order', 'type': 'object'}
            ]
        }
    ],
    'connections': [
        {
            'from': {'blockId': 'provider_1', 'index': 0},  # price_feed
            'to': {'blockId': 'condition_1', 'index': 0}    # value
        },
        {
            'from': {'blockId': 'condition_1', 'index': 0},  # pass
            'to': {'blockId': 'action_1', 'index': 0}        # signal
        }
    ]
}


async def demo_basic_execution():
    """Demonstrate basic enhanced workflow execution."""
    print("\n=== Basic Enhanced Workflow Execution ===\n")

    # Create infrastructure
    infra = await create_infrastructure("development")

    # Subscribe to events
    events_received = []

    async def capture_event(event):
        events_received.append(event)
        event_type = event.get('type')
        node_id = event.get('node_id', 'N/A')
        print(f"  Event: {event_type:25s} | Node: {node_id}")

    await infra.events.subscribe("workflow_events", capture_event)

    # Create enhanced executor
    executor = EnhancedWorkflowExecutor(
        workflow=DEMO_WORKFLOW,
        infra=infra,
        workflow_id="demo_workflow_001",
        bot_id="bot_demo",
        strategy_id="demo_strategy"
    )

    # Initialize and execute
    await executor.initialize()

    print("Executing workflow...\n")
    result = await executor.execute()

    print(f"\nExecution completed!")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration']:.2f}ms")
    print(f"  Nodes executed: {len(result['results'])}")
    print(f"  Events emitted: {len(events_received)}")

    # Show event types
    event_types = {}
    for event in events_received:
        event_type = event['type']
        event_types[event_type] = event_types.get(event_type, 0) + 1

    print(f"\n  Event breakdown:")
    for event_type, count in event_types.items():
        print(f"    {event_type}: {count}")

    await infra.close()

    print("\n✓ Basic execution complete\n")


async def demo_emergency_halt():
    """Demonstrate emergency halt during workflow execution."""
    print("\n=== Emergency Halt Demo ===\n")

    # Create infrastructure
    infra = await create_infrastructure("development")

    # Create executor
    executor = EnhancedWorkflowExecutor(
        workflow=DEMO_WORKFLOW,
        infra=infra,
        workflow_id="demo_workflow_002",
        bot_id="bot_demo"
    )

    await executor.initialize()

    # Trigger emergency halt
    print("Triggering emergency halt...")
    await infra.emergency.halt("Demo emergency halt")

    # Try to execute workflow
    print("Attempting to execute workflow...\n")
    try:
        await executor.execute()
        print("  ✗ Workflow executed (should have been halted!)")
    except Exception as e:
        print(f"  ✓ Workflow halted: {type(e).__name__}")
        print(f"  Reason: {str(e)}")

    # Resume and try again
    print("\nResuming operations...")
    await infra.emergency.resume("Demo resume")

    print("Executing workflow again...\n")
    result = await executor.execute()
    print(f"  ✓ Workflow executed successfully")
    print(f"  Status: {result['status']}")

    await infra.close()

    print("\n✓ Emergency halt demo complete\n")


async def demo_state_persistence():
    """Demonstrate workflow state persistence."""
    print("\n=== State Persistence Demo ===\n")

    # Create infrastructure
    infra = await create_infrastructure("development")

    # Create and execute workflow
    executor = EnhancedWorkflowExecutor(
        workflow=DEMO_WORKFLOW,
        infra=infra,
        workflow_id="demo_workflow_003",
        bot_id="bot_demo"
    )

    await executor.initialize()

    print("Executing workflow...")
    result = await executor.execute()

    execution_id = executor.execution_id
    print(f"  Execution ID: {execution_id}")
    print(f"  Status: {result['status']}")

    # Retrieve persisted state
    print("\nRetrieving persisted state...")
    status = await infra.state.get(
        f"workflow:demo_workflow_003:execution:{execution_id}:status"
    )
    print(f"  Persisted status: {status}")

    result_data = await infra.state.get(
        f"workflow:demo_workflow_003:execution:{execution_id}:result"
    )
    print(f"  Persisted result: {result_data is not None}")

    # Get execution history
    print("\nExecution history:")
    history = await executor.get_execution_history()
    for item in history:
        print(f"  - {item['execution_id']}: {item['status']}")

    await infra.close()

    print("\n✓ State persistence demo complete\n")


async def demo_correlation_id_tracking():
    """Demonstrate correlation ID tracking across logs."""
    print("\n=== Correlation ID Tracking Demo ===\n")

    # Create infrastructure with console logging
    infra = await create_infrastructure("development")

    # Create executor
    executor = EnhancedWorkflowExecutor(
        workflow=DEMO_WORKFLOW,
        infra=infra,
        workflow_id="demo_workflow_004",
        bot_id="bot_demo"
    )

    await executor.initialize()

    print("Executing workflow with correlation ID tracking...")
    print("(Check logs - all entries will have the same correlation_id)\n")

    result = await executor.execute()

    print(f"Execution ID: {executor.execution_id}")
    print(f"Status: {result['status']}")
    print("\nAll log entries above share the same correlation_id")
    print("This enables tracing a single execution across all components!")

    await infra.close()

    print("\n✓ Correlation ID tracking demo complete\n")


async def demo_concurrent_workflows():
    """Demonstrate multiple concurrent workflows with isolated correlation IDs."""
    print("\n=== Concurrent Workflows Demo ===\n")

    # Create infrastructure
    infra = await create_infrastructure("development")

    async def run_workflow(workflow_id: str, delay: float):
        """Run a workflow with a delay."""
        executor = EnhancedWorkflowExecutor(
            workflow=DEMO_WORKFLOW,
            infra=infra,
            workflow_id=workflow_id,
            bot_id="bot_demo"
        )

        await executor.initialize()
        await asyncio.sleep(delay)

        result = await executor.execute()

        print(f"  Workflow {workflow_id}: {result['status']}")

        return executor.execution_id

    print("Running 3 workflows concurrently...\n")

    # Run workflows concurrently
    execution_ids = await asyncio.gather(
        run_workflow("concurrent_001", 0.1),
        run_workflow("concurrent_002", 0.15),
        run_workflow("concurrent_003", 0.12)
    )

    print(f"\nAll workflows completed!")
    print(f"Each workflow has its own correlation ID:")
    for wf_id, exec_id in zip(
        ["concurrent_001", "concurrent_002", "concurrent_003"],
        execution_ids
    ):
        print(f"  {wf_id}: {exec_id}")

    await infra.close()

    print("\n✓ Concurrent workflows demo complete\n")


async def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("Enhanced Workflow Executor Demo")
    print("="*60)

    await demo_basic_execution()
    await demo_emergency_halt()
    await demo_state_persistence()
    await demo_correlation_id_tracking()
    await demo_concurrent_workflows()

    print("="*60)
    print("All Demos Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
