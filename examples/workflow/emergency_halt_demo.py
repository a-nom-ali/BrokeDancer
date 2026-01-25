"""
Emergency Halt Scenario Demonstration

Demonstrates emergency halt and risk limit features:
1. Daily loss limit exceeded - auto-halt
2. Manual emergency halt
3. Resume from halt
4. Emergency event subscriptions

This example shows how the system protects trading capital by automatically
halting operations when risk limits are exceeded.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from src.infrastructure.emergency import EmergencyHalted, RiskLimitExceeded, EmergencyEvent


# Simple trading workflow
TRADING_WORKFLOW = {
    "blocks": [
        {
            "id": "check_market",
            "name": "Market Check",
            "category": "providers",
            "type": "market_data",
            "properties": {},
            "config": {},
            "inputs": {},
            "outputs": ["price"],
            "timeout": 10.0
        },
        {
            "id": "execute_trade",
            "name": "Execute Trade",
            "category": "actions",
            "type": "trade",
            "properties": {},
            "config": {},
            "inputs": {
                "price": "check_market.price"
            },
            "outputs": ["trade_id"],
            "timeout": 30.0
        }
    ]
}


async def demo_daily_loss_limit():
    """Demonstrate daily loss limit exceeded - auto-halt"""
    print("\n" + "="*70)
    print("DEMO 1: Daily Loss Limit Exceeded")
    print("="*70 + "\n")

    infra = await Infrastructure.create("development")

    # Get default daily loss limit from config
    daily_loss_limit = infra.config.emergency.daily_loss_limit
    print(f"💰 Daily Loss Limit: ${abs(daily_loss_limit):.2f}\n")

    # Simulate daily PnL tracking
    daily_pnl = -250.0  # Lost $250
    print(f"📉 Current Daily P&L: ${daily_pnl:.2f}")
    print(f"   Utilization: {abs(daily_pnl / daily_loss_limit) * 100:.1f}%\n")

    # Check risk limit - should warn but not halt (under 80%)
    try:
        await infra.emergency.check_risk_limit(
            "daily_loss",
            daily_pnl,
            daily_loss_limit,
            auto_halt=True
        )
        print("✅ Risk limit check passed (under threshold)\n")
    except RiskLimitExceeded:
        print("❌ Unexpected halt at this level\n")

    # Now simulate exceeding the limit
    daily_pnl = -550.0  # Lost $550 - exceeds $500 limit
    print(f"📉 Updated Daily P&L: ${daily_pnl:.2f}")
    print(f"   Utilization: {abs(daily_pnl / daily_loss_limit) * 100:.1f}%\n")

    # Check risk limit - should halt
    try:
        await infra.emergency.check_risk_limit(
            "daily_loss",
            daily_pnl,
            daily_loss_limit,
            auto_halt=True
        )
        print("❌ Risk limit should have been exceeded\n")
    except RiskLimitExceeded as e:
        print(f"🛑 RISK LIMIT EXCEEDED!")
        print(f"   Limit Type: {e.limit_type}")
        print(f"   Current: ${e.current:.2f}")
        print(f"   Limit: ${e.limit:.2f}")
        print(f"   Emergency State: {infra.emergency.state.value}\n")

    # Try to execute workflow - should be halted
    print("🔧 Attempting to execute trading workflow...\n")

    executor = EnhancedWorkflowExecutor(
        workflow=TRADING_WORKFLOW,
        infra=infra,
        workflow_id="trade_after_limit",
        bot_id="bot_demo",
        strategy_id="demo_strategy"
    )

    await executor.initialize()

    try:
        result = await executor.execute()
        print("❌ Should not have executed\n")
    except EmergencyHalted as e:
        print(f"✅ EXECUTION BLOCKED BY EMERGENCY HALT")
        print(f"   State: {e.state.value}")
        print(f"   Reason: {e.reason}\n")

    # Check emergency status
    status = infra.emergency.get_status()
    print("="*70)
    print("Emergency Controller Status:")
    print(f"  State: {status['state']}")
    print(f"  Can Trade: {status['can_trade']}")
    print(f"  Can Operate: {status['can_operate']}")
    print(f"  Halt Reason: {status['halt_reason']}")
    if status['risk_limits']:
        print(f"  Risk Limits:")
        for name, data in status['risk_limits'].items():
            print(f"    - {name}: {data['current']:.2f} / {data['limit']:.2f} ({data['utilization']*100:.1f}%)")
    print("="*70 + "\n")


async def demo_manual_halt_resume():
    """Demonstrate manual emergency halt and resume"""
    print("\n" + "="*70)
    print("DEMO 2: Manual Emergency Halt and Resume")
    print("="*70 + "\n")

    infra = await Infrastructure.create("development")

    # Subscribe to emergency events
    emergency_events = []

    async def on_emergency_event(event: EmergencyEvent):
        emergency_events.append(event)
        print(f"🚨 EMERGENCY EVENT RECEIVED")
        print(f"   Previous State: {event.previous_state.value}")
        print(f"   New State: {event.new_state.value}")
        print(f"   Reason: {event.reason}")
        print(f"   Timestamp: {event.timestamp.isoformat()}\n")

    await infra.emergency.subscribe(on_emergency_event)
    print("📡 Subscribed to emergency events\n")

    # Check initial state
    print(f"Initial State: {infra.emergency.state.value}")
    print(f"Can Trade: {infra.emergency.can_trade()}\n")

    # Manual emergency halt
    print("🛑 Triggering manual emergency halt...\n")
    await infra.emergency.halt("User-initiated emergency stop - suspicious market activity")

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Try to execute workflow
    print("🔧 Attempting to execute workflow during halt...\n")

    executor = EnhancedWorkflowExecutor(
        workflow=TRADING_WORKFLOW,
        infra=infra,
        workflow_id="trade_during_halt",
        bot_id="bot_demo",
        strategy_id="demo_strategy"
    )

    await executor.initialize()

    try:
        result = await executor.execute()
        print("❌ Should not have executed during halt\n")
    except EmergencyHalted as e:
        print(f"✅ EXECUTION BLOCKED")
        print(f"   Reason: {e.reason}\n")

    # Resume operations
    print("✅ Resuming normal operations...\n")
    await infra.emergency.resume("Market conditions normalized - resuming trading")

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Try to execute workflow again
    print("🔧 Attempting to execute workflow after resume...\n")

    from unittest.mock import patch

    async def mock_market_data(*args, **kwargs):
        return {"price": 50000.0}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=mock_market_data
    ):
        try:
            result = await executor.execute()
            print(f"✅ EXECUTION SUCCEEDED")
            print(f"   Status: {result['status']}")
            print(f"   Duration: {result['duration']:.2f}ms\n")
        except EmergencyHalted as e:
            print(f"❌ Should have been able to execute: {e}\n")

    # Display all emergency events
    print("="*70)
    print(f"Emergency Events Received: {len(emergency_events)}")
    for i, event in enumerate(emergency_events, 1):
        print(f"\n  Event {i}:")
        print(f"    Controller: {event.controller_id}")
        print(f"    Transition: {event.previous_state.value} → {event.new_state.value}")
        print(f"    Reason: {event.reason}")
    print("="*70 + "\n")


async def demo_alert_state():
    """Demonstrate alert state (trading continues with caution)"""
    print("\n" + "="*70)
    print("DEMO 3: Alert State (Cautious Trading)")
    print("="*70 + "\n")

    infra = await Infrastructure.create("development")

    print(f"Initial State: {infra.emergency.state.value}")
    print(f"Can Trade: {infra.emergency.can_trade()}\n")

    # Set alert state
    print("⚠️  Setting alert state...\n")
    await infra.emergency.alert(
        "High volatility detected - trading with increased caution",
        volatility_index=85.5,
        recommendation="reduce_position_sizes"
    )

    await asyncio.sleep(0.1)

    # Check state
    print(f"Current State: {infra.emergency.state.value}")
    print(f"Can Trade: {infra.emergency.can_trade()}")
    print(f"Can Operate: {infra.emergency.can_operate()}\n")

    # Execute workflow - should succeed
    print("🔧 Executing workflow in alert state...\n")

    executor = EnhancedWorkflowExecutor(
        workflow=TRADING_WORKFLOW,
        infra=infra,
        workflow_id="trade_in_alert",
        bot_id="bot_demo",
        strategy_id="demo_strategy"
    )

    await executor.initialize()

    from unittest.mock import patch

    async def mock_market_data(*args, **kwargs):
        return {"price": 50000.0}

    with patch.object(
        executor.__class__.__bases__[0],
        '_execute_provider_node',
        side_effect=mock_market_data
    ):
        try:
            result = await executor.execute()
            print(f"✅ EXECUTION SUCCEEDED IN ALERT STATE")
            print(f"   Status: {result['status']}")
            print(f"   Duration: {result['duration']:.2f}ms")
            print(f"   Note: Trading continues but with increased caution\n")
        except EmergencyHalted as e:
            print(f"❌ Unexpected halt: {e}\n")

    # Get status
    status = infra.emergency.get_status()
    print("="*70)
    print("Emergency Controller Status:")
    print(f"  State: {status['state']}")
    print(f"  Can Trade: {status['can_trade']}")
    print(f"  Can Operate: {status['can_operate']}")
    if status['metadata']:
        print(f"  Metadata: {status['metadata']}")
    print("="*70 + "\n")


async def main():
    """Run all emergency halt demonstrations"""
    print("\n" + "="*70)
    print("Emergency Halt & Risk Limit Demonstrations")
    print("="*70)

    try:
        # Demo 1: Daily loss limit
        await demo_daily_loss_limit()

        # Demo 2: Manual halt and resume
        await demo_manual_halt_resume()

        # Demo 3: Alert state
        await demo_alert_state()

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
