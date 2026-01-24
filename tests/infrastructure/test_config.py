"""
Tests for Configuration System

Tests Pydantic configuration models and environment presets.
"""

import pytest
from src.infrastructure.config import (
    Config,
    StateConfig,
    EventsConfig,
    LoggingConfig,
    ResilienceConfig,
    EmergencyConfig,
    get_config,
    Environment
)


def test_state_config_defaults():
    """Test StateConfig default values"""
    config = StateConfig()

    assert config.backend == "memory"
    assert config.redis_url == "redis://localhost:6379"
    assert config.key_prefix == "bot"


def test_events_config_defaults():
    """Test EventsConfig default values"""
    config = EventsConfig()

    assert config.backend == "memory"
    assert config.redis_url == "redis://localhost:6379"


def test_logging_config_defaults():
    """Test LoggingConfig default values"""
    config = LoggingConfig()

    assert config.level == "INFO"
    assert config.format == "console"
    assert config.add_correlation_id is True
    assert config.show_locals is False


def test_resilience_config_defaults():
    """Test ResilienceConfig default values"""
    config = ResilienceConfig()

    assert config.retry_max_attempts == 3
    assert config.retry_min_wait_seconds == 1.0
    assert config.retry_max_wait_seconds == 60.0
    assert config.retry_multiplier == 2.0

    assert config.circuit_failure_threshold == 5
    assert config.circuit_success_threshold == 2
    assert config.circuit_timeout_seconds == 60.0

    assert config.api_timeout_seconds == 10.0
    assert config.db_timeout_seconds == 5.0


def test_emergency_config_defaults():
    """Test EmergencyConfig default values"""
    config = EmergencyConfig()

    assert config.daily_loss_limit == -500.0
    assert config.max_position_size == 10000.0
    assert config.max_drawdown_percent == 20.0
    assert config.auto_halt_on_limit is True
    assert config.persist_state is True


def test_main_config_defaults():
    """Test main Config default values"""
    config = Config()

    assert config.env == Environment.DEVELOPMENT
    assert isinstance(config.state, StateConfig)
    assert isinstance(config.events, EventsConfig)
    assert isinstance(config.logging, LoggingConfig)
    assert isinstance(config.resilience, ResilienceConfig)
    assert isinstance(config.emergency, EmergencyConfig)


def test_config_custom_values():
    """Test creating config with custom values"""
    config = Config(
        env=Environment.PRODUCTION,
        state=StateConfig(
            backend="redis",
            redis_url="redis://prod.example.com:6379"
        ),
        logging=LoggingConfig(
            level="WARNING",
            format="json"
        )
    )

    assert config.env == Environment.PRODUCTION
    assert config.state.backend == "redis"
    assert config.state.redis_url == "redis://prod.example.com:6379"
    assert config.logging.level == "WARNING"
    assert config.logging.format == "json"


def test_get_development_config():
    """Test development configuration preset"""
    config = get_config("development")

    assert config.env == Environment.DEVELOPMENT
    assert config.state.backend == "memory"
    assert config.events.backend == "memory"
    assert config.logging.level == "DEBUG"
    assert config.logging.format == "console"
    assert config.logging.show_locals is True
    assert config.emergency.auto_halt_on_limit is False


def test_get_staging_config():
    """Test staging configuration preset"""
    config = get_config("staging")

    assert config.env == Environment.STAGING
    assert config.state.backend == "redis"
    assert config.events.backend == "redis"
    assert config.logging.level == "INFO"
    assert config.logging.format == "json"
    assert config.logging.show_locals is False
    assert config.emergency.auto_halt_on_limit is True


def test_get_production_config():
    """Test production configuration preset"""
    config = get_config("production")

    assert config.env == Environment.PRODUCTION
    assert config.state.backend == "redis"
    assert config.events.backend == "redis"
    assert config.logging.level == "INFO"
    assert config.logging.format == "json"
    assert config.logging.show_locals is False
    assert config.emergency.auto_halt_on_limit is True
    assert config.emergency.persist_state is True


def test_get_config_invalid_env():
    """Test get_config with invalid environment"""
    with pytest.raises(ValueError) as exc_info:
        get_config("invalid_env")

    assert "Unknown environment" in str(exc_info.value)


def test_resilience_config_validation():
    """Test ResilienceConfig validation"""
    # Valid config
    config = ResilienceConfig(
        retry_max_attempts=5,
        retry_min_wait_seconds=2.0,
        api_timeout_seconds=30.0
    )
    assert config.retry_max_attempts == 5

    # Invalid: max_attempts < 1
    with pytest.raises(Exception):  # Pydantic ValidationError
        ResilienceConfig(retry_max_attempts=0)

    # Invalid: negative timeout
    with pytest.raises(Exception):  # Pydantic ValidationError
        ResilienceConfig(api_timeout_seconds=-1.0)


def test_emergency_config_validation():
    """Test EmergencyConfig validation"""
    # Valid config
    config = EmergencyConfig(
        max_position_size=5000.0,
        max_drawdown_percent=15.0
    )
    assert config.max_position_size == 5000.0

    # Invalid: max_position_size <= 0
    with pytest.raises(Exception):  # Pydantic ValidationError
        EmergencyConfig(max_position_size=0)

    # Invalid: max_drawdown_percent > 100
    with pytest.raises(Exception):  # Pydantic ValidationError
        EmergencyConfig(max_drawdown_percent=150.0)


def test_nested_config_structure():
    """Test nested configuration structure"""
    config = Config()

    # Access nested values
    assert config.state.backend == "memory"
    assert config.events.backend == "memory"
    assert config.logging.level == "INFO"
    assert config.resilience.retry_max_attempts == 3
    assert config.emergency.daily_loss_limit == -500.0


def test_config_case_insensitive():
    """Test get_config is case-insensitive"""
    config1 = get_config("development")
    config2 = get_config("DEVELOPMENT")
    config3 = get_config("Development")

    assert config1.env == config2.env == config3.env
