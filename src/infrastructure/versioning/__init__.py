"""
Versioning Infrastructure

Provides version control for strategies, workflows, configurations, and bot state.

Usage:
    from src.infrastructure.versioning import create_version_store, EntityType

    # Local development
    store = create_version_store("memory")

    # Production
    store = create_version_store("redis", url="redis://localhost:6379")

    # Save a version
    meta = await store.save_version(
        entity_type=EntityType.WORKFLOW,
        entity_id="my_workflow",
        data=workflow_dict,
        created_by="user@example.com",
        message="Added stop-loss node"
    )

    # Get version history
    versions = await store.list_versions(EntityType.WORKFLOW, "my_workflow")

    # Rollback
    await store.rollback(
        EntityType.WORKFLOW,
        "my_workflow",
        to_version=3,
        created_by="admin"
    )
"""

from .base import (
    EntityType,
    RetentionPolicy,
    VersionDiff,
    VersionedSnapshot,
    VersionMetadata,
    VersionStore,
    VersionStoreError,
    VersionNotFoundError,
    VersionConflictError,
)
from .memory import InMemoryVersionStore
from .redis_store import RedisVersionStore


def create_version_store(backend: str, **kwargs) -> VersionStore:
    """
    Factory function to create version store based on backend type.

    Args:
        backend: Backend type ("memory" or "redis")
        **kwargs: Backend-specific configuration
            - For redis: url (default: "redis://localhost:6379")

    Returns:
        VersionStore instance

    Raises:
        ValueError: If backend is not supported

    Usage:
        # Development
        store = create_version_store("memory")

        # Production
        store = create_version_store("redis", url="redis://localhost:6379")
    """
    if backend == "memory":
        return InMemoryVersionStore()

    elif backend == "redis":
        url = kwargs.get("url", "redis://localhost:6379")
        return RedisVersionStore(url=url)

    else:
        raise ValueError(
            f"Unknown version backend: {backend}. "
            f"Supported backends: 'memory', 'redis'"
        )


__all__ = [
    # Core types
    "VersionStore",
    "VersionMetadata",
    "VersionedSnapshot",
    "VersionDiff",
    "RetentionPolicy",
    "EntityType",
    # Exceptions
    "VersionStoreError",
    "VersionNotFoundError",
    "VersionConflictError",
    # Implementations
    "InMemoryVersionStore",
    "RedisVersionStore",
    # Factory
    "create_version_store",
]
