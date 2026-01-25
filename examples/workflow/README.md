# Workflow Examples

Complete examples demonstrating the Enhanced Workflow Executor with infrastructure integration.

## Overview

These examples show how to use the production-ready workflow executor with:
- Real-time event emission
- Emergency halt controls
- Risk limit monitoring
- Circuit breakers and retry logic
- State persistence
- Concurrent execution

---

## Examples

### 1. Real-Time Trading Workflow (`realtime_trading_workflow.py`)

Demonstrates a complete BTC arbitrage trading workflow with real-time event monitoring.

**Features:**
- Multiple provider nodes (price feeds)
- Risk assessment and threshold checking
- Trade execution
- Real-time event monitoring via WebSocket-ready event bus
- Correlation ID tracking for debugging
- Event visualization with timestamps

**Run:**
```bash
python examples/workflow/realtime_trading_workflow.py
```

**Expected Output:**
```
🚀 EXECUTION STARTED
[  0.01s] ▶️  Starting: Binance BTC Price
[  0.13s] ✅ Completed: Binance BTC Price (119ms)
[  0.29s] ✅ Completed: Coinbase BTC Price (161ms)
🏁 EXECUTION COMPLETED
```

**Key Learnings:**
- How to create multi-node workflows
- How to subscribe to workflow events
- How to track execution with correlation IDs
- How events flow through the system in real-time

---

### 2. Emergency Halt Demonstrations (`emergency_halt_demo.py`)

Shows emergency controls and risk limit features.

**Scenarios:**
1. **Daily Loss Limit Exceeded** - Automatic halt when loss limit is breached
2. **Manual Emergency Halt** - User-initiated halt and resume
3. **Alert State** - Cautious trading mode (trading continues with warnings)

**Run:**
```bash
python examples/workflow/emergency_halt_demo.py
```

**Expected Output:**
```
DEMO 1: Daily Loss Limit Exceeded
🛑 RISK LIMIT EXCEEDED!
   Emergency State: halt
✅ EXECUTION BLOCKED BY EMERGENCY HALT

DEMO 2: Manual Emergency Halt and Resume
🛑 Triggering manual emergency halt...
✅ EXECUTION BLOCKED
✅ Resuming normal operations...
✅ EXECUTION SUCCEEDED

DEMO 3: Alert State (Cautious Trading)
⚠️  Setting alert state...
✅ EXECUTION SUCCEEDED IN ALERT STATE
```

**Key Learnings:**
- How risk limits protect trading capital
- How to manually halt and resume trading
- How emergency events are emitted
- Different emergency states (NORMAL, ALERT, HALT, SHUTDOWN)

---

### 3. Concurrent Workflows (`concurrent_workflows.py`)

Demonstrates running multiple workflows simultaneously with shared infrastructure.

**Features:**
- 5 concurrent workflows for different trading pairs
- Shared event bus for all workflows
- Shared emergency controller
- Performance metrics
- Event aggregation across workflows

**Run:**
```bash
python examples/workflow/concurrent_workflows.py
```

**Expected Output:**
```
🚀 Launching 5 concurrent workflows...
Trading Pairs:
  - BTC/USD (delay: 0.0s)
  - ETH/USD (delay: 0.1s)
  - SOL/USD (delay: 0.2s)
  - MATIC/USD (delay: 0.3s)
  - AVAX/USD (delay: 0.4s)

📊 EXECUTION RESULTS
✅ BTC/USD: completed (131.80ms)
✅ ETH/USD: completed (92.47ms)
✅ SOL/USD: completed (144.01ms)
✅ MATIC/USD: completed (143.23ms)
✅ AVAX/USD: completed (133.29ms)

Summary:
  Total: 5
  Avg Time per Workflow: 0.11s

📈 EVENT SUMMARY
Total Workflows: 5
Total Events: 85
```

**Key Learnings:**
- How to run multiple workflows concurrently
- How workflows share infrastructure (event bus, state store, emergency controller)
- How emergency halt affects all running workflows
- Performance characteristics of concurrent execution

---

### 4. Performance Benchmarks (`performance_benchmark.py`)

Measures performance characteristics and provides baseline metrics.

**Benchmarks:**
1. Single workflow execution overhead
2. Event emission overhead
3. Concurrent workflow throughput
4. State persistence latency

**Run:**
```bash
python examples/workflow/performance_benchmark.py
```

**Expected Output:**
```
BENCHMARK: Single Workflow Execution
Results:
  Mean: 0.61ms
  Median: 0.58ms
  P95: 0.89ms
  P99: 1.12ms

BENCHMARK: Concurrent Workflow Throughput
Testing concurrency level: 50
  Throughput: 1036.26 workflows/sec

Summary:
  - Single execution overhead: ~1-5ms
  - Event emission: Minimal overhead (<1ms)
  - Concurrent throughput: Scales well with concurrency
  - State persistence: In-memory backend has minimal overhead
```

**Key Learnings:**
- Baseline performance metrics for production
- How execution time scales with concurrency
- Overhead of infrastructure features
- Memory backend vs Redis backend performance differences

---

## Architecture Features Demonstrated

### Event System
All examples show real-time event emission:
- `execution_started` - Workflow begins
- `node_started` - Node execution begins
- `node_completed` - Node succeeds
- `node_failed` - Node fails
- `execution_completed` - Workflow completes
- `execution_halted` - Emergency halt triggered

### Emergency Controls
Examples show all emergency states:
- **NORMAL** - Normal operation
- **ALERT** - Warning state, trading continues
- **HALT** - Emergency halt, no new trades
- **SHUTDOWN** - Complete shutdown

### Resilience Patterns
All examples benefit from:
- **Circuit Breakers** - Protect against API failures
- **Retry Logic** - Automatic recovery from transient failures
- **Timeout Handling** - Prevent hanging operations
- **State Persistence** - Resume after restarts

---

## Production Deployment

These examples use the development configuration. For production:

```python
# Use production config
infra = await Infrastructure.create("production")

# Production config differences:
# - Redis backend for state and events
# - Longer timeouts (120s vs 60s)
# - More retry attempts (3 vs 2)
# - Higher circuit breaker thresholds (10 vs 5)
# - JSON log format for parsing
```

---

## WebSocket Integration

The real-time trading workflow example shows events ready for WebSocket consumption:

```python
# In your WebSocket server (from Week 3 Day 2)
from src.web.run_websocket_server import WorkflowWebSocketServer

# Events are automatically forwarded to connected clients
# Clients receive events in real-time for UI updates
```

See `src/web/websocket_server.py` and `examples/websocket_test_client.html` for WebSocket integration.

---

## Next Steps

After running these examples:

1. **Create Your Own Workflows** - Use these as templates
2. **Add Custom Nodes** - Extend with domain-specific logic
3. **Integrate with UI** - Connect WebSocket server to dashboard
4. **Deploy to Production** - Use production config and Redis backends
5. **Monitor Performance** - Use benchmarks to set baselines

---

## Troubleshooting

### "Unknown node category" Error
Workflow nodes must use valid categories:
- `providers` - External data sources (price feeds, APIs)
- `triggers` - Event triggers
- `conditions` - Decision points
- `actions` - Trade executions, notifications
- `risk` - Risk calculations

### "Emergency controller is in halt state"
Your previous test triggered emergency halt. Reset:
```python
await infra.emergency.resume("Manual reset")
```

### Slow Performance
Check configuration:
- Use production config for realistic timings
- In-memory backends are fastest for testing
- Redis backends add network latency but provide persistence

---

## Additional Resources

- **Week 3 Day 1 Summary**: Infrastructure integration details
- **Week 3 Day 2 Summary**: WebSocket server documentation
- **Week 3 Day 3 Summary**: Resilience patterns testing
- **Integration Tests**: `tests/integration/test_workflow_resilience.py`
- **Manual Tests**: `manual_resilience_tests.py`

---

## Support

Questions or issues? Check:
1. Week 3 summaries in project root
2. Integration tests for usage examples
3. Infrastructure documentation in `src/infrastructure/`

Happy workflow building! 🚀
