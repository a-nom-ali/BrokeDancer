"""
State Store Abstraction

Provides a unified interface for state persistence across different backends.
Allows easy swapping between in-memory (dev/test) and Redis (production).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import timedelta


class StateStore(ABC):
    """
    Abstract state persistence layer.

    This interface allows the application to be backend-agnostic,
    making it easy to switch between:
    - In-memory (fast dev/testing)
    - Local Redis (docker-compose)
    - Hosted Redis (ElastiCache, Redis Cloud, etc.)
    - Future: DynamoDB, PostgreSQL, etc.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value by key.

        Args:
            key: The key to retrieve

        Returns:
            The stored value, or None if key doesn't exist or expired
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """
        Set value with optional TTL.

        Args:
            key: The key to store
            value: The value to store (must be JSON-serializable)
            ttl: Optional time-to-live (None = no expiration)
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete key.

        Args:
            key: The key to delete

        Returns:
            True if key was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: The key to check

        Returns:
            True if key exists and hasn't expired, False otherwise
        """
        pass

    @abstractmethod
    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """
        Get multiple keys at once (atomic).

        Args:
            keys: List of keys to retrieve

        Returns:
            Dictionary mapping keys to values (only existing keys included)
        """
        pass

    @abstractmethod
    async def set_many(self, items: Dict[str, Any], ttl: Optional[timedelta] = None):
        """
        Set multiple keys at once (atomic).

        Args:
            items: Dictionary mapping keys to values
            ttl: Optional time-to-live for all keys
        """
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Atomically increment a counter.

        Args:
            key: The counter key
            amount: Amount to increment by (default 1)

        Returns:
            The new value after increment
        """
        pass

    @abstractmethod
    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Atomically decrement a counter.

        Args:
            key: The counter key
            amount: Amount to decrement by (default 1)

        Returns:
            The new value after decrement
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close connections and cleanup resources.

        Should be called when shutting down the application.
        """
        pass

    # Helper methods (can be overridden for better performance)

    async def get_or_default(self, key: str, default: Any) -> Any:
        """Get value or return default if key doesn't exist"""
        value = await self.get(key)
        return value if value is not None else default

    async def set_if_not_exists(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        Set key only if it doesn't already exist.

        Returns:
            True if key was set, False if it already existed
        """
        if await self.exists(key):
            return False
        await self.set(key, value, ttl)
        return True

    async def get_and_delete(self, key: str) -> Optional[Any]:
        """
        Get value and delete key atomically.

        Returns:
            The value, or None if key didn't exist
        """
        value = await self.get(key)
        if value is not None:
            await self.delete(key)
        return value
