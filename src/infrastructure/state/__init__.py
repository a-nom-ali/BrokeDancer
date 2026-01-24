"""
State Management Infrastructure

Provides abstraction for state persistence with multiple backend implementations.

Usage:
    # Create state store based on configuration
    from src.infrastructure.state import create_state_store

    # Local development (in-memory)
    store = create_state_store("memory")

    # Local Redis
    store = create_state_store("redis", url="redis://localhost:6379")

    # Hosted Redis (Redis Cloud, ElastiCache, etc.)
    store = create_state_store("redis", url="redis://:password@host:port")

    # Use the store
    await store.set("key", {"data": "value"})
    value = await store.get("key")
    await store.close()
"""

from typing import Optional
from .base import StateStore
from .memory import InMemoryStateStore
from .redis_store import RedisStateStore


def create_state_store(backend: str, **kwargs) -> StateStore:
    """
    Factory function to create state store based on backend type.

    Args:
        backend: Backend type ("memory" or "redis")
        **kwargs: Backend-specific configuration

    Returns:
        StateStore instance

    Examples:
        # In-memory store (development/testing)
        store = create_state_store("memory")

        # Local Redis
        store = create_state_store("redis", url="redis://localhost:6379")

        # Redis Cloud (hosted)
        store = create_state_store(
            "redis",
            url="redis://:password@redis-12345.c1.cloud.redislabs.com:12345"
        )

        # AWS ElastiCache
        store = create_state_store(
            "redis",
            url="redis://master.xxx.cache.amazonaws.com:6379"
        )

    Raises:
        ValueError: If backend is not recognized
    """
    if backend == "memory":
        return InMemoryStateStore()

    elif backend == "redis":
        url = kwargs.get("url", "redis://localhost:6379")
        return RedisStateStore(url=url)

    else:
        raise ValueError(
            f"Unknown state backend: {backend}. "
            f"Supported backends: 'memory', 'redis'"
        )


__all__ = [
    "StateStore",
    "InMemoryStateStore",
    "RedisStateStore",
    "create_state_store"
]
