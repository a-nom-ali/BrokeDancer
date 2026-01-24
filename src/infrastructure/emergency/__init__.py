"""
Emergency Controls

Provides emergency stop and control mechanisms for trading bots.

Features:
- Emergency halt system (NORMAL/ALERT/HALT/SHUTDOWN)
- Risk limit monitoring
- Manual override controls
- State persistence across restarts
- Event notifications

Usage:
    # Create emergency controller
    from src.infrastructure.emergency import EmergencyController

    controller = EmergencyController("bot_001")

    # Check state before operations
    if controller.can_trade():
        await execute_trade()

    # Trigger emergency halt
    await controller.halt("Daily loss limit exceeded")

    # Resume after investigation
    await controller.resume()

    # Subscribe to state changes
    async def on_halt(event):
        logger.critical("Emergency halt triggered", reason=event['reason'])

    await controller.subscribe(on_halt)
"""

from .controller import (
    EmergencyController,
    EmergencyState,
    EmergencyEvent,
    EmergencyHalted,
    RiskLimitExceeded
)

__all__ = [
    "EmergencyController",
    "EmergencyState",
    "EmergencyEvent",
    "EmergencyHalted",
    "RiskLimitExceeded",
]
