"""
Bot State Snapshots

Provides full bot state capture with:
- Periodic automatic snapshots
- Manual snapshot creation
- State restoration
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.infrastructure.logging import get_logger

from .base import EntityType, RetentionPolicy, VersionMetadata, VersionStore

logger = get_logger(__name__)


class BotStateManager:
    """
    Manages bot state snapshots.

    Captures comprehensive bot state including:
    - Strategy configuration
    - Current positions
    - P&L tracking
    - Risk metrics
    - Execution history

    Usage:
        manager = BotStateManager(version_store)

        # Register a bot for snapshotting
        manager.register_bot("bot_001", bot_instance)

        # Manual snapshot
        await manager.capture_snapshot("bot_001", created_by="admin")

        # Start automatic snapshots
        await manager.start_auto_snapshots()

        # Restore state
        await manager.restore_state("bot_001", version=5, restored_by="admin")
    """

    def __init__(
        self,
        version_store: VersionStore,
        auto_snapshot_interval: Optional[timedelta] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ):
        """
        Initialize BotStateManager.

        Args:
            version_store: Version store backend
            auto_snapshot_interval: Interval for automatic snapshots (None = disabled)
            retention_policy: Policy for snapshot retention
        """
        self._store = version_store
        self._auto_interval = auto_snapshot_interval
        self._retention = retention_policy or RetentionPolicy(
            max_versions=100,
            max_age=timedelta(days=30),
            keep_latest=10
        )
        self._snapshot_task: Optional[asyncio.Task] = None
        self._bots: Dict[str, Dict[str, Any]] = {}  # bot_id -> {"provider": bot_instance}

    def register_bot(
        self,
        bot_id: str,
        state_provider: Any,
        state_extractor: Optional[Callable] = None
    ) -> None:
        """
        Register a bot for state snapshotting.

        Args:
            bot_id: Unique bot identifier
            state_provider: Object that provides state (bot instance)
            state_extractor: Optional custom function to extract state
        """
        self._bots[bot_id] = {
            "provider": state_provider,
            "extractor": state_extractor
        }
        logger.info("bot_registered_for_snapshots", bot_id=bot_id)

    def unregister_bot(self, bot_id: str) -> None:
        """
        Unregister a bot from snapshotting.

        Args:
            bot_id: Bot identifier
        """
        if bot_id in self._bots:
            del self._bots[bot_id]
            logger.info("bot_unregistered_from_snapshots", bot_id=bot_id)

    def list_registered_bots(self) -> List[str]:
        """
        List all registered bot IDs.

        Returns:
            List of bot IDs
        """
        return list(self._bots.keys())

    async def _extract_state(self, bot_id: str) -> Dict[str, Any]:
        """
        Extract state from a registered bot.

        Args:
            bot_id: Bot identifier

        Returns:
            State dictionary
        """
        if bot_id not in self._bots:
            return {}

        bot_info = self._bots[bot_id]
        provider = bot_info["provider"]
        extractor = bot_info.get("extractor")

        # Use custom extractor if provided
        if extractor:
            state = extractor(provider)
            if asyncio.iscoroutine(state):
                state = await state
            return state

        # Try various methods to get state
        if hasattr(provider, "get_full_state"):
            state = provider.get_full_state()
            if asyncio.iscoroutine(state):
                state = await state
            return state

        if hasattr(provider, "get_state"):
            state = provider.get_state()
            if asyncio.iscoroutine(state):
                state = await state
            return state

        if hasattr(provider, "get_stats"):
            return provider.get_stats()

        if hasattr(provider, "stats"):
            return provider.stats

        # Fallback: extract public attributes
        return {
            k: v for k, v in vars(provider).items()
            if not k.startswith("_") and not callable(v)
        }

    async def capture_snapshot(
        self,
        bot_id: str,
        created_by: str = "system",
        message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[VersionMetadata]:
        """
        Capture current bot state as a snapshot.

        Args:
            bot_id: Bot identifier
            created_by: User or "system" for auto-snapshots
            message: Optional snapshot description
            tags: Optional tags (e.g., ["manual", "pre-upgrade"])

        Returns:
            VersionMetadata or None if bot not registered
        """
        if bot_id not in self._bots:
            logger.warning("bot_not_registered", bot_id=bot_id)
            return None

        try:
            # Get full state from bot
            state = await self._extract_state(bot_id)

            # Enrich with metadata
            snapshot_data = {
                "bot_id": bot_id,
                "captured_at": datetime.utcnow().isoformat(),
                "state": state
            }

            meta = await self._store.save_version(
                entity_type=EntityType.BOT_STATE,
                entity_id=bot_id,
                data=snapshot_data,
                created_by=created_by,
                message=message,
                tags=tags
            )

            logger.info(
                "bot_state_snapshot_captured",
                bot_id=bot_id,
                version=meta.version,
                created_by=created_by
            )

            # Apply retention policy
            await self._store.apply_retention_policy(
                EntityType.BOT_STATE,
                bot_id,
                self._retention
            )

            return meta

        except Exception as e:
            logger.error(
                "bot_state_snapshot_failed",
                bot_id=bot_id,
                error=str(e)
            )
            return None

    async def get_snapshot(
        self,
        bot_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a bot state snapshot.

        Args:
            bot_id: Bot identifier
            version: Specific version (None = latest)

        Returns:
            Snapshot data or None
        """
        snapshot = await self._store.get_version(
            EntityType.BOT_STATE,
            bot_id,
            version
        )
        return snapshot.data if snapshot else None

    async def get_state(
        self,
        bot_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get just the state portion of a snapshot.

        Args:
            bot_id: Bot identifier
            version: Specific version (None = latest)

        Returns:
            State dictionary or None
        """
        data = await self.get_snapshot(bot_id, version)
        if data:
            return data.get("state")
        return None

    async def list_snapshots(
        self,
        bot_id: str,
        limit: int = 50
    ) -> List[VersionMetadata]:
        """
        List snapshot history for a bot.

        Args:
            bot_id: Bot identifier
            limit: Max snapshots to return

        Returns:
            List of VersionMetadata, newest first
        """
        return await self._store.list_versions(
            EntityType.BOT_STATE,
            bot_id,
            limit=limit
        )

    async def restore_state(
        self,
        bot_id: str,
        version: int,
        restored_by: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore bot to a previous state.

        Note: This returns the state data. Actual restoration
        depends on the bot's restore_state() implementation.

        Args:
            bot_id: Bot identifier
            version: Version to restore from
            restored_by: User performing the restore

        Returns:
            State data to restore, or None if version not found
        """
        snapshot = await self.get_snapshot(bot_id, version)

        if not snapshot:
            return None

        state = snapshot.get("state", {})

        # Try to restore state to the bot if registered
        if bot_id in self._bots:
            provider = self._bots[bot_id]["provider"]
            if hasattr(provider, "restore_state"):
                result = provider.restore_state(state)
                if asyncio.iscoroutine(result):
                    await result

                logger.info(
                    "bot_state_restored",
                    bot_id=bot_id,
                    from_version=version,
                    restored_by=restored_by
                )

        return state

    async def start_auto_snapshots(self):
        """Start automatic periodic snapshots"""
        if self._auto_interval and not self._snapshot_task:
            self._snapshot_task = asyncio.create_task(self._auto_snapshot_loop())
            logger.info(
                "auto_snapshots_started",
                interval_seconds=self._auto_interval.total_seconds()
            )

    async def stop_auto_snapshots(self):
        """Stop automatic snapshots"""
        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
            self._snapshot_task = None
            logger.info("auto_snapshots_stopped")

    async def _auto_snapshot_loop(self):
        """Background task for auto-snapshots"""
        while True:
            try:
                await asyncio.sleep(self._auto_interval.total_seconds())

                for bot_id in list(self._bots.keys()):
                    await self.capture_snapshot(
                        bot_id,
                        created_by="system",
                        message="Automatic periodic snapshot",
                        tags=["auto"]
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("auto_snapshot_error", error=str(e))
