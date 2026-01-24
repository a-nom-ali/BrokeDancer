"""
In-Memory State Store Implementation

Fast, simple state store for local development and testing.
All data is stored in memory and lost on restart.
"""

from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import asyncio
from .base import StateStore


class InMemoryStateStore(StateStore):
    """
    In-memory state store for local development and testing.

    Features:
    - Fast (no network overhead)
    - Simple (no external dependencies)
    - Thread-safe (async lock)
    - TTL support (automatic expiration)

    Limitations:
    - Data lost on restart
    - Not shared across processes
    - Memory bounded by available RAM

    Usage:
        store = InMemoryStateStore()
        await store.set("user:123", {"name": "Alice"})
        user = await store.get("user:123")
    """

    def __init__(self):
        self._data: Dict[str, tuple[Any, Optional[datetime]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._data:
                return None

            value, expiry = self._data[key]

            # Check if expired
            if expiry and datetime.utcnow() > expiry:
                del self._data[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        async with self._lock:
            expiry = datetime.utcnow() + ttl if ttl else None
            self._data[key] = (value, expiry)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        result = await self.get(key)
        return result is not None

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        async with self._lock:
            expiry = datetime.utcnow() + ttl if ttl else None
            for key, value in items.items():
                self._data[key] = (value, expiry)

    async def increment(self, key: str, amount: int = 1) -> int:
        async with self._lock:
            current = 0
            if key in self._data:
                current_value, _ = self._data[key]
                if isinstance(current_value, (int, float)):
                    current = int(current_value)

            new_value = current + amount
            self._data[key] = (new_value, None)
            return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        return await self.increment(key, -amount)

    async def close(self):
        """Clear all data"""
        async with self._lock:
            self._data.clear()

    # Additional helper for testing

    async def size(self) -> int:
        """Get number of keys in store (useful for testing)"""
        async with self._lock:
            return len(self._data)

    async def clear(self):
        """Clear all data (useful for testing)"""
        await self.close()

    async def keys(self) -> list[str]:
        """Get all keys (useful for debugging)"""
        async with self._lock:
            return list(self._data.keys())
