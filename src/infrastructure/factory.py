"""
Infrastructure Factory

Unified factory for creating infrastructure components with configuration.
"""

from typing import Optional
from .config import Config, get_config
from .state import StateStore, create_state_store
from .events import EventBus, create_event_bus
from .logging import configure_logging
from .emergency import EmergencyController
from .resilience import CircuitBreaker
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class Infrastructure:
    """
    Infrastructure components container.

    Provides easy access to all infrastructure components with
    configuration applied.

    Usage:
        # Create infrastructure with default config
        infra = await Infrastructure.create()

        # Create infrastructure for specific environment
        infra = await Infrastructure.create("production")

        # Use components
        await infra.state.set("key", "value")
        await infra.events.publish("channel", {"event": "data"})
        await infra.emergency.assert_can_trade()

        # Clean up
        await infra.close()
    """

    def __init__(
        self,
        config: Config,
        state: StateStore,
        events: EventBus,
        emergency: EmergencyController
    ):
        """
        Initialize infrastructure container.

        Args:
            config: Configuration instance
            state: State store instance
            events: Event bus instance
            emergency: Emergency controller instance
        """
        self.config = config
        self.state = state
        self.events = events
        self.emergency = emergency

        # Circuit breakers for common services
        self.circuit_breakers = {
            "state": CircuitBreaker(
                "state_store",
                failure_threshold=config.resilience.circuit_failure_threshold,
                timeout_seconds=config.resilience.circuit_timeout_seconds
            ),
            "events": CircuitBreaker(
                "event_bus",
                failure_threshold=config.resilience.circuit_failure_threshold,
                timeout_seconds=config.resilience.circuit_timeout_seconds
            ),
        }

        logger.info(
            "infrastructure_initialized",
            env=config.env.value,
            state_backend=config.state.backend,
            events_backend=config.events.backend,
            log_format=config.logging.format
        )

    @classmethod
    async def create(
        cls,
        env: Optional[str] = None,
        config: Optional[Config] = None,
        controller_id: str = "default"
    ) -> "Infrastructure":
        """
        Create infrastructure with configuration.

        Args:
            env: Environment name (development/staging/production)
                 Ignored if config is provided
            config: Explicit configuration instance
                    If None, loads from environment or env parameter
            controller_id: Emergency controller ID

        Returns:
            Infrastructure instance

        Usage:
            # Development (in-memory)
            infra = await Infrastructure.create("development")

            # Production (Redis)
            infra = await Infrastructure.create("production")

            # Custom config
            config = Config(...)
            infra = await Infrastructure.create(config=config)
        """
        # Load configuration
        if config is None:
            config = get_config(env)

        # Configure logging
        configure_logging(
            level=config.logging.level,
            format=config.logging.format,
            add_correlation_id=config.logging.add_correlation_id,
            show_locals=config.logging.show_locals
        )

        # Create state store
        state = create_state_store(
            backend=config.state.backend,
            url=config.state.redis_url if config.state.backend == "redis" else None
        )

        # Create event bus
        events = create_event_bus(
            backend=config.events.backend,
            url=config.events.redis_url if config.events.backend == "redis" else None
        )

        # Start event bus listener
        await events.start_listening()

        # Create emergency controller
        emergency = EmergencyController(controller_id)

        # Restore emergency state if enabled
        if config.emergency.persist_state:
            await emergency.restore_state(state)

        return cls(
            config=config,
            state=state,
            events=events,
            emergency=emergency
        )

    async def close(self):
        """
        Close all infrastructure components.

        Call this before shutting down the application.

        Usage:
            infra = await Infrastructure.create()
            try:
                # ... use infrastructure ...
            finally:
                await infra.close()
        """
        logger.info("infrastructure_shutting_down")

        # Persist emergency state
        if self.config.emergency.persist_state:
            await self.emergency.persist_state(self.state)

        # Close event bus
        await self.events.close()

        # Close state store
        await self.state.close()

        logger.info("infrastructure_shutdown_complete")

    def create_circuit_breaker(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> CircuitBreaker:
        """
        Create a circuit breaker with configuration defaults.

        Args:
            name: Circuit breaker name
            failure_threshold: Override default failure threshold
            timeout_seconds: Override default timeout

        Returns:
            CircuitBreaker instance

        Usage:
            api_breaker = infra.create_circuit_breaker("exchange_api")
            result = await api_breaker.call(exchange.get_price, "BTC-USDT")
        """
        return CircuitBreaker(
            name,
            failure_threshold=failure_threshold or self.config.resilience.circuit_failure_threshold,
            success_threshold=self.config.resilience.circuit_success_threshold,
            timeout_seconds=timeout_seconds or self.config.resilience.circuit_timeout_seconds,
            window_seconds=self.config.resilience.circuit_window_seconds
        )

    async def health_check(self) -> dict:
        """
        Perform health check on infrastructure components.

        Returns:
            Dictionary with health status

        Usage:
            health = await infra.health_check()
            print(health)
        """
        health = {
            "status": "healthy",
            "components": {}
        }

        # Check state store
        try:
            await self.state.set("health_check", "ok")
            await self.state.get("health_check")
            health["components"]["state"] = "healthy"
        except Exception as e:
            health["components"]["state"] = f"unhealthy: {str(e)}"
            health["status"] = "degraded"

        # Check event bus
        try:
            await self.events.publish("health_check", {"status": "ok"})
            health["components"]["events"] = "healthy"
        except Exception as e:
            health["components"]["events"] = f"unhealthy: {str(e)}"
            health["status"] = "degraded"

        # Check emergency controller
        health["components"]["emergency"] = {
            "state": self.emergency.state.value,
            "can_trade": self.emergency.can_trade()
        }
        if not self.emergency.can_trade():
            health["status"] = "halted"

        # Check circuit breakers
        health["components"]["circuit_breakers"] = {
            name: {
                "state": breaker.state.value,
                "failures": breaker._failure_count
            }
            for name, breaker in self.circuit_breakers.items()
        }

        return health


async def create_infrastructure(
    env: Optional[str] = None,
    config: Optional[Config] = None,
    controller_id: str = "default"
) -> Infrastructure:
    """
    Convenience function to create infrastructure.

    Args:
        env: Environment name (development/staging/production)
        config: Explicit configuration instance
        controller_id: Emergency controller ID

    Returns:
        Infrastructure instance

    Usage:
        # Quick setup for development
        infra = await create_infrastructure("development")

        # Quick setup for production
        infra = await create_infrastructure("production")
    """
    return await Infrastructure.create(env, config, controller_id)
