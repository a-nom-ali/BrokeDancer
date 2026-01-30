"""
In-Memory Version Store

Fast in-memory implementation for local development and testing.
Data is lost on restart - use Redis for production.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    EntityType,
    RetentionPolicy,
    VersionedSnapshot,
    VersionMetadata,
    VersionStore,
)


class InMemoryVersionStore(VersionStore):
    """
    In-memory version store for local development and testing.

    Follows InMemoryStateStore pattern:
    - Fast (no network overhead)
    - Thread-safe (async lock)
    - Data lost on restart
    """

    def __init__(self):
        # Structure: {entity_type: {entity_id: {version: VersionedSnapshot}}}
        self._data: Dict[str, Dict[str, Dict[int, VersionedSnapshot]]] = {}
        # Track latest version per entity
        self._latest: Dict[str, Dict[str, int]] = {}
        self._lock = asyncio.Lock()

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute SHA-256 checksum of data"""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def save_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        data: Dict[str, Any],
        created_by: str,
        message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> VersionMetadata:
        async with self._lock:
            type_key = entity_type.value

            # Initialize storage if needed
            if type_key not in self._data:
                self._data[type_key] = {}
                self._latest[type_key] = {}

            if entity_id not in self._data[type_key]:
                self._data[type_key][entity_id] = {}
                self._latest[type_key][entity_id] = 0

            # Compute next version
            current_version = self._latest[type_key][entity_id]
            new_version = current_version + 1

            # Create metadata
            metadata = VersionMetadata(
                entity_type=entity_type,
                entity_id=entity_id,
                version=new_version,
                created_at=datetime.utcnow(),
                created_by=created_by,
                message=message,
                parent_version=current_version if current_version > 0 else None,
                tags=tags or [],
                checksum=self._compute_checksum(data)
            )

            # Store snapshot
            snapshot = VersionedSnapshot(metadata=metadata, data=data)
            self._data[type_key][entity_id][new_version] = snapshot
            self._latest[type_key][entity_id] = new_version

            return metadata

    async def get_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: Optional[int] = None
    ) -> Optional[VersionedSnapshot]:
        async with self._lock:
            type_key = entity_type.value

            if type_key not in self._data:
                return None
            if entity_id not in self._data[type_key]:
                return None

            if version is None:
                version = self._latest.get(type_key, {}).get(entity_id)
                if version is None:
                    return None

            return self._data[type_key][entity_id].get(version)

    async def get_latest_version(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> Optional[int]:
        async with self._lock:
            return self._latest.get(entity_type.value, {}).get(entity_id)

    async def list_versions(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        async with self._lock:
            type_key = entity_type.value

            if type_key not in self._data:
                return []
            if entity_id not in self._data[type_key]:
                return []

            versions = self._data[type_key][entity_id]
            sorted_versions = sorted(versions.keys(), reverse=True)
            paginated = sorted_versions[offset:offset + limit]

            return [versions[v].metadata for v in paginated]

    async def delete_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: int
    ) -> bool:
        async with self._lock:
            type_key = entity_type.value

            if type_key not in self._data:
                return False
            if entity_id not in self._data[type_key]:
                return False
            if version not in self._data[type_key][entity_id]:
                return False

            del self._data[type_key][entity_id][version]
            return True

    async def apply_retention_policy(
        self,
        entity_type: EntityType,
        entity_id: str,
        policy: RetentionPolicy
    ) -> int:
        from .retention import apply_policy

        versions = await self.list_versions(entity_type, entity_id, limit=10000)
        to_delete = apply_policy(versions, policy)

        deleted = 0
        for meta in to_delete:
            if await self.delete_version(entity_type, entity_id, meta.version):
                deleted += 1

        return deleted

    async def tag_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: int,
        tags: List[str]
    ) -> bool:
        async with self._lock:
            type_key = entity_type.value

            if type_key not in self._data:
                return False
            if entity_id not in self._data[type_key]:
                return False
            if version not in self._data[type_key][entity_id]:
                return False

            snapshot = self._data[type_key][entity_id][version]
            snapshot.metadata.tags = list(set(snapshot.metadata.tags + tags))
            return True

    async def close(self):
        async with self._lock:
            self._data.clear()
            self._latest.clear()

    # Testing helpers

    async def clear(self):
        """Clear all data (for testing)"""
        await self.close()

    async def count_versions(self, entity_type: EntityType, entity_id: str) -> int:
        """Count versions (for testing)"""
        async with self._lock:
            type_key = entity_type.value
            if type_key not in self._data:
                return 0
            if entity_id not in self._data[type_key]:
                return 0
            return len(self._data[type_key][entity_id])
