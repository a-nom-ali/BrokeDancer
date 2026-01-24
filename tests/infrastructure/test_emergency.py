"""
Tests for Emergency Controller

Tests emergency halt functionality and risk limit monitoring.
"""

import pytest
import asyncio
from src.infrastructure.emergency import (
    EmergencyController,
    EmergencyState,
    EmergencyEvent,
    EmergencyHalted,
    RiskLimitExceeded
)
from src.infrastructure.state import create_state_store


@pytest.mark.asyncio
async def test_emergency_controller_initial_state():
    """Test emergency controller initial state"""
    controller = EmergencyController("test_bot")

    assert controller.state == EmergencyState.NORMAL
    assert controller.is_normal
    assert controller.can_trade()
    assert controller.can_operate()


@pytest.mark.asyncio
async def test_emergency_halt():
    """Test emergency halt"""
    controller = EmergencyController("test_bot")

    # Trigger halt
    await controller.halt("Manual emergency stop")

    assert controller.state == EmergencyState.HALT
    assert controller.is_halted
    assert not controller.can_trade()
    assert controller.can_operate()  # Can still operate, just not trade


@pytest.mark.asyncio
async def test_emergency_shutdown():
    """Test emergency shutdown"""
    controller = EmergencyController("test_bot")

    # Trigger shutdown
    await controller.shutdown("Critical system failure")

    assert controller.state == EmergencyState.SHUTDOWN
    assert controller.is_shutdown
    assert not controller.can_trade()
    assert not controller.can_operate()


@pytest.mark.asyncio
async def test_emergency_alert():
    """Test alert state"""
    controller = EmergencyController("test_bot")

    # Set alert
    await controller.alert("High API latency detected")

    assert controller.state == EmergencyState.ALERT
    assert controller.is_alert
    assert controller.can_trade()  # Can still trade in alert
    assert controller.can_operate()


@pytest.mark.asyncio
async def test_emergency_resume():
    """Test resuming from halt"""
    controller = EmergencyController("test_bot")

    # Halt then resume
    await controller.halt("Manual stop")
    assert controller.is_halted

    await controller.resume("Investigation complete")
    assert controller.is_normal
    assert controller.can_trade()


@pytest.mark.asyncio
async def test_assert_can_trade():
    """Test assert_can_trade raises when halted"""
    controller = EmergencyController("test_bot")

    # Should not raise in normal state
    await controller.assert_can_trade()

    # Halt
    await controller.halt("Test halt")

    # Should raise
    with pytest.raises(EmergencyHalted) as exc_info:
        await controller.assert_can_trade()

    assert exc_info.value.state == EmergencyState.HALT


@pytest.mark.asyncio
async def test_assert_can_operate():
    """Test assert_can_operate raises when shutdown"""
    controller = EmergencyController("test_bot")

    # Should not raise in normal state
    await controller.assert_can_operate()

    # Shutdown
    await controller.shutdown("Test shutdown")

    # Should raise
    with pytest.raises(EmergencyHalted) as exc_info:
        await controller.assert_can_operate()

    assert exc_info.value.state == EmergencyState.SHUTDOWN


@pytest.mark.asyncio
async def test_risk_limit_check_pass():
    """Test risk limit check when within limits"""
    controller = EmergencyController("test_bot")

    # Within limit (should not raise)
    await controller.check_risk_limit(
        "daily_loss",
        -250.0,  # Current loss
        -500.0,  # Limit
        auto_halt=False
    )

    # Should still be in normal state
    assert controller.is_normal


@pytest.mark.asyncio
async def test_risk_limit_check_exceeded():
    """Test risk limit check when exceeded"""
    controller = EmergencyController("test_bot")

    # Exceed limit
    with pytest.raises(RiskLimitExceeded) as exc_info:
        await controller.check_risk_limit(
            "daily_loss",
            -600.0,  # Current loss (exceeded)
            -500.0,  # Limit
            auto_halt=False
        )

    assert exc_info.value.limit_type == "daily_loss"
    assert exc_info.value.current == -600.0
    assert exc_info.value.limit == -500.0


@pytest.mark.asyncio
async def test_risk_limit_auto_halt():
    """Test automatic halt when risk limit exceeded"""
    controller = EmergencyController("test_bot")

    # Exceed limit with auto-halt enabled
    with pytest.raises(RiskLimitExceeded):
        await controller.check_risk_limit(
            "daily_loss",
            -600.0,  # Current loss (exceeded)
            -500.0,  # Limit
            auto_halt=True  # Should auto-halt
        )

    # Should be halted now
    assert controller.is_halted


@pytest.mark.asyncio
async def test_event_subscription():
    """Test subscribing to state change events"""
    controller = EmergencyController("test_bot")

    events_received = []

    async def event_handler(event: EmergencyEvent):
        events_received.append(event)

    # Subscribe
    await controller.subscribe(event_handler)

    # Trigger state change
    await controller.halt("Test halt")

    # Wait for event
    await asyncio.sleep(0.01)

    # Check event received
    assert len(events_received) == 1
    event = events_received[0]
    assert event.controller_id == "test_bot"
    assert event.previous_state == EmergencyState.NORMAL
    assert event.new_state == EmergencyState.HALT
    assert event.reason == "Test halt"


@pytest.mark.asyncio
async def test_event_unsubscribe():
    """Test unsubscribing from events"""
    controller = EmergencyController("test_bot")

    events_received = []

    async def event_handler(event: EmergencyEvent):
        events_received.append(event)

    # Subscribe then unsubscribe
    await controller.subscribe(event_handler)
    await controller.unsubscribe(event_handler)

    # Trigger state change
    await controller.halt("Test halt")

    await asyncio.sleep(0.01)

    # Should not receive event
    assert len(events_received) == 0


@pytest.mark.asyncio
async def test_get_status():
    """Test getting controller status"""
    controller = EmergencyController("test_bot")

    # Add some risk limits
    await controller.check_risk_limit(
        "daily_loss",
        -250.0,
        -500.0,
        auto_halt=False
    )

    # Get status
    status = controller.get_status()

    assert status["controller_id"] == "test_bot"
    assert status["state"] == "normal"
    assert status["can_trade"] is True
    assert status["can_operate"] is True
    assert "daily_loss" in status["risk_limits"]


@pytest.mark.asyncio
async def test_persist_and_restore_state():
    """Test persisting and restoring controller state"""
    # Create state store
    state_store = create_state_store("memory")

    # Create controller and set state
    controller1 = EmergencyController("test_bot")
    await controller1.halt("Test halt reason")
    await controller1.check_risk_limit("daily_loss", -250.0, -500.0, auto_halt=False)

    # Persist state
    await controller1.persist_state(state_store)

    # Create new controller and restore
    controller2 = EmergencyController("test_bot")
    restored = await controller2.restore_state(state_store)

    assert restored is True
    assert controller2.state == EmergencyState.HALT
    assert controller2._halt_reason == "Test halt reason"
    assert "daily_loss" in controller2._risk_limits


@pytest.mark.asyncio
async def test_no_state_to_restore():
    """Test restoring when no saved state"""
    state_store = create_state_store("memory")

    controller = EmergencyController("test_bot")
    restored = await controller.restore_state(state_store)

    assert restored is False
    assert controller.is_normal  # Should remain in initial state


@pytest.mark.asyncio
async def test_multiple_risk_limits():
    """Test tracking multiple risk limits"""
    controller = EmergencyController("test_bot")

    # Check multiple limits
    await controller.check_risk_limit(
        "daily_loss",
        -250.0,
        -500.0,
        auto_halt=False
    )

    await controller.check_risk_limit(
        "position_size",
        5000.0,
        10000.0,
        auto_halt=False
    )

    # Get status
    status = controller.get_status()

    assert "daily_loss" in status["risk_limits"]
    assert "position_size" in status["risk_limits"]
    assert status["risk_limits"]["daily_loss"]["current"] == -250.0
    assert status["risk_limits"]["position_size"]["current"] == 5000.0


@pytest.mark.asyncio
async def test_state_change_metadata():
    """Test passing metadata with state changes"""
    controller = EmergencyController("test_bot")

    events_received = []

    async def event_handler(event: EmergencyEvent):
        events_received.append(event)

    await controller.subscribe(event_handler)

    # Halt with metadata
    await controller.halt(
        "Loss limit exceeded",
        current_loss=-520.0,
        limit=-500.0,
        triggered_by="automatic"
    )

    await asyncio.sleep(0.01)

    # Check metadata
    event = events_received[0]
    assert event.metadata["current_loss"] == -520.0
    assert event.metadata["limit"] == -500.0
    assert event.metadata["triggered_by"] == "automatic"
