"""
Event Sourcing / Audit Log

Provides persistent event storage with:
- Significant event persistence
- Queryable event history
- Replay capability for debugging
- Retention policies
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.infrastructure.logging import get_logger

from .base import EntityType, RetentionPolicy, VersionMetadata, VersionStore

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Categories of auditable events"""
    TRADE_EXECUTED = "trade_executed"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_PAUSED = "bot_paused"
    BOT_RESUMED = "bot_resumed"
    STRATEGY_CHANGED = "strategy_changed"
    CONFIG_CHANGED = "config_changed"
    WORKFLOW_MODIFIED = "workflow_modified"
    EMERGENCY_HALT = "emergency_halt"
    EMERGENCY_RESUME = "emergency_resume"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    ERROR_OCCURRED = "error_occurred"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"


@dataclass
class AuditEvent:
    """Auditable event record"""
    event_type: AuditEventType
    entity_type: str
    entity_id: str
    timestamp: datetime
    actor: str
    action: str
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary"""
        return {
            "event_type": self.event_type.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "data": self.data,
            "correlation_id": self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Deserialize event from dictionary"""
        return cls(
            event_type=AuditEventType(data["event_type"]),
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data["actor"],
            action=data["action"],
            data=data.get("data", {}),
            correlation_id=data.get("correlation_id")
        )


class AuditLog:
    """
    Persistent audit log for significant events.

    Uses VersionStore for persistence with specialized
    querying and replay capabilities.

    Usage:
        audit = AuditLog(version_store)

        # Record an event
        await audit.record(
            event_type=AuditEventType.TRADE_EXECUTED,
            entity_type="bot",
            entity_id="bot_001",
            actor="system",
            action="Executed arbitrage trade",
            data={"profit": 12.50, "pair": "BTC-USD"}
        )

        # Query events
        events = await audit.query(
            entity_type="bot",
            entity_id="bot_001",
            event_type=AuditEventType.TRADE_EXECUTED,
            limit=100
        )

        # Replay events for debugging
        await audit.replay(
            entity_type="bot",
            entity_id="bot_001",
            handler=my_replay_handler
        )
    """

    def __init__(
        self,
        version_store: VersionStore,
        event_bus: Optional[Any] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ):
        """
        Initialize AuditLog.

        Args:
            version_store: Version store backend
            event_bus: Optional event bus for real-time notifications
            retention_policy: Policy for event retention
        """
        self._store = version_store
        self._event_bus = event_bus
        self._retention = retention_policy or RetentionPolicy(
            max_age=timedelta(days=90),
            keep_latest=1000
        )

    async def record(
        self,
        event_type: AuditEventType,
        entity_type: str,
        entity_id: str,
        actor: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> VersionMetadata:
        """
        Record an auditable event.

        Args:
            event_type: Category of event
            entity_type: Type of entity involved (e.g., "bot", "strategy")
            entity_id: Entity identifier
            actor: Who performed the action
            action: Description of action
            data: Additional event data
            correlation_id: For tracing related events

        Returns:
            VersionMetadata of stored event
        """
        event = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow(),
            actor=actor,
            action=action,
            data=data or {},
            correlation_id=correlation_id
        )

        # Use a composite key for the event
        # Format: {entity_type}:{entity_id} so we can query by entity
        composite_id = f"{entity_type}:{entity_id}"

        meta = await self._store.save_version(
            entity_type=EntityType.EVENT,
            entity_id=composite_id,
            data=event.to_dict(),
            created_by=actor,
            message=f"{event_type.value}: {action}",
            tags=[event_type.value]
        )

        logger.debug(
            "audit_event_recorded",
            event_type=event_type.value,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            version=meta.version
        )

        # Publish to event bus if available
        if self._event_bus:
            try:
                await self._event_bus.publish(
                    f"audit:{event_type.value}",
                    event.to_dict()
                )
            except Exception as e:
                logger.warning("audit_event_publish_failed", error=str(e))

        return meta

    async def query(
        self,
        entity_type: str,
        entity_id: str,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit events with filters.

        Args:
            entity_type: Entity type to query
            entity_id: Entity ID to query
            event_type: Filter by event type
            actor: Filter by actor
            from_time: Filter events after this time
            to_time: Filter events before this time
            limit: Max events to return

        Returns:
            List of AuditEvent, newest first
        """
        composite_id = f"{entity_type}:{entity_id}"
        versions = await self._store.list_versions(
            EntityType.EVENT,
            composite_id,
            limit=limit * 2  # Fetch extra to allow for filtering
        )

        events = []
        for meta in versions:
            if len(events) >= limit:
                break

            snapshot = await self._store.get_version(
                EntityType.EVENT,
                composite_id,
                meta.version
            )

            if not snapshot:
                continue

            event = AuditEvent.from_dict(snapshot.data)

            # Apply filters
            if event_type and event.event_type != event_type:
                continue
            if actor and event.actor != actor:
                continue
            if from_time and event.timestamp < from_time:
                continue
            if to_time and event.timestamp > to_time:
                continue

            events.append(event)

        return events

    async def get_event(
        self,
        entity_type: str,
        entity_id: str,
        version: int
    ) -> Optional[AuditEvent]:
        """
        Get a specific audit event by version.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            version: Event version number

        Returns:
            AuditEvent or None if not found
        """
        composite_id = f"{entity_type}:{entity_id}"
        snapshot = await self._store.get_version(
            EntityType.EVENT,
            composite_id,
            version
        )

        if snapshot:
            return AuditEvent.from_dict(snapshot.data)
        return None

    async def replay(
        self,
        entity_type: str,
        entity_id: str,
        handler: Callable[[AuditEvent], Awaitable[None]],
        from_version: int = 1,
        to_version: Optional[int] = None,
        event_types: Optional[List[AuditEventType]] = None
    ) -> int:
        """
        Replay events for an entity (for debugging).

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            handler: Async function to call for each event
            from_version: Starting version (inclusive)
            to_version: Ending version (inclusive, None = all)
            event_types: Filter by event types (None = all)

        Returns:
            Number of events replayed
        """
        composite_id = f"{entity_type}:{entity_id}"
        versions = await self._store.list_versions(
            EntityType.EVENT,
            composite_id,
            limit=10000
        )

        # Sort by version ascending for replay
        versions.sort(key=lambda m: m.version)

        count = 0
        for meta in versions:
            if meta.version < from_version:
                continue
            if to_version and meta.version > to_version:
                break

            snapshot = await self._store.get_version(
                EntityType.EVENT,
                composite_id,
                meta.version
            )

            if not snapshot:
                continue

            event = AuditEvent.from_dict(snapshot.data)

            # Filter by event types if specified
            if event_types and event.event_type not in event_types:
                continue

            await handler(event)
            count += 1

        logger.info(
            "audit_events_replayed",
            entity_type=entity_type,
            entity_id=entity_id,
            count=count
        )

        return count

    async def count_events(
        self,
        entity_type: str,
        entity_id: str
    ) -> int:
        """
        Count total events for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            Number of events
        """
        composite_id = f"{entity_type}:{entity_id}"
        latest = await self._store.get_latest_version(
            EntityType.EVENT,
            composite_id
        )
        return latest or 0

    async def apply_retention(
        self,
        entity_type: str,
        entity_id: str
    ) -> int:
        """
        Apply retention policy to events.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            Number of events deleted
        """
        composite_id = f"{entity_type}:{entity_id}"
        return await self._store.apply_retention_policy(
            EntityType.EVENT,
            composite_id,
            self._retention
        )
