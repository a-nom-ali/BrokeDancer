# Migration Guide: Base Executor → Enhanced Executor

Guide for migrating existing workflows from `WorkflowExecutor` to `EnhancedWorkflowExecutor`.

---

## Table of Contents

1. [Why Migrate?](#why-migrate)
2. [What Changes?](#what-changes)
3. [Migration Steps](#migration-steps)
4. [Before and After Examples](#before-and-after-examples)
5. [Breaking Changes](#breaking-changes)
6. [Testing Your Migration](#testing-your-migration)
7. [Rollback Plan](#rollback-plan)

---

## Why Migrate?

### Benefits of Enhanced Executor

✅ **Real-Time Observability**
- Event emission for UI updates
- WebSocket-ready event format
- Correlation ID tracking

✅ **Production Safety**
- Emergency halt controls
- Risk limit monitoring
- Automatic halt on limit breach

✅ **Reliability**
- Circuit breakers for API calls
- Automatic retries with exponential backoff
- Timeout handling

✅ **State Management**
- Automatic state persistence
- Execution history tracking
- Resume after restarts

✅ **Structured Logging**
- JSON format for production
- Correlation IDs for tracing
- Context-aware logging

---

## What Changes?

### Minimal Code Changes Required

The enhanced executor is **backward compatible** with existing workflows. Migration requires only:

1. Create infrastructure instance
2. Pass infrastructure to executor constructor
3. Add workflow/bot/strategy IDs

That's it! No workflow definition changes needed.

### What Stays the Same

✅ Workflow definition format (unchanged)
✅ Node execution logic (unchanged)
✅ Topological sorting (unchanged)
✅ Node categories (providers, triggers, conditions, actions, risk)

### What's New

🆕 Infrastructure integration
🆕 Event emission
🆕 Emergency controls
🆕 Circuit breakers
🆕 State persistence

---

## Migration Steps

### Step 1: Create Infrastructure

**Before:**
```python
from src.workflow.executor import WorkflowExecutor

executor = WorkflowExecutor(workflow_definition)
await executor.initialize()
result = await executor.execute()
```

**After:**
```python
from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor

# Create infrastructure
infra = await Infrastructure.create("development")

# Create enhanced executor
executor = EnhancedWorkflowExecutor(
    workflow=workflow_definition,
    infra=infra,
    workflow_id="arb_btc_001",
    bot_id="bot_001",  # Optional
    strategy_id="arbitrage_btc"  # Optional
)

await executor.initialize()
result = await executor.execute()
```

### Step 2: Subscribe to Events (Optional)

```python
# Subscribe to workflow events for monitoring
async def handle_event(event: dict):
    print(f"Event: {event['type']} - {event.get('node_id')}")

await infra.events.subscribe("workflow_events", handle_event)
```

### Step 3: Handle Emergency States (Recommended)

```python
from src.infrastructure.emergency import EmergencyHalted

try:
    result = await executor.execute()
except EmergencyHalted as e:
    logger.critical(f"Trading halted: {e.reason}")
    # Notify operations team
```

---

## Before and After Examples

### Example 1: Simple Trading Bot

**Before (Base Executor):**
```python
from src.workflow.executor import WorkflowExecutor

# Create executor
executor = WorkflowExecutor(trading_workflow)

# Initialize
await executor.initialize()

# Execute
result = await executor.execute()

# Check result
if result['status'] == 'completed':
    print("Trading workflow completed")
```

**After (Enhanced Executor):**
```python
from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor
from src.infrastructure.emergency import EmergencyHalted

# Create infrastructure (once, reuse across workflows)
infra = await Infrastructure.create("production")

# Subscribe to events
async def log_events(event):
    logger.info(f"{event['type']}: {event.get('node_id')}")

await infra.events.subscribe("workflow_events", log_events)

# Create executor
executor = EnhancedWorkflowExecutor(
    workflow=trading_workflow,
    infra=infra,
    workflow_id="trade_001",
    bot_id="trading_bot_001",
    strategy_id="mean_reversion"
)

# Initialize
await executor.initialize()

# Execute with emergency handling
try:
    result = await executor.execute()

    if result['status'] == 'completed':
        print("Trading workflow completed")

except EmergencyHalted as e:
    logger.critical(f"Emergency halt: {e.reason}")
```

### Example 2: Multiple Concurrent Workflows

**Before (Base Executor):**
```python
# Execute workflows sequentially
for workflow_def in workflows:
    executor = WorkflowExecutor(workflow_def)
    await executor.initialize()
    result = await executor.execute()
```

**After (Enhanced Executor):**
```python
# Create shared infrastructure
infra = await Infrastructure.create("production")

# Execute workflows concurrently
async def run_workflow(workflow_def, workflow_id):
    executor = EnhancedWorkflowExecutor(
        workflow=workflow_def,
        infra=infra,
        workflow_id=workflow_id,
        bot_id="multi_bot",
        strategy_id="concurrent_strategy"
    )
    await executor.initialize()
    return await executor.execute()

# Run all workflows concurrently
tasks = [
    run_workflow(wf, f"wf_{i}")
    for i, wf in enumerate(workflows)
]

results = await asyncio.gather(*tasks)
```

### Example 3: With Risk Limits

**Before (Base Executor):**
```python
# Manual risk checking
daily_pnl = calculate_daily_pnl()
if daily_pnl < -500:
    raise Exception("Daily loss limit exceeded")

executor = WorkflowExecutor(trading_workflow)
result = await executor.execute()
```

**After (Enhanced Executor):**
```python
# Automatic risk limit checking
infra = await Infrastructure.create("production")

# Set up risk limits
daily_pnl = calculate_daily_pnl()

try:
    await infra.emergency.check_risk_limit(
        "daily_loss",
        daily_pnl,
        -500.0,
        auto_halt=True
    )

    executor = EnhancedWorkflowExecutor(
        workflow=trading_workflow,
        infra=infra,
        workflow_id="trade_001"
    )

    result = await executor.execute()

except RiskLimitExceeded as e:
    logger.critical(f"Risk limit exceeded: {e.limit_type}")
    # Emergency controller is now in HALT state
    # All subsequent trades will be blocked
except EmergencyHalted as e:
    logger.critical(f"Trading halted: {e.reason}")
```

---

## Breaking Changes

### None!

The enhanced executor is **fully backward compatible**. Your existing workflows will work without modification.

### API Additions (Not Breaking)

**New Required Parameters:**
- `infra`: Infrastructure instance
- `workflow_id`: Unique workflow identifier

**New Optional Parameters:**
- `bot_id`: Bot identifier (for grouping/filtering)
- `strategy_id`: Strategy identifier (for grouping/filtering)

**New Exception:**
- `EmergencyHalted`: Raised when emergency controller blocks execution

### Workflow Definition (Unchanged)

Your workflow definitions require **no changes**:

```python
# This works with both base and enhanced executors
workflow = {
    "blocks": [
        {
            "id": "node1",
            "name": "My Node",
            "category": "providers",
            "type": "api_call",
            "properties": {},
            "config": {},
            "inputs": {},
            "outputs": ["result"]
        }
    ]
}
```

---

## Testing Your Migration

### 1. Unit Tests

```python
import pytest
from src.infrastructure.factory import Infrastructure
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor

@pytest.mark.asyncio
async def test_migrated_workflow():
    """Test workflow works with enhanced executor"""
    # Your existing workflow
    workflow = load_your_workflow()

    # Create infrastructure
    infra = await Infrastructure.create("development")

    # Create enhanced executor
    executor = EnhancedWorkflowExecutor(
        workflow=workflow,
        infra=infra,
        workflow_id="test_workflow"
    )

    # Should work identically to base executor
    await executor.initialize()
    result = await executor.execute()

    assert result['status'] == 'completed'
```

### 2. Integration Tests

```python
@pytest.mark.asyncio
async def test_events_emitted():
    """Test that events are emitted"""
    infra = await Infrastructure.create("development")

    events_received = []
    async def capture_events(event):
        events_received.append(event)

    await infra.events.subscribe("workflow_events", capture_events)

    executor = EnhancedWorkflowExecutor(
        workflow=your_workflow,
        infra=infra,
        workflow_id="test"
    )

    await executor.initialize()
    await executor.execute()

    # Wait for events
    await asyncio.sleep(0.1)

    # Verify events
    assert len(events_received) > 0
    assert any(e['type'] == 'execution_started' for e in events_received)
    assert any(e['type'] == 'execution_completed' for e in events_received)
```

### 3. Manual Testing

```python
# Run in development mode first
async def test_manual():
    infra = await Infrastructure.create("development")

    # Subscribe to events for visibility
    async def print_events(event):
        print(f"Event: {event}")

    await infra.events.subscribe("workflow_events", print_events)

    # Your workflow
    executor = EnhancedWorkflowExecutor(
        workflow=your_workflow,
        infra=infra,
        workflow_id="manual_test"
    )

    await executor.initialize()
    result = await executor.execute()

    print(f"Result: {result}")

# Run test
asyncio.run(test_manual())
```

---

## Rollback Plan

If issues occur, you can easily rollback:

### Option 1: Keep Both Executors

```python
# Use enhanced executor for new workflows
from src.workflow.enhanced_executor import EnhancedWorkflowExecutor

# Keep base executor for existing critical workflows
from src.workflow.executor import WorkflowExecutor

# Gradual migration
if is_critical_workflow:
    executor = WorkflowExecutor(workflow)
else:
    executor = EnhancedWorkflowExecutor(workflow, infra, ...)
```

### Option 2: Feature Flag

```python
USE_ENHANCED_EXECUTOR = os.getenv("USE_ENHANCED_EXECUTOR", "false") == "true"

if USE_ENHANCED_EXECUTOR:
    executor = EnhancedWorkflowExecutor(workflow, infra, workflow_id)
else:
    executor = WorkflowExecutor(workflow)
```

### Option 3: Gradual Rollout

1. **Week 1**: Test environment only
2. **Week 2**: Staging environment + non-critical workflows
3. **Week 3**: Production, 10% of workflows
4. **Week 4**: Production, 50% of workflows
5. **Week 5**: Production, 100% of workflows

---

## Migration Checklist

### Pre-Migration

- [ ] Review Week 3 documentation
- [ ] Understand infrastructure components
- [ ] Run example workflows
- [ ] Set up development environment

### Migration

- [ ] Create infrastructure instance
- [ ] Update executor creation code
- [ ] Add workflow/bot/strategy IDs
- [ ] Add event subscriptions (optional)
- [ ] Add emergency halt handling

### Testing

- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Manual testing in development
- [ ] Performance testing
- [ ] Load testing

### Deployment

- [ ] Deploy to test environment
- [ ] Monitor for 24 hours
- [ ] Deploy to staging
- [ ] Monitor for 48 hours
- [ ] Gradual production rollout
- [ ] Monitor metrics and events

### Post-Migration

- [ ] Verify event emission
- [ ] Verify state persistence
- [ ] Check emergency controls
- [ ] Monitor circuit breakers
- [ ] Review logs for issues

---

## Common Migration Patterns

### Pattern 1: Singleton Infrastructure

```python
# Create infrastructure once, reuse everywhere
class WorkflowManager:
    def __init__(self):
        self.infra = None

    async def initialize(self):
        self.infra = await Infrastructure.create("production")

    async def execute_workflow(self, workflow_def, workflow_id):
        executor = EnhancedWorkflowExecutor(
            workflow=workflow_def,
            infra=self.infra,  # Reuse infrastructure
            workflow_id=workflow_id
        )
        await executor.initialize()
        return await executor.execute()

# Usage
manager = WorkflowManager()
await manager.initialize()

result1 = await manager.execute_workflow(workflow1, "wf1")
result2 = await manager.execute_workflow(workflow2, "wf2")
```

### Pattern 2: Factory Function

```python
async def create_executor(workflow_def, workflow_id, infra=None):
    """Factory function for creating executors"""
    if infra is None:
        infra = await Infrastructure.create("development")

    return EnhancedWorkflowExecutor(
        workflow=workflow_def,
        infra=infra,
        workflow_id=workflow_id
    )

# Usage
executor = await create_executor(workflow, "wf_001")
result = await executor.execute()
```

### Pattern 3: Context Manager

```python
class ExecutorContext:
    """Context manager for executor lifecycle"""

    def __init__(self, workflow, workflow_id):
        self.workflow = workflow
        self.workflow_id = workflow_id
        self.infra = None
        self.executor = None

    async def __aenter__(self):
        self.infra = await Infrastructure.create("production")
        self.executor = EnhancedWorkflowExecutor(
            workflow=self.workflow,
            infra=self.infra,
            workflow_id=self.workflow_id
        )
        await self.executor.initialize()
        return self.executor

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass

# Usage
async with ExecutorContext(workflow, "wf_001") as executor:
    result = await executor.execute()
```

---

## FAQ

**Q: Do I need to change my workflow definitions?**
A: No, workflow definitions are unchanged.

**Q: Can I use both executors simultaneously?**
A: Yes, they can coexist during migration.

**Q: What if I don't want event emission?**
A: Events are emitted regardless, but you don't have to subscribe to them.

**Q: Is there a performance impact?**
A: Minimal (<2ms overhead). See performance benchmarks in Week 3 Day 4 summary.

**Q: How do I test the migration?**
A: Start with development environment, run your existing test suite.

**Q: What about production deployment?**
A: Use gradual rollout (10% → 50% → 100%) with monitoring.

**Q: Can I rollback if issues occur?**
A: Yes, easily. Keep both executors available during migration.

---

## Support

Need help with migration?

1. Check [Infrastructure Integration Guide](./INFRASTRUCTURE_INTEGRATION.md)
2. Review [Example Workflows](../examples/workflow/)
3. See [Week 3 Summaries](../) for detailed documentation
4. Run [Integration Tests](../tests/integration/) as reference

Happy migrating! 🚀
