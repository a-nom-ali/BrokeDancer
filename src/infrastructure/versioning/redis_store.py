"""
Redis Version Store

Production-ready Redis implementation for persistent version storage.
Supports atomic operations and efficient version listing.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from .base import (
    EntityType,
    RetentionPolicy,
    VersionedSnapshot,
    VersionMetadata,
    VersionStore,
)


class RedisVersionStore(VersionStore):
    """
    Redis-backed version store for production use.

    Follows RedisStateStore pattern:
    - Persistent across restarts
    - Atomic operations
    - Lazy connection initialization

    Key schema:
    - version:{type}:{id}:latest -> int (latest version number)
    - version:{type}:{id}:v:{n} -> JSON (snapshot data)
    - version:{type}:{id}:meta:{n} -> JSON (metadata only, for listing)
    - version:{type}:{id}:versions -> sorted set (version index)
    """

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self._redis = None

    async def _ensure_connected(self):
        """Lazily initialize Redis connection"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
            except ImportError:
                raise ImportError(
                    "redis package not installed. "
                    "Install with: pip install redis"
                )

            self._redis = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            await self._redis.ping()

    def _key(self, entity_type: EntityType, entity_id: str, suffix: str) -> str:
        """Generate Redis key"""
        return f"version:{entity_type.value}:{entity_id}:{suffix}"

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
        await self._ensure_connected()

        from datetime import datetime

        latest_key = self._key(entity_type, entity_id, "latest")

        # Atomic increment for version number
        new_version = await self._redis.incr(latest_key)

        # Get parent version
        parent_version = new_version - 1 if new_version > 1 else None

        # Create metadata
        metadata = VersionMetadata(
            entity_type=entity_type,
            entity_id=entity_id,
            version=new_version,
            created_at=datetime.utcnow(),
            created_by=created_by,
            message=message,
            parent_version=parent_version,
            tags=tags or [],
            checksum=self._compute_checksum(data)
        )

        # Store using pipeline for atomicity
        snapshot = VersionedSnapshot(metadata=metadata, data=data)

        pipe = self._redis.pipeline()

        # Store full snapshot
        version_key = self._key(entity_type, entity_id, f"v:{new_version}")
        pipe.set(version_key, json.dumps(snapshot.to_dict()))

        # Store metadata separately for efficient listing
        meta_key = self._key(entity_type, entity_id, f"meta:{new_version}")
        pipe.set(meta_key, json.dumps(metadata.to_dict()))

        # Add to sorted set for efficient version listing
        index_key = self._key(entity_type, entity_id, "versions")
        pipe.zadd(index_key, {str(new_version): new_version})

        await pipe.execute()

        return metadata

    async def get_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: Optional[int] = None
    ) -> Optional[VersionedSnapshot]:
        await self._ensure_connected()

        if version is None:
            version = await self.get_latest_version(entity_type, entity_id)
            if version is None:
                return None

        version_key = self._key(entity_type, entity_id, f"v:{version}")
        data = await self._redis.get(version_key)

        if data is None:
            return None

        return VersionedSnapshot.from_dict(json.loads(data))

    async def get_latest_version(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> Optional[int]:
        await self._ensure_connected()

        latest_key = self._key(entity_type, entity_id, "latest")
        value = await self._redis.get(latest_key)

        return int(value) if value else None

    async def list_versions(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[VersionMetadata]:
        await self._ensure_connected()

        index_key = self._key(entity_type, entity_id, "versions")

        # Get version numbers from sorted set (highest to lowest)
        versions = await self._redis.zrevrange(
            index_key, offset, offset + limit - 1
        )

        if not versions:
            return []

        # Fetch metadata for each version
        pipe = self._redis.pipeline()
        for v in versions:
            meta_key = self._key(entity_type, entity_id, f"meta:{v}")
            pipe.get(meta_key)

        results = await pipe.execute()

        metadata_list = []
        for data in results:
            if data:
                metadata_list.append(VersionMetadata.from_dict(json.loads(data)))

        return metadata_list

    async def delete_version(
        self,
        entity_type: EntityType,
        entity_id: str,
        version: int
    ) -> bool:
        await self._ensure_connected()

        pipe = self._redis.pipeline()

        version_key = self._key(entity_type, entity_id, f"v:{version}")
        meta_key = self._key(entity_type, entity_id, f"meta:{version}")
        index_key = self._key(entity_type, entity_id, "versions")

        pipe.delete(version_key)
        pipe.delete(meta_key)
        pipe.zrem(index_key, str(version))

        results = await pipe.execute()

        return results[0] > 0  # True if version key was deleted

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
        await self._ensure_connected()

        # Fetch, modify, and save metadata
        meta_key = self._key(entity_type, entity_id, f"meta:{version}")
        data = await self._redis.get(meta_key)

        if not data:
            return False

        metadata = VersionMetadata.from_dict(json.loads(data))
        metadata.tags = list(set(metadata.tags + tags))

        await self._redis.set(meta_key, json.dumps(metadata.to_dict()))

        # Also update the full snapshot
        version_key = self._key(entity_type, entity_id, f"v:{version}")
        snapshot_data = await self._redis.get(version_key)

        if snapshot_data:
            snapshot = VersionedSnapshot.from_dict(json.loads(snapshot_data))
            snapshot.metadata.tags = metadata.tags
            await self._redis.set(version_key, json.dumps(snapshot.to_dict()))

        return True

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def ping(self) -> bool:
        """Health check"""
        try:
            await self._ensure_connected()
            await self._redis.ping()
            return True
        except Exception:
            return False
