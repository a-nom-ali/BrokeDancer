"""
Redis State Store Implementation

Production-ready state store using Redis.
Works with local Redis or hosted services (ElastiCache, Redis Cloud, etc.).
"""

from typing import Any, Optional, Dict
from datetime import timedelta
import json
from .base import StateStore


class RedisStateStore(StateStore):
    """
    Redis-backed state store for production use.

    Features:
    - Persistent across restarts
    - Shared across processes
    - Atomic operations
    - TTL support (native)
    - High performance

    Supports:
    - Local Redis (docker-compose)
    - Redis Cloud (managed service)
    - AWS ElastiCache (managed service)
    - Any Redis-compatible service

    Usage:
        # Local Redis
        store = RedisStateStore("redis://localhost:6379")

        # Redis Cloud
        store = RedisStateStore("redis://:password@redis-12345.c1.cloud.redislabs.com:12345")

        # AWS ElastiCache
        store = RedisStateStore("redis://master.xxx.cache.amazonaws.com:6379")

        await store.set("user:123", {"name": "Alice"})
        user = await store.get("user:123")
    """

    def __init__(self, url: str = "redis://localhost:6379"):
        """
        Initialize Redis state store.

        Args:
            url: Redis connection URL
                Format: redis://[username]:[password]@[host]:[port]/[db]
        """
        self.url = url
        self._redis = None  # Lazy initialization

    async def _ensure_connected(self):
        """Lazy connection initialization"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
            except ImportError:
                raise ImportError(
                    "redis package not installed. Install with: pip install redis"
                )

            self._redis = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )

            # Test connection
            await self._redis.ping()

    async def get(self, key: str) -> Optional[Any]:
        await self._ensure_connected()
        value = await self._redis.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Return raw string if not JSON
            return value

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        await self._ensure_connected()

        # Serialize value as JSON
        serialized = json.dumps(value)

        if ttl:
            # Set with expiration
            await self._redis.setex(
                key,
                int(ttl.total_seconds()),
                serialized
            )
        else:
            # Set without expiration
            await self._redis.set(key, serialized)

    async def delete(self, key: str) -> bool:
        await self._ensure_connected()
        result = await self._redis.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        await self._ensure_connected()
        result = await self._redis.exists(key)
        return result > 0

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        await self._ensure_connected()

        if not keys:
            return {}

        values = await self._redis.mget(keys)
        result = {}

        for key, value in zip(keys, values):
            if value is not None:
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value

        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        await self._ensure_connected()

        if not items:
            return

        # Use pipeline for atomic operation
        pipe = self._redis.pipeline()

        for key, value in items.items():
            serialized = json.dumps(value)

            if ttl:
                pipe.setex(key, int(ttl.total_seconds()), serialized)
            else:
                pipe.set(key, serialized)

        await pipe.execute()

    async def increment(self, key: str, amount: int = 1) -> int:
        await self._ensure_connected()
        result = await self._redis.incrby(key, amount)
        return result

    async def decrement(self, key: str, amount: int = 1) -> int:
        await self._ensure_connected()
        result = await self._redis.decrby(key, amount)
        return result

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    # Redis-specific optimizations

    async def set_if_not_exists(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        Set key only if it doesn't exist (Redis SETNX).
        More efficient than checking existence first.
        """
        await self._ensure_connected()

        serialized = json.dumps(value)

        if ttl:
            # SET key value EX seconds NX
            result = await self._redis.set(
                key,
                serialized,
                ex=int(ttl.total_seconds()),
                nx=True
            )
        else:
            # SET key value NX
            result = await self._redis.set(key, serialized, nx=True)

        return result is not None

    async def get_and_delete(self, key: str) -> Optional[Any]:
        """
        Get value and delete key atomically (Redis GETDEL).
        More efficient than separate get + delete.
        """
        await self._ensure_connected()

        # Use GETDEL command (Redis 6.2+)
        try:
            value = await self._redis.getdel(key)
            if value is None:
                return None

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        except Exception:
            # Fallback for older Redis versions
            value = await self.get(key)
            if value is not None:
                await self.delete(key)
            return value

    async def expire(self, key: str, ttl: timedelta) -> bool:
        """
        Set expiration on existing key.

        Returns:
            True if expiration was set, False if key doesn't exist
        """
        await self._ensure_connected()
        result = await self._redis.expire(key, int(ttl.total_seconds()))
        return result > 0

    async def ttl(self, key: str) -> Optional[int]:
        """
        Get remaining time-to-live in seconds.

        Returns:
            Seconds until expiration, or None if key doesn't exist or has no TTL
        """
        await self._ensure_connected()
        result = await self._redis.ttl(key)

        if result == -2:
            # Key doesn't exist
            return None
        elif result == -1:
            # Key exists but has no TTL
            return None
        else:
            return result

    async def keys(self, pattern: str = "*") -> list[str]:
        """
        Get all keys matching pattern.

        Warning: This is O(N) operation, use with caution in production.
        Consider using SCAN for large datasets.

        Args:
            pattern: Redis pattern (e.g., "user:*", "session:*")

        Returns:
            List of matching keys
        """
        await self._ensure_connected()
        keys = await self._redis.keys(pattern)
        return [k.decode() if isinstance(k, bytes) else k for k in keys]

    async def ping(self) -> bool:
        """
        Test connection to Redis.

        Returns:
            True if connection is healthy
        """
        try:
            await self._ensure_connected()
            await self._redis.ping()
            return True
        except Exception:
            return False
