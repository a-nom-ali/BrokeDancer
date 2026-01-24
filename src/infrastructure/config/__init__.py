"""
Configuration Management

Provides type-safe configuration management using Pydantic.

Features:
- Environment variable loading
- Type validation
- Nested configuration structures
- Default values
- Configuration presets (dev/staging/prod)

Usage:
    # Define configuration
    from src.infrastructure.config import Config, StateConfig, EventsConfig

    config = Config()

    # Access configuration
    state_store = create_state_store(
        backend=config.state.backend,
        url=config.state.redis_url
    )

    # Environment-specific config
    from src.infrastructure.config import get_config

    config = get_config("production")  # Loads production settings
"""

from .config import (
    Config,
    StateConfig,
    EventsConfig,
    LoggingConfig,
    ResilienceConfig,
    EmergencyConfig,
    get_config,
    Environment
)

__all__ = [
    "Config",
    "StateConfig",
    "EventsConfig",
    "LoggingConfig",
    "ResilienceConfig",
    "EmergencyConfig",
    "get_config",
    "Environment",
]
