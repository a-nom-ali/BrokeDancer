"""
Strategy Versioning

Provides version tracking for trading strategies with:
- Version metadata embedded in strategy classes
- Strategy registry with version tracking
- Ability to load specific strategy versions
- Configuration snapshot support
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from src.infrastructure.logging import get_logger

from .base import EntityType, VersionMetadata, VersionStore

logger = get_logger(__name__)


@dataclass
class StrategyVersion:
    """
    Version metadata for a strategy class.

    Follows semantic versioning (major.minor.patch).
    """
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> "StrategyVersion":
        """
        Parse version string into StrategyVersion.

        Args:
            version_str: Version string like "1.2.3"

        Returns:
            StrategyVersion instance
        """
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )

    def is_compatible_with(self, other: "StrategyVersion") -> bool:
        """
        Check if this version is backward compatible with other.

        Major version changes indicate breaking changes.

        Args:
            other: Version to compare against

        Returns:
            True if compatible (same major version)
        """
        return self.major == other.major

    def __lt__(self, other: "StrategyVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StrategyVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)


class StrategyVersionMixin:
    """
    Mixin for strategies to declare version information.

    Add this mixin to strategy classes to enable version tracking.

    Usage:
        class MyStrategy(BaseStrategy, StrategyVersionMixin):
            __version__ = "1.2.0"
            __changelog__ = "Added dynamic stop-loss"

            # ... strategy implementation ...
    """
    __version__: str = "1.0.0"
    __changelog__: str = ""

    @classmethod
    def get_version(cls) -> StrategyVersion:
        """Get parsed version"""
        return StrategyVersion.parse(cls.__version__)

    def get_version_info(self) -> Dict[str, Any]:
        """Get version information as dictionary"""
        return {
            "class": self.__class__.__name__,
            "version": self.__version__,
            "changelog": self.__changelog__
        }


class StrategyRegistry:
    """
    Registry for tracking strategy versions.

    Maintains a mapping of strategy_name -> version -> class.
    Also supports saving/restoring strategy configurations.

    Usage:
        registry = StrategyRegistry(version_store)

        # Register strategy classes
        registry.register(BinaryArbitrageStrategy)
        registry.register(MarketMakingStrategy)

        # Get strategy class
        strategy_class = registry.get("BinaryArbitrageStrategy")
        strategy_class = registry.get("BinaryArbitrageStrategy", version="1.0.0")

        # Save configuration
        await registry.save_strategy_config(
            strategy_name="my_arb",
            config={"threshold": 0.01, "max_size": 1000},
            created_by="user"
        )
    """

    def __init__(self, version_store: VersionStore):
        self._store = version_store
        self._strategies: Dict[str, Dict[str, Type]] = {}  # name -> version -> class
        self._active_versions: Dict[str, str] = {}  # name -> active version

    def register(self, strategy_class: Type) -> None:
        """
        Register a strategy class.

        Args:
            strategy_class: Strategy class to register
        """
        name = strategy_class.__name__
        version = getattr(strategy_class, "__version__", "1.0.0")

        if name not in self._strategies:
            self._strategies[name] = {}

        self._strategies[name][version] = strategy_class

        # Set as active if it's the first or highest version
        if name not in self._active_versions:
            self._active_versions[name] = version
        else:
            current = StrategyVersion.parse(self._active_versions[name])
            new = StrategyVersion.parse(version)
            if new > current:
                self._active_versions[name] = version

        logger.info(
            "strategy_registered",
            strategy=name,
            version=version
        )

    def get(self, name: str, version: Optional[str] = None) -> Optional[Type]:
        """
        Get a strategy class by name and optional version.

        Args:
            name: Strategy class name
            version: Specific version (None = active/latest)

        Returns:
            Strategy class or None if not found
        """
        if name not in self._strategies:
            return None

        if version is None:
            version = self._active_versions.get(name)

        return self._strategies[name].get(version)

    def list_strategies(self) -> List[str]:
        """
        List all registered strategy names.

        Returns:
            List of strategy names
        """
        return list(self._strategies.keys())

    def list_versions(self, name: str) -> List[str]:
        """
        List all versions of a strategy.

        Args:
            name: Strategy name

        Returns:
            List of version strings, newest first
        """
        if name not in self._strategies:
            return []

        versions = list(self._strategies[name].keys())
        return sorted(versions, key=lambda v: StrategyVersion.parse(v), reverse=True)

    def get_active_version(self, name: str) -> Optional[str]:
        """
        Get the active version for a strategy.

        Args:
            name: Strategy name

        Returns:
            Active version string or None
        """
        return self._active_versions.get(name)

    def set_active_version(self, name: str, version: str) -> bool:
        """
        Set the active version for a strategy.

        Args:
            name: Strategy name
            version: Version to make active

        Returns:
            True if set, False if version doesn't exist
        """
        if name not in self._strategies:
            return False
        if version not in self._strategies[name]:
            return False

        self._active_versions[name] = version
        logger.info(
            "strategy_active_version_changed",
            strategy=name,
            version=version
        )
        return True

    async def save_strategy_config(
        self,
        strategy_name: str,
        config: Dict[str, Any],
        created_by: str,
        message: Optional[str] = None
    ) -> VersionMetadata:
        """
        Save a strategy configuration snapshot.

        Args:
            strategy_name: Name of the strategy instance
            config: Strategy configuration
            created_by: User or system ID
            message: Optional version message

        Returns:
            VersionMetadata of saved configuration
        """
        strategy_class = self.get(strategy_name)

        data = {
            "strategy_name": strategy_name,
            "strategy_class": strategy_class.__name__ if strategy_class else "unknown",
            "strategy_version": getattr(strategy_class, "__version__", "1.0.0") if strategy_class else "unknown",
            "config": config,
            "saved_at": datetime.utcnow().isoformat()
        }

        logger.info(
            "strategy_config_saved",
            strategy_name=strategy_name,
            created_by=created_by
        )

        return await self._store.save_version(
            entity_type=EntityType.STRATEGY,
            entity_id=strategy_name,
            data=data,
            created_by=created_by,
            message=message
        )

    async def get_strategy_config(
        self,
        strategy_name: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a strategy configuration.

        Args:
            strategy_name: Strategy name
            version: Config version (None = latest)

        Returns:
            Configuration data or None
        """
        snapshot = await self._store.get_version(
            EntityType.STRATEGY,
            strategy_name,
            version
        )
        return snapshot.data if snapshot else None

    async def list_strategy_configs(
        self,
        strategy_name: str,
        limit: int = 50
    ) -> List[VersionMetadata]:
        """
        List configuration history for a strategy.

        Args:
            strategy_name: Strategy name
            limit: Max configs to return

        Returns:
            List of VersionMetadata, newest first
        """
        return await self._store.list_versions(
            EntityType.STRATEGY,
            strategy_name,
            limit=limit
        )
