"""
Configuration Snapshots

Provides named snapshots of configuration state with:
- Snapshot current config
- Named snapshots (not just timestamps)
- Restore previous configurations
- Diff between configs
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.infrastructure.logging import get_logger

from .base import EntityType, VersionMetadata, VersionStore
from .diff import compute_dict_diff

logger = get_logger(__name__)


class ConfigSnapshotManager:
    """
    Manages configuration snapshots.

    Unlike other versioned entities, configs use named snapshots
    (e.g., "production_2024_01", "before_feature_x") rather than
    just incrementing version numbers.

    Usage:
        manager = ConfigSnapshotManager(version_store)

        # Save current config
        await manager.save_snapshot(
            snapshot_name="before_upgrade",
            config=current_config,
            created_by="admin"
        )

        # Get snapshot
        config = await manager.get_snapshot("before_upgrade")

        # Compare snapshots
        diff = await manager.diff_snapshots("before_upgrade", "after_upgrade")
    """

    def __init__(self, version_store: VersionStore):
        self._store = version_store

    async def save_snapshot(
        self,
        snapshot_name: str,
        config: Any,
        created_by: str,
        message: Optional[str] = None
    ) -> VersionMetadata:
        """
        Save a named configuration snapshot.

        Args:
            snapshot_name: Unique name for this snapshot
            config: Config instance or dictionary to snapshot
            created_by: User or system ID
            message: Optional description

        Returns:
            VersionMetadata
        """
        # Handle both Config objects and plain dicts
        if hasattr(config, "model_dump"):
            # Pydantic model
            config_dict = config.model_dump()
        elif hasattr(config, "dict"):
            # Older Pydantic model
            config_dict = config.dict()
        elif isinstance(config, dict):
            config_dict = config
        else:
            # Try to extract attributes
            config_dict = {
                k: v for k, v in vars(config).items()
                if not k.startswith("_")
            }

        # Add snapshot metadata
        data = {
            "snapshot_name": snapshot_name,
            "snapshot_at": datetime.utcnow().isoformat(),
            "config": config_dict
        }

        logger.info(
            "config_snapshot_saved",
            snapshot_name=snapshot_name,
            created_by=created_by
        )

        return await self._store.save_version(
            entity_type=EntityType.CONFIG,
            entity_id=snapshot_name,
            data=data,
            created_by=created_by,
            message=message,
            tags=[snapshot_name]
        )

    async def get_snapshot(
        self,
        snapshot_name: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a configuration snapshot.

        Args:
            snapshot_name: Snapshot name
            version: Specific version (None = latest)

        Returns:
            Snapshot data or None
        """
        snapshot = await self._store.get_version(
            EntityType.CONFIG,
            snapshot_name,
            version
        )
        return snapshot.data if snapshot else None

    async def get_config(
        self,
        snapshot_name: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get just the config portion of a snapshot.

        Args:
            snapshot_name: Snapshot name
            version: Specific version (None = latest)

        Returns:
            Config dictionary or None
        """
        data = await self.get_snapshot(snapshot_name, version)
        if data:
            return data.get("config")
        return None

    async def list_snapshot_versions(
        self,
        snapshot_name: str,
        limit: int = 50
    ) -> List[VersionMetadata]:
        """
        List version history for a named snapshot.

        Args:
            snapshot_name: Snapshot name
            limit: Max versions to return

        Returns:
            List of VersionMetadata, newest first
        """
        return await self._store.list_versions(
            EntityType.CONFIG,
            snapshot_name,
            limit=limit
        )

    async def diff_snapshots(
        self,
        snapshot_a: str,
        snapshot_b: str,
        version_a: Optional[int] = None,
        version_b: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Diff two named snapshots.

        Args:
            snapshot_a: First snapshot name
            snapshot_b: Second snapshot name
            version_a: Specific version of first snapshot (None = latest)
            version_b: Specific version of second snapshot (None = latest)

        Returns:
            Dictionary with changes list and count, or None if snapshots not found
        """
        config_a = await self.get_config(snapshot_a, version_a)
        config_b = await self.get_config(snapshot_b, version_b)

        if not config_a or not config_b:
            return None

        return compute_dict_diff(config_a, config_b)

    async def restore_snapshot(
        self,
        snapshot_name: str,
        from_version: int,
        restored_by: str
    ) -> Optional[VersionMetadata]:
        """
        Restore a snapshot to a previous version.

        Creates a new version with the old data.

        Args:
            snapshot_name: Snapshot name
            from_version: Version to restore from
            restored_by: User performing the restore

        Returns:
            Metadata of new version, or None if source not found
        """
        result = await self._store.rollback(
            EntityType.CONFIG,
            snapshot_name,
            from_version,
            created_by=restored_by
        )

        if result:
            logger.info(
                "config_snapshot_restored",
                snapshot_name=snapshot_name,
                from_version=from_version,
                new_version=result.version,
                restored_by=restored_by
            )

        return result
