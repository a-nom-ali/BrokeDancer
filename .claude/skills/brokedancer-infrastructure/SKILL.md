---
name: brokedancer-infrastructure
description: |
  Production infrastructure for BrokeDancer: state management, event bus, logging, resilience patterns, and emergency controls. Use when:
  (1) Adding state persistence (memory/Redis)
  (2) Working with event pub/sub system
  (3) Implementing retry, circuit breaker, or timeout patterns
  (4) Configuring structured logging with correlation IDs
  (5) Managing emergency halt states and risk limits
  Cross-cutting concerns used by all other layers.
---

# BrokeDancer Infrastructure Layer

## Quick Reference

**Factory** (`src/infrastructure/factory.py`):
```python
from src.infrastructure.factory import Infrastructure

infra = await Infrastructure.create()
# Access components:
infra.state      # StateStore
infra.events     # EventBus
infra.logger     # StructuredLogger
infra.emergency  # EmergencyController
```

## State Management

**Interface** (`src/infrastructure/state/base.py`):
```python
class StateStore(ABC):
    async def get(key: str) -> Optional[Any]
    async def set(key: str, value: Any, ttl: int = None)
    async def delete(key: str) -> bool
    async def clear() -> None
    async def list_keys(pattern: str = "*") -> List[str]
```

**Implementations**:
- `MemoryStateStore`: In-memory (default, dev)
- `RedisStateStore`: Redis backend (production)

```python
# Usage
await state.set("bot:123:status", "running", ttl=3600)
status = await state.get("bot:123:status")
```

## Event Bus

**Interface** (`src/infrastructure/events/base.py`):
```python
class EventBus(ABC):
    async def publish(topic: str, message: Dict)
    async def subscribe(topic: str, callback: Callable) -> str
    async def unsubscribe(subscription_id: str)
```

**Implementations**:
- `MemoryEventBus`: In-memory (default)
- `RedisEventBus`: Redis pub/sub (distributed)

```python
# Publish
await events.publish("trade.executed", {"bot_id": "123", "profit": 10.5})

# Subscribe (pattern matching)
await events.subscribe("trade.*", handle_trade)
await events.subscribe("bot.123.*", handle_bot_events)
```

## Resilience Patterns

**Retry** (`src/infrastructure/resilience/retry.py`):
```python
from src.infrastructure.resilience.retry import retry_with_backoff

@retry_with_backoff(max_attempts=3, initial_delay=1.0)
async def fetch_data():
    ...
```

**Circuit Breaker** (`src/infrastructure/resilience/circuit_breaker.py`):
```python
from src.infrastructure.resilience.circuit_breaker import circuit_breaker

@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def external_api_call():
    ...
```

**Timeout** (`src/infrastructure/resilience/timeout.py`):
```python
from src.infrastructure.resilience.timeout import with_timeout

@with_timeout(seconds=30)
async def long_operation():
    ...
```

## Logging

**Structured Logger** (`src/infrastructure/logging/`):
```python
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)
logger.info("Trade executed", extra={
    "bot_id": "123",
    "profit": 10.5,
    "correlation_id": "abc-123"
})
```

Features:
- JSON output for production
- Correlation IDs for request tracing
- Sensitive value masking
- Log levels: DEBUG, INFO, WARNING, ERROR

## Emergency Controls

**Controller** (`src/infrastructure/emergency/controller.py`):
```python
from src.infrastructure.emergency.controller import EmergencyController

emergency = EmergencyController()

# States: RUNNING, PAUSED, HALTED, EMERGENCY
await emergency.pause()           # Stop new trades
await emergency.halt()            # Stop all activity
await emergency.emergency_halt()  # Immediate shutdown
await emergency.resume()          # Back to normal

# Risk checks
emergency.check_daily_loss(current_loss)   # Raises if exceeded
emergency.check_position_size(size)        # Raises if exceeded
emergency.check_trade_frequency(count)     # Raises if exceeded
```

**Risk Limits**:
```python
{
    "max_daily_loss": 1000,        # USD
    "max_position_size": 10000,    # USD
    "max_trades_per_hour": 100
}
```

## Configuration

**Settings** (`src/infrastructure/config/config.py`):
```python
from src.infrastructure.config import InfrastructureConfig

config = InfrastructureConfig(
    state_backend="redis",         # "memory" or "redis"
    redis_url="redis://localhost:6379",
    event_backend="redis",
    log_format="json",             # "json" or "console"
    log_level="INFO"
)
```

## Testing

```bash
# Run all infrastructure tests (109 tests)
pytest tests/infrastructure/ -v

# Specific component
pytest tests/infrastructure/test_state_store.py -v
pytest tests/infrastructure/test_event_bus.py -v
pytest tests/infrastructure/test_resilience.py -v
pytest tests/infrastructure/test_emergency.py -v
```

## Directory Structure

```
src/infrastructure/
├── config/           # Configuration
│   └── config.py
├── state/            # State persistence
│   ├── base.py
│   ├── memory.py
│   └── redis_store.py
├── events/           # Event pub/sub
│   ├── base.py
│   ├── memory.py
│   └── redis_bus.py
├── logging/          # Structured logging
│   ├── config.py
│   └── logger.py
├── resilience/       # Fault tolerance
│   ├── retry.py
│   ├── circuit_breaker.py
│   └── timeout.py
├── emergency/        # Safety controls
│   └── controller.py
└── factory.py        # Unified initialization
```
