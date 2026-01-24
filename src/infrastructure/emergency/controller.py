"""
Emergency Controller

Provides emergency halt and control mechanisms for trading bots.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Awaitable, Dict, Any
import asyncio
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EmergencyState(Enum):
    """Emergency controller states"""
    NORMAL = "normal"          # Normal operation
    ALERT = "alert"            # Warning state, continue with caution
    HALT = "halt"              # Emergency halt, no new trades
    SHUTDOWN = "shutdown"      # Complete shutdown, cease all operations


class EmergencyHalted(Exception):
    """Raised when attempting operations during emergency halt"""

    def __init__(self, state: EmergencyState, reason: str):
        self.state = state
        self.reason = reason
        super().__init__(
            f"Emergency controller is in {state.value} state. Reason: {reason}"
        )


class RiskLimitExceeded(Exception):
    """Raised when a risk limit is exceeded"""

    def __init__(self, limit_type: str, current: float, limit: float):
        self.limit_type = limit_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Risk limit exceeded: {limit_type} - current: {current}, limit: {limit}"
        )


@dataclass
class EmergencyEvent:
    """Emergency state change event"""
    controller_id: str
    previous_state: EmergencyState
    new_state: EmergencyState
    reason: str
    timestamp: datetime
    metadata: Dict[str, Any]


EventHandler = Callable[[EmergencyEvent], Awaitable[None]]


class EmergencyController:
    """
    Emergency controller for trading bots.

    Provides emergency halt functionality and risk limit monitoring.

    States:
    - NORMAL: Normal operation, all systems go
    - ALERT: Warning state, operations continue with caution
    - HALT: Emergency halt, no new trades allowed
    - SHUTDOWN: Complete shutdown, cease all operations

    Usage:
        # Create controller
        controller = EmergencyController("bot_001")

        # Check before trading
        if controller.can_trade():
            await execute_trade()

        # Monitor risk limits
        await controller.check_risk_limit("daily_loss", -450.0, -500.0)

        # Emergency halt
        await controller.halt("Manual emergency stop")

        # Resume
        await controller.resume()

        # Subscribe to events
        async def on_state_change(event: EmergencyEvent):
            logger.critical("State changed", event=event)

        await controller.subscribe(on_state_change)
    """

    def __init__(
        self,
        controller_id: str,
        initial_state: EmergencyState = EmergencyState.NORMAL
    ):
        """
        Initialize emergency controller.

        Args:
            controller_id: Unique identifier for this controller
            initial_state: Initial state (default: NORMAL)
        """
        self.controller_id = controller_id
        self._state = initial_state
        self._halt_reason: Optional[str] = None
        self._halt_timestamp: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._handlers: list[EventHandler] = []

        # Risk limits tracking
        self._risk_limits: Dict[str, tuple[float, float]] = {}  # name -> (current, limit)

        logger.info(
            "emergency_controller_created",
            controller_id=controller_id,
            initial_state=initial_state.value
        )

    @property
    def state(self) -> EmergencyState:
        """Get current state"""
        return self._state

    @property
    def is_normal(self) -> bool:
        """Check if in normal state"""
        return self._state == EmergencyState.NORMAL

    @property
    def is_alert(self) -> bool:
        """Check if in alert state"""
        return self._state == EmergencyState.ALERT

    @property
    def is_halted(self) -> bool:
        """Check if halted"""
        return self._state == EmergencyState.HALT

    @property
    def is_shutdown(self) -> bool:
        """Check if shutdown"""
        return self._state == EmergencyState.SHUTDOWN

    def can_trade(self) -> bool:
        """
        Check if trading is allowed.

        Returns:
            True if in NORMAL or ALERT state, False otherwise
        """
        return self._state in (EmergencyState.NORMAL, EmergencyState.ALERT)

    def can_operate(self) -> bool:
        """
        Check if any operations are allowed.

        Returns:
            True if not in SHUTDOWN state, False otherwise
        """
        return self._state != EmergencyState.SHUTDOWN

    async def assert_can_trade(self):
        """
        Assert that trading is allowed.

        Raises:
            EmergencyHalted: If trading is not allowed
        """
        if not self.can_trade():
            raise EmergencyHalted(
                self._state,
                self._halt_reason or "Emergency halt active"
            )

    async def assert_can_operate(self):
        """
        Assert that operations are allowed.

        Raises:
            EmergencyHalted: If operations are not allowed
        """
        if not self.can_operate():
            raise EmergencyHalted(
                self._state,
                self._halt_reason or "System shutdown active"
            )

    async def set_state(
        self,
        new_state: EmergencyState,
        reason: str,
        **metadata
    ):
        """
        Set emergency state.

        Args:
            new_state: New state to transition to
            reason: Reason for state change
            **metadata: Additional metadata
        """
        async with self._lock:
            previous_state = self._state

            if previous_state == new_state:
                logger.debug(
                    "emergency_state_unchanged",
                    controller_id=self.controller_id,
                    state=new_state.value
                )
                return

            self._state = new_state
            self._halt_reason = reason
            self._halt_timestamp = datetime.utcnow()
            self._metadata.update(metadata)

            # Create event
            event = EmergencyEvent(
                controller_id=self.controller_id,
                previous_state=previous_state,
                new_state=new_state,
                reason=reason,
                timestamp=self._halt_timestamp,
                metadata=metadata
            )

            # Log state change
            log_level = "critical" if new_state in (EmergencyState.HALT, EmergencyState.SHUTDOWN) else "warning"
            getattr(logger, log_level)(
                "emergency_state_changed",
                controller_id=self.controller_id,
                previous_state=previous_state.value,
                new_state=new_state.value,
                reason=reason,
                **metadata
            )

            # Notify handlers
            await self._notify_handlers(event)

    async def halt(self, reason: str, **metadata):
        """
        Trigger emergency halt.

        No new trades will be allowed until resumed.

        Args:
            reason: Reason for halt
            **metadata: Additional metadata
        """
        await self.set_state(EmergencyState.HALT, reason, **metadata)

    async def alert(self, reason: str, **metadata):
        """
        Set alert state.

        Operations continue but with caution.

        Args:
            reason: Reason for alert
            **metadata: Additional metadata
        """
        await self.set_state(EmergencyState.ALERT, reason, **metadata)

    async def shutdown(self, reason: str, **metadata):
        """
        Trigger complete shutdown.

        All operations will cease.

        Args:
            reason: Reason for shutdown
            **metadata: Additional metadata
        """
        await self.set_state(EmergencyState.SHUTDOWN, reason, **metadata)

    async def resume(self, reason: str = "Manual resume", **metadata):
        """
        Resume normal operations.

        Args:
            reason: Reason for resume
            **metadata: Additional metadata
        """
        await self.set_state(EmergencyState.NORMAL, reason, **metadata)

    async def check_risk_limit(
        self,
        limit_type: str,
        current_value: float,
        limit_value: float,
        auto_halt: bool = True
    ):
        """
        Check if a risk limit is exceeded.

        Args:
            limit_type: Type of limit (e.g., "daily_loss", "position_size")
            current_value: Current value
            limit_value: Limit threshold
            auto_halt: Automatically halt if limit exceeded (default: True)

        Raises:
            RiskLimitExceeded: If limit is exceeded
        """
        # Track limit
        self._risk_limits[limit_type] = (current_value, limit_value)

        # Check if exceeded
        is_exceeded = False
        if limit_type.endswith("_loss"):
            # For loss limits, current should be >= limit (less negative)
            is_exceeded = current_value < limit_value
        else:
            # For other limits, current should be <= limit
            is_exceeded = current_value > limit_value

        if is_exceeded:
            logger.error(
                "risk_limit_exceeded",
                controller_id=self.controller_id,
                limit_type=limit_type,
                current=current_value,
                limit=limit_value,
                utilization=abs(current_value / limit_value) if limit_value != 0 else float('inf')
            )

            # Auto-halt if enabled
            if auto_halt:
                await self.halt(
                    f"Risk limit exceeded: {limit_type}",
                    limit_type=limit_type,
                    current_value=current_value,
                    limit_value=limit_value
                )

            raise RiskLimitExceeded(limit_type, current_value, limit_value)

        # Warn if approaching limit (80% threshold)
        threshold = 0.8
        utilization = abs(current_value / limit_value) if limit_value != 0 else 0
        if utilization >= threshold:
            logger.warning(
                "risk_limit_approaching",
                controller_id=self.controller_id,
                limit_type=limit_type,
                current=current_value,
                limit=limit_value,
                utilization=utilization
            )

    async def subscribe(self, handler: EventHandler):
        """
        Subscribe to emergency state changes.

        Args:
            handler: Async function to call on state changes
        """
        async with self._lock:
            self._handlers.append(handler)

        logger.debug(
            "emergency_handler_subscribed",
            controller_id=self.controller_id,
            total_handlers=len(self._handlers)
        )

    async def unsubscribe(self, handler: EventHandler):
        """
        Unsubscribe from emergency state changes.

        Args:
            handler: Handler to remove
        """
        async with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

        logger.debug(
            "emergency_handler_unsubscribed",
            controller_id=self.controller_id,
            total_handlers=len(self._handlers)
        )

    async def _notify_handlers(self, event: EmergencyEvent):
        """Notify all subscribed handlers of state change"""
        handlers = self._handlers.copy()

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "emergency_handler_error",
                    controller_id=self.controller_id,
                    error=str(e),
                    error_type=type(e).__name__
                )

    def get_status(self) -> Dict[str, Any]:
        """
        Get current controller status.

        Returns:
            Dictionary with status information
        """
        return {
            "controller_id": self.controller_id,
            "state": self._state.value,
            "can_trade": self.can_trade(),
            "can_operate": self.can_operate(),
            "halt_reason": self._halt_reason,
            "halt_timestamp": self._halt_timestamp.isoformat() if self._halt_timestamp else None,
            "risk_limits": {
                name: {
                    "current": current,
                    "limit": limit,
                    "utilization": abs(current / limit) if limit != 0 else 0
                }
                for name, (current, limit) in self._risk_limits.items()
            },
            "metadata": self._metadata,
            "handlers_count": len(self._handlers)
        }

    async def persist_state(self, state_store) -> None:
        """
        Persist controller state to state store.

        Args:
            state_store: StateStore instance

        Usage:
            from src.infrastructure.state import create_state_store

            state_store = create_state_store("redis")
            await controller.persist_state(state_store)
        """
        state_data = {
            "state": self._state.value,
            "halt_reason": self._halt_reason,
            "halt_timestamp": self._halt_timestamp.isoformat() if self._halt_timestamp else None,
            "metadata": self._metadata,
            "risk_limits": {
                name: {"current": current, "limit": limit}
                for name, (current, limit) in self._risk_limits.items()
            }
        }

        key = f"emergency_controller:{self.controller_id}"
        await state_store.set(key, state_data)

        logger.info(
            "emergency_state_persisted",
            controller_id=self.controller_id,
            state=self._state.value
        )

    async def restore_state(self, state_store) -> bool:
        """
        Restore controller state from state store.

        Args:
            state_store: StateStore instance

        Returns:
            True if state was restored, False if no saved state

        Usage:
            from src.infrastructure.state import create_state_store

            state_store = create_state_store("redis")
            restored = await controller.restore_state(state_store)
        """
        key = f"emergency_controller:{self.controller_id}"
        state_data = await state_store.get(key)

        if not state_data:
            logger.debug(
                "no_emergency_state_to_restore",
                controller_id=self.controller_id
            )
            return False

        async with self._lock:
            self._state = EmergencyState(state_data["state"])
            self._halt_reason = state_data.get("halt_reason")

            halt_timestamp_str = state_data.get("halt_timestamp")
            self._halt_timestamp = (
                datetime.fromisoformat(halt_timestamp_str)
                if halt_timestamp_str else None
            )

            self._metadata = state_data.get("metadata", {})

            # Restore risk limits
            risk_limits_data = state_data.get("risk_limits", {})
            self._risk_limits = {
                name: (data["current"], data["limit"])
                for name, data in risk_limits_data.items()
            }

        logger.info(
            "emergency_state_restored",
            controller_id=self.controller_id,
            state=self._state.value,
            halt_reason=self._halt_reason
        )

        return True
