"""
Configuration Models

Type-safe configuration using Pydantic.
"""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Deployment environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StateConfig(BaseModel):
    """State management configuration"""
    backend: Literal["memory", "redis"] = Field(
        default="memory",
        description="State backend to use"
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    key_prefix: str = Field(
        default="bot",
        description="Prefix for all state keys"
    )


class EventsConfig(BaseModel):
    """Event bus configuration"""
    backend: Literal["memory", "redis"] = Field(
        default="memory",
        description="Event bus backend to use"
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level"
    )
    format: Literal["console", "json"] = Field(
        default="console",
        description="Log format (console for dev, json for production)"
    )
    add_correlation_id: bool = Field(
        default=True,
        description="Add correlation IDs to logs"
    )
    show_locals: bool = Field(
        default=False,
        description="Show local variables in exception traces"
    )


class ResilienceConfig(BaseModel):
    """Resilience patterns configuration"""

    # Retry configuration
    retry_max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts"
    )
    retry_min_wait_seconds: float = Field(
        default=1.0,
        ge=0,
        description="Minimum wait between retries"
    )
    retry_max_wait_seconds: float = Field(
        default=60.0,
        ge=0,
        description="Maximum wait between retries"
    )
    retry_multiplier: float = Field(
        default=2.0,
        ge=1,
        description="Exponential backoff multiplier"
    )

    # Circuit breaker configuration
    circuit_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Failures before opening circuit"
    )
    circuit_success_threshold: int = Field(
        default=2,
        ge=1,
        description="Successes in half-open before closing"
    )
    circuit_timeout_seconds: float = Field(
        default=60.0,
        ge=0,
        description="Seconds before trying half-open"
    )
    circuit_window_seconds: float = Field(
        default=120.0,
        ge=0,
        description="Time window for counting failures"
    )

    # Timeout configuration
    api_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description="Default API call timeout"
    )
    db_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Default database timeout"
    )
    network_timeout_seconds: float = Field(
        default=15.0,
        gt=0,
        description="Default network operation timeout"
    )


class EmergencyConfig(BaseModel):
    """Emergency controls configuration"""

    # Risk limits
    daily_loss_limit: float = Field(
        default=-500.0,
        description="Daily loss limit (negative value)"
    )
    max_position_size: float = Field(
        default=10000.0,
        gt=0,
        description="Maximum position size"
    )
    max_drawdown_percent: float = Field(
        default=20.0,
        gt=0,
        le=100,
        description="Maximum drawdown percentage"
    )

    # Auto-halt settings
    auto_halt_on_limit: bool = Field(
        default=True,
        description="Automatically halt when limits exceeded"
    )
    persist_state: bool = Field(
        default=True,
        description="Persist emergency state across restarts"
    )


class Config(BaseSettings):
    """
    Main application configuration.

    Loads configuration from environment variables and .env file.

    Environment Variables:
        ENV: Environment (development/staging/production)
        STATE_BACKEND: State backend (memory/redis)
        EVENTS_BACKEND: Events backend (memory/redis)
        REDIS_URL: Redis connection URL
        LOG_LEVEL: Log level
        LOG_FORMAT: Log format (console/json)

    Usage:
        # Load default config
        config = Config()

        # Load from environment
        import os
        os.environ["ENV"] = "production"
        os.environ["STATE_BACKEND"] = "redis"
        config = Config()

        # Access configuration
        print(config.state.backend)
        print(config.logging.level)
    """

    # Environment
    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment"
    )

    # Sub-configurations
    state: StateConfig = Field(
        default_factory=StateConfig,
        description="State management configuration"
    )
    events: EventsConfig = Field(
        default_factory=EventsConfig,
        description="Event bus configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    resilience: ResilienceConfig = Field(
        default_factory=ResilienceConfig,
        description="Resilience patterns configuration"
    )
    emergency: EmergencyConfig = Field(
        default_factory=EmergencyConfig,
        description="Emergency controls configuration"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"  # e.g., STATE__BACKEND=redis


def get_development_config() -> Config:
    """
    Get development configuration.

    - In-memory state and events (fast, no dependencies)
    - Console logging (colorful, readable)
    - Relaxed resilience settings
    - Lower risk limits for testing
    """
    return Config(
        env=Environment.DEVELOPMENT,
        state=StateConfig(
            backend="memory"
        ),
        events=EventsConfig(
            backend="memory"
        ),
        logging=LoggingConfig(
            level="DEBUG",
            format="console",
            show_locals=True
        ),
        resilience=ResilienceConfig(
            retry_max_attempts=2,
            retry_min_wait_seconds=0.5,
            circuit_failure_threshold=10,
            api_timeout_seconds=30.0
        ),
        emergency=EmergencyConfig(
            daily_loss_limit=-100.0,
            max_position_size=1000.0,
            auto_halt_on_limit=False  # Don't auto-halt in dev
        )
    )


def get_staging_config() -> Config:
    """
    Get staging configuration.

    - Redis for state and events (realistic)
    - JSON logging (structured)
    - Production-like resilience settings
    - Production risk limits
    """
    return Config(
        env=Environment.STAGING,
        state=StateConfig(
            backend="redis",
            redis_url="redis://localhost:6379"
        ),
        events=EventsConfig(
            backend="redis",
            redis_url="redis://localhost:6379"
        ),
        logging=LoggingConfig(
            level="INFO",
            format="json",
            show_locals=False
        ),
        resilience=ResilienceConfig(
            retry_max_attempts=3,
            circuit_failure_threshold=5
        ),
        emergency=EmergencyConfig(
            daily_loss_limit=-500.0,
            auto_halt_on_limit=True
        )
    )


def get_production_config() -> Config:
    """
    Get production configuration.

    - Redis for state and events (persistent, distributed)
    - JSON logging (for log aggregation)
    - Strict resilience settings
    - Production risk limits
    - Auto-halt enabled
    """
    return Config(
        env=Environment.PRODUCTION,
        state=StateConfig(
            backend="redis",
            redis_url="redis://localhost:6379"  # Override with env var
        ),
        events=EventsConfig(
            backend="redis",
            redis_url="redis://localhost:6379"  # Override with env var
        ),
        logging=LoggingConfig(
            level="INFO",
            format="json",
            show_locals=False
        ),
        resilience=ResilienceConfig(
            retry_max_attempts=3,
            retry_min_wait_seconds=1.0,
            retry_max_wait_seconds=60.0,
            circuit_failure_threshold=5,
            circuit_timeout_seconds=60.0,
            api_timeout_seconds=10.0
        ),
        emergency=EmergencyConfig(
            daily_loss_limit=-500.0,
            max_position_size=10000.0,
            auto_halt_on_limit=True,
            persist_state=True
        )
    )


def get_config(env: Optional[str] = None) -> Config:
    """
    Get configuration for specified environment.

    Args:
        env: Environment name (development/staging/production)
             If None, loads from ENV environment variable

    Returns:
        Configuration instance

    Usage:
        # Load from environment variable
        config = get_config()

        # Load specific environment
        config = get_config("production")
        config = get_config("development")
        config = get_config("staging")
    """
    if env is None:
        # Load default config (reads from environment)
        return Config()

    env_lower = env.lower()

    if env_lower == "development":
        return get_development_config()
    elif env_lower == "staging":
        return get_staging_config()
    elif env_lower == "production":
        return get_production_config()
    else:
        raise ValueError(
            f"Unknown environment: {env}. "
            f"Use 'development', 'staging', or 'production'"
        )
