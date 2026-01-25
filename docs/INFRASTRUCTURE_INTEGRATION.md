# Infrastructure Integration Guide

Complete guide for integrating Week 2 infrastructure with your workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Infrastructure Components](#infrastructure-components)
4. [Event System](#event-system)
5. [Emergency Controls](#emergency-controls)
6. [State Persistence](#state-persistence)
7. [Resilience Patterns](#resilience-patterns)
8. [Configuration](#configuration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Enhanced Workflow Executor integrates production-ready infrastructure from Week 2:

- **Event Bus** - Real-time event emission for UI updates
- **State Store** - Persistent state across restarts
- **Emergency Controller** - Risk limits and manual halt controls
- **Resilience** - Circuit breakers, retries, timeouts
- **Logging** - Structured logging with correlation IDs

### Benefits

✅ **Observability** - Real-time events for monitoring
✅ **Safety** - Risk limits protect trading capital
✅ **Reliability** - Automatic recovery from failures
✅ **Traceability** - Correlation IDs track executions
✅ **Production-Ready** - Battle-tested patterns

---

## Quick Start

### 1. Create Infrastructure

```python
from src.infrastructure.factory import Infrastructure

# Create infrastructure instance
infra = await Infrastructure.create("development")
```

### 2. Create Enhanced Executor

```python
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor

executor = EnhancedWorkflowExecutor(
    workflow=your_workflow_definition,
    infra=infra,
    workflow_id="arb_btc_001",
    bot_id="bot_001",
    strategy_id="arbitrage_btc"
)
```

### 3. Subscribe to Events

```python
async def handle_event(event: dict):
    print(f"Event: {event['type']} - {event.get('node_id')}")

await infra.events.subscribe("workflow_events", handle_event)
```

### 4. Execute Workflow

```python
await executor.initialize()
result = await executor.execute()
```

That's it! Your workflow now has:
- ✅ Real-time event emission
- ✅ Emergency halt protection
- ✅ State persistence
- ✅ Circuit breakers and retries
- ✅ Correlation ID tracking

---

## Infrastructure Components

### Infrastructure Factory

Central factory for creating infrastructure instances:

```python
from src.infrastructure.factory import Infrastructure

# Development (in-memory backends)
infra_dev = await Infrastructure.create("development")

# Production (Redis backends)
infra_prod = await Infrastructure.create("production")

# Custom config
from src.infrastructure.config import InfrastructureConfig
custom_config = InfrastructureConfig(...)
infra_custom = await Infrastructure.create("development", config=custom_config)
```

### Available Components

```python
# Access infrastructure components
infra.events          # Event bus
infra.state           # State store
infra.emergency       # Emergency controller
infra.config          # Configuration
infra.create_circuit_breaker()  # Create circuit breakers
```

---

## Event System

### Event Types

The executor emits these events:

**Execution Events:**
- `execution_started` - Workflow begins
- `execution_completed` - Workflow completes successfully
- `execution_failed` - Workflow fails
- `execution_halted` - Emergency halt triggered

**Node Events:**
- `node_started` - Node execution begins
- `node_completed` - Node succeeds
- `node_failed` - Node fails

### Event Schema

**execution_started:**
```json
{
  "type": "execution_started",
  "execution_id": "exec_arb_btc_001_abc123",
  "workflow_id": "arb_btc_001",
  "bot_id": "bot_001",
  "strategy_id": "arbitrage_btc",
  "timestamp": "2026-01-25T10:15:23.456Z",
  "node_count": 5
}
```

**node_completed:**
```json
{
  "type": "node_completed",
  "execution_id": "exec_arb_btc_001_abc123",
  "workflow_id": "arb_btc_001",
  "node_id": "price_binance",
  "node_name": "Binance Price Feed",
  "node_category": "providers",
  "timestamp": "2026-01-25T10:15:23.501Z",
  "duration_ms": 45.2,
  "status": "success",
  "outputs": {
    "price": 50234.56,
    "volume": 1234.56
  }
}
```

### Subscribing to Events

```python
# Subscribe to all workflow events
async def my_handler(event: dict):
    event_type = event.get("type")

    if event_type == "execution_started":
        print(f"Workflow {event['workflow_id']} started")

    elif event_type == "node_completed":
        print(f"Node {event['node_id']} completed in {event['duration_ms']}ms")

await infra.events.subscribe("workflow_events", my_handler)
```

### Filtering Events

```python
async def filter_by_bot(event: dict):
    # Only handle events for specific bot
    if event.get("bot_id") == "bot_001":
        await process_event(event)

await infra.events.subscribe("workflow_events", filter_by_bot)
```

---

## Emergency Controls

### Emergency States

- **NORMAL** - Normal operation, all systems go
- **ALERT** - Warning state, trading continues with caution
- **HALT** - Emergency halt, no new trades allowed
- **SHUTDOWN** - Complete shutdown, cease all operations

### Manual Controls

```python
# Manual emergency halt
await infra.emergency.halt("Suspicious market activity detected")

# Set alert state
await infra.emergency.alert(
    "High volatility detected",
    volatility_index=85.5
)

# Resume normal operations
await infra.emergency.resume("Market conditions normalized")

# Complete shutdown
await infra.emergency.shutdown("End of trading day")
```

### Risk Limits

```python
# Check risk limit
daily_pnl = -450.0
daily_loss_limit = -500.0

try:
    await infra.emergency.check_risk_limit(
        "daily_loss",
        daily_pnl,
        daily_loss_limit,
        auto_halt=True  # Automatically halt if exceeded
    )
except RiskLimitExceeded as e:
    print(f"Risk limit exceeded: {e.limit_type}")
    # Emergency controller is now in HALT state
```

### Emergency Event Subscriptions

```python
from src.infrastructure.emergency import EmergencyEvent

async def on_emergency(event: EmergencyEvent):
    print(f"Emergency: {event.previous_state} → {event.new_state}")
    print(f"Reason: {event.reason}")

    # Send alert to operations team
    await send_alert(event)

await infra.emergency.subscribe(on_emergency)
```

### Querying Emergency Status

```python
status = infra.emergency.get_status()

print(f"State: {status['state']}")
print(f"Can Trade: {status['can_trade']}")
print(f"Can Operate: {status['can_operate']}")

# Risk limits
for limit_name, limit_data in status['risk_limits'].items():
    utilization = limit_data['utilization'] * 100
    print(f"{limit_name}: {utilization:.1f}% utilized")
```

---

## State Persistence

### Automatic State Persistence

The executor automatically persists:

```python
# Execution status
f"workflow:{workflow_id}:execution:{execution_id}:status"

# Execution result
f"workflow:{workflow_id}:execution:{execution_id}:result"

# Latest execution
f"workflow:{workflow_id}:latest_execution"
```

### Manual State Operations

```python
# Store state
await infra.state.set("my_key", {"data": "value"})

# Retrieve state
value = await infra.state.get("my_key")

# Delete state
await infra.state.delete("my_key")

# Check existence
exists = await infra.state.exists("my_key")
```

### Execution History

```python
# Get execution history
history = await executor.get_execution_history(limit=10)

for execution in history:
    print(f"{execution['execution_id']}: {execution['status']}")
```

---

## Resilience Patterns

### Circuit Breakers

Automatically created for each workflow:

```python
# Access workflow's circuit breaker
breaker = executor.api_breaker

# Get statistics
stats = breaker.get_stats()
print(f"State: {stats['state']}")
print(f"Failures: {stats['failure_count']}/{stats['failure_threshold']}")

# Manual controls
await breaker.force_open()   # Manually open breaker
await breaker.force_close()  # Manually close breaker
await breaker.reset()        # Reset failure count
```

### Retry Logic

Provider nodes automatically retry with exponential backoff:

```python
# Configuration (from ResilienceConfig)
retry_max_attempts: 2          # Development
retry_max_attempts: 3          # Production
retry_min_wait_seconds: 1.0
retry_max_wait_seconds: 60.0

# Retries on: ConnectionError, TimeoutError
```

### Timeout Handling

All nodes have configurable timeouts:

```python
# In workflow definition
{
    "id": "slow_api",
    "name": "Slow API Call",
    "category": "providers",
    "timeout": 30.0  # 30 second timeout
}

# Default timeout: 30 seconds
```

---

## Configuration

### Environment Configurations

**Development:**
```python
config = InfrastructureConfig(
    state_backend="memory",
    events_backend="memory",
    log_format="console",
    resilience=ResilienceConfig(
        retry_max_attempts=2,
        circuit_failure_threshold=5,
        circuit_timeout_seconds=60.0
    ),
    emergency=EmergencyConfig(
        daily_loss_limit=-100.0
    )
)
```

**Production:**
```python
config = InfrastructureConfig(
    state_backend="redis",
    events_backend="redis",
    log_format="json",
    redis_url="redis://localhost:6379/0",
    resilience=ResilienceConfig(
        retry_max_attempts=3,
        circuit_failure_threshold=10,
        circuit_timeout_seconds=120.0
    ),
    emergency=EmergencyConfig(
        daily_loss_limit=-500.0
    )
)
```

### Custom Configuration

```python
from src.infrastructure.config import (
    InfrastructureConfig,
    ResilienceConfig,
    EmergencyConfig
)

custom_config = InfrastructureConfig(
    state_backend="redis",
    redis_url="redis://my-redis:6379/1",
    resilience=ResilienceConfig(
        retry_max_attempts=5,
        retry_min_wait_seconds=0.5,
        retry_max_wait_seconds=30.0,
        circuit_failure_threshold=15,
        circuit_timeout_seconds=180.0
    ),
    emergency=EmergencyConfig(
        daily_loss_limit=-1000.0,
        max_position_size=50000.0,
        max_drawdown_percent=15.0
    )
)

infra = await Infrastructure.create("production", config=custom_config)
```

---

## Best Practices

### 1. Always Use Infrastructure Factory

✅ **Good:**
```python
infra = await Infrastructure.create("development")
executor = EnhancedWorkflowExecutor(workflow, infra, ...)
```

❌ **Bad:**
```python
# Don't create components manually
from src.infrastructure.state import MemoryStateStore
state = MemoryStateStore()  # Missing initialization
```

### 2. Subscribe to Events Early

✅ **Good:**
```python
# Subscribe before executing workflows
await infra.events.subscribe("workflow_events", handler)
await executor.execute()
```

❌ **Bad:**
```python
# Don't subscribe after execution
await executor.execute()
await infra.events.subscribe("workflow_events", handler)  # Missed events
```

### 3. Use Correlation IDs for Debugging

```python
from src.infrastructure.logging import get_correlation_id

async def my_handler(event):
    corr_id = event.get("execution_id")
    # Search logs by correlation ID to find all related messages
```

### 4. Handle Emergency States

✅ **Good:**
```python
try:
    await executor.execute()
except EmergencyHalted as e:
    logger.critical(f"Trading halted: {e.reason}")
    await notify_operations_team(e)
```

❌ **Bad:**
```python
try:
    await executor.execute()
except Exception:
    pass  # Don't suppress emergency halts
```

### 5. Monitor Circuit Breaker States

```python
# Periodic health check
stats = executor.api_breaker.get_stats()
if stats["state"] == "OPEN":
    logger.warning("Circuit breaker open - API unavailable")
```

### 6. Use Appropriate Configuration

```python
# Development: Fast feedback, verbose logging
infra_dev = await Infrastructure.create("development")

# Production: Resilience, performance, JSON logs
infra_prod = await Infrastructure.create("production")
```

---

## Troubleshooting

### "Emergency controller is in halt state"

**Cause:** Previous workflow triggered emergency halt

**Solution:**
```python
# Check emergency status
status = infra.emergency.get_status()
print(f"State: {status['state']}, Reason: {status['halt_reason']}")

# Resume if appropriate
await infra.emergency.resume("Issue resolved")
```

### "Circuit breaker is open"

**Cause:** Too many API failures

**Solution:**
```python
# Check breaker stats
stats = executor.api_breaker.get_stats()
print(f"Failures: {stats['failure_count']}")

# Wait for recovery or manually reset
await asyncio.sleep(60)  # Wait for time window
await executor.api_breaker.reset()  # Or manually reset
```

### Events Not Received

**Causes:**
1. Subscribed after execution
2. Event handler errors
3. Wrong channel name

**Solution:**
```python
# Subscribe early
await infra.events.subscribe("workflow_events", handler)

# Add error handling to handler
async def safe_handler(event):
    try:
        await process_event(event)
    except Exception as e:
        logger.error(f"Event handler error: {e}")
```

### Slow Performance

**Causes:**
1. Network latency (Redis backends)
2. Many concurrent workflows
3. Long-running nodes

**Solutions:**
```python
# Use in-memory for testing
infra = await Infrastructure.create("development")

# Adjust timeouts
node["timeout"] = 60.0  # Increase timeout

# Monitor performance
result = await executor.execute()
print(f"Duration: {result['duration']}ms")
```

---

## See Also

- [Week 3 Day 1 Summary](../WEEK_3_DAY_1_SUMMARY.md) - Infrastructure integration details
- [Week 3 Day 2 Summary](../WEEK_3_DAY_2_SUMMARY.md) - WebSocket server
- [Week 3 Day 3 Summary](../WEEK_3_DAY_3_SUMMARY.md) - Resilience testing
- [Week 3 Day 4 Summary](../WEEK_3_DAY_4_SUMMARY.md) - Examples and benchmarks
- [Example Workflows](../examples/workflow/) - Production-ready templates
- [Configuration Reference](./CONFIGURATION.md) - Configuration options

---

## Support

For questions or issues:
1. Check example workflows in `examples/workflow/`
2. Review integration tests in `tests/integration/`
3. See Week 3 summaries for detailed documentation

Happy integrating! 🚀
