"""
Version Store Abstraction

Provides a unified interface for version persistence across different backends.
Allows easy swapping between in-memory (dev/test) and Redis (production).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(Enum):
    """Types of entities that can be versioned"""
    STRATEGY = "strategy"
    WORKFLOW = "workflow"
    CONFIG = "config"
    BOT_STATE = "bot_state"
    EVENT = "event"


@dataclass
class VersionMetadata:
    """Metadata for a versioned entity snapshot"""
    entity_type: EntityType
    entity_id: str
    version: int
    created_at: datetime
    created_by: str
    message: Optional[str] = None
    parent_version: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to dictionary"""
        return {
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "message": self.message,
            "parent_version": self.parent_version,
            "tags": self.tags,
            "checksum": self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionMetadata":
        """Deserialize metadata from dictionary"""
        return cls(
            entity_type=EntityType(data["entity_type"]),
            entity_id=data["entity_id"],
            version=data["version"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data["created_by"],
            message=data.get("message"),
            parent_version=data.get("parent_version"),
            tags=data.get("tags", []),
            checksum=data.get("checksum")
        )


@dataclass
class VersionedSnapshot:
    """Complete versioned snapshot of an entity"""
    metadata: VersionMetadata
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionedSnapshot":
        """Deserialize snapshot from dictionary"""
        return cls(
            metadata=VersionMetadata.from_dict(data["metadata"]),
            data=data["data"]
        )


@dataclass
class VersionDiff:
    """Diff between two versions"""
    entity_type: EntityType
    entity_id: str
    from_version: int
    to_version: int
    changes: List[Dict[str, Any]]
    summary: str


@dataclass
class RetentionPolicy:
    """Retention policy for versioned entities"""
    max_versions: Optional[int] = None
    max_age: Optional[timedelta] = None
    keep_tagged: bool = True
    keep_latest: int = 1


class VersionStore(ABC):
    """
    Abstract version persistence layer.

    This interface allows the application to be backend-agnostic,
    making it easy to switch between:
    - In-memory (fast dev/testing)
    - Local Redis (docker-compose)
    - Hosted Redis (ElastiCache, Redis Cloud, etc.)
    """

    @abstractmethod
    async def save_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        data: Dict[str, Any],
        created_by: str,
        message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> VersionMetadata:
        """
        Save a new version of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique entity identifier
            data: Entity data (must be JSON-serializable)
            created_by: User or system ID
            message: Optional version description
            tags: Optional tags for this version

        Returns:
            Metadata of the created version
        """
        pass

    @abstractmethod
    async def get_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: Optional[int] = None
    ) -> Optional[VersionedSnapshot]:
        """
        Get a specific version of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique entity identifier
            version: Version number (None = latest)

        Returns:
            VersionedSnapshot or None if not found
        """
        pass

    @abstractmethod
    async def get_latest_version(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> Optional[int]:
        """
        Get the latest version number for an entity.

        Returns:
            Latest version number or None if no versions exist
        """
        pass

    @abstractmethod
    async def list_versions(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        """
        List version history for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique entity identifier
            limit: Max versions to return
            offset: Number of versions to skip

        Returns:
            List of VersionMetadata, newest first
        """
        pass

    @abstractmethod
    async def delete_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: int
    ) -> bool:
        """
        Delete a specific version.

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def apply_retention_policy(
        self,
        entity_type: EntityType,
        entity_id: str,
        policy: RetentionPolicy
    ) -> int:
        """
        Apply retention policy to an entity's versions.

        Returns:
            Number of versions deleted
        """
        pass

    @abstractmethod
    async def close(self):
        """Close connections and cleanup resources."""
        pass

    # Helper methods (can be overridden for optimization)

    async def diff_versions(
        self,
        entity_type: EntityType,
        entity_id: str,
        from_version: int,
        to_version: int
    ) -> Optional[VersionDiff]:
        """
        Compute diff between two versions.

        Default implementation fetches both versions and diffs.
        Can be overridden for optimization.
        """
        from .diff import compute_diff

        from_snapshot = await self.get_version(entity_type, entity_id, from_version)
        to_snapshot = await self.get_version(entity_type, entity_id, to_version)

        if not from_snapshot or not to_snapshot:
            return None

        return compute_diff(
            entity_type=entity_type,
            entity_id=entity_id,
            from_version=from_version,
            to_version=to_version,
            from_data=from_snapshot.data,
            to_data=to_snapshot.data
        )

    async def rollback(
        self,
        entity_type: EntityType,
        entity_id: str,
        to_version: int,
        created_by: str
    ) -> Optional[VersionMetadata]:
        """
        Rollback to a previous version (creates new version with old data).

        This does NOT delete intermediate versions.

        Returns:
            Metadata of the new version, or None if source version not found
        """
        source = await self.get_version(entity_type, entity_id, to_version)
        if not source:
            return None

        return await self.save_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=source.data,
            created_by=created_by,
            message=f"Rollback to version {to_version}",
            tags=["rollback"]
        )

    async def tag_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: int,
        tags: List[str]
    ) -> bool:
        """
        Add tags to a version (implementation-specific).

        Default returns False. Override for tag support.
        """
        return False


class VersionStoreError(Exception):
    """Base exception for version store errors"""
    pass


class VersionNotFoundError(VersionStoreError):
    """Raised when a version is not found"""
    pass


class VersionConflictError(VersionStoreError):
    """Raised on concurrent version conflicts"""
    pass
