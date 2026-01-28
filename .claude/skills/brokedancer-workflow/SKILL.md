---
name: brokedancer-workflow
description: |
  Node-based workflow system for BrokeDancer trading automation. Use when:
  (1) Creating or modifying workflow DAGs in src/workflow/
  (2) Adding new workflow node types
  (3) Working with the WorkflowExecutor or EnhancedExecutor
  (4) Debugging workflow execution or node dependencies
  (5) Integrating workflows with WebSocket real-time updates
  Workflows define trading logic as directed acyclic graphs executed by the runtime.
---

# BrokeDancer Workflow System

## Overview

Workflows define trading automation as **directed acyclic graphs (DAGs)** where nodes represent operations (fetch data, analyze, execute trades) and edges represent data flow between nodes.

## Core Components

**WorkflowExecutor** (`src/workflow/executor.py`):
```python
from src.workflow.executor import WorkflowExecutor

executor = WorkflowExecutor(workflow_dag)
await executor.initialize()  # Create providers
await executor.execute()     # Run workflow
```

**EnhancedExecutor** (`src/workflow/enhanced_executor.py`):
- Extends WorkflowExecutor with WebSocket event emission
- Sends real-time updates to frontend during execution

## Workflow Structure

```python
workflow = {
    "nodes": [
        {
            "id": "fetch_orderbook",
            "type": "provider",
            "provider": "binance",
            "action": "get_orderbook",
            "params": {"pair": "BTCUSDT"}
        },
        {
            "id": "analyze",
            "type": "analysis",
            "action": "detect_arbitrage",
            "inputs": ["fetch_orderbook"]
        },
        {
            "id": "execute",
            "type": "action",
            "action": "place_order",
            "inputs": ["analyze"],
            "condition": "opportunity.profit > 0.01"
        }
    ],
    "edges": [
        {"from": "fetch_orderbook", "to": "analyze"},
        {"from": "analyze", "to": "execute"}
    ]
}
```

## Node Types

### Provider Nodes
Fetch data from exchange providers.
```python
{
    "id": "node_1",
    "type": "provider",
    "provider": "binance",        # Provider name
    "action": "get_orderbook",    # Provider method
    "params": {"pair": "BTCUSDT", "depth": 100}
}
```

Actions: `get_orderbook`, `get_balance`, `get_markets`, `place_order`, `cancel_order`

### Analysis Nodes
Process data and detect opportunities.
```python
{
    "id": "node_2",
    "type": "analysis",
    "action": "detect_arbitrage",
    "inputs": ["node_1"],
    "params": {"min_spread": 0.01}
}
```

Actions: `detect_arbitrage`, `calculate_spread`, `check_threshold`

### Action Nodes
Execute trades or other side effects.
```python
{
    "id": "node_3",
    "type": "action",
    "action": "place_order",
    "inputs": ["node_2"],
    "condition": "input.profit > 0.01"  # Optional condition
}
```

### Condition Nodes
Branch workflow based on conditions.
```python
{
    "id": "node_4",
    "type": "condition",
    "condition": "input.spread > 0.02",
    "true_branch": "execute_trade",
    "false_branch": "log_and_skip"
}
```

## Execution Flow

1. **Topological Sort**: Nodes ordered by dependencies
2. **Sequential Execution**: Each node runs after its inputs complete
3. **Data Passing**: Node outputs available to downstream nodes
4. **Event Emission**: WebSocket events sent for UI updates

```
[Provider Nodes] → [Analysis Nodes] → [Condition] → [Action Nodes]
       ↓                  ↓               ↓              ↓
   Fetch Data      Process Data     Branch Logic    Execute Trade
```

## WebSocket Events

EnhancedExecutor emits these events:
- `workflow_started`: Workflow execution begins
- `node_started`: Node execution begins
- `node_completed`: Node execution finished
- `node_error`: Node execution failed
- `workflow_completed`: Workflow finished

```python
# Event payload
{
    "type": "node_completed",
    "node_id": "fetch_orderbook",
    "status": "success",
    "output": {...},
    "execution_time_ms": 150
}
```

## Adding a New Node Type

1. Define node handler in `src/workflow/nodes.py`:
```python
async def handle_my_node(node: Dict, inputs: Dict, context: Dict) -> Any:
    # Process inputs
    # Return output for downstream nodes
    return result
```

2. Register in node registry:
```python
NODE_HANDLERS = {
    "provider": handle_provider_node,
    "analysis": handle_analysis_node,
    "my_type": handle_my_node,  # Add here
}
```

## GPU Workflow Nodes

**Location**: `src/workflow/gpu_nodes.py`

Specialized nodes for GPU marketplace optimization:
- `vast_fetch_offers`: Get GPU rental offers
- `vast_analyze_pricing`: Analyze GPU pricing
- `vast_allocate`: Rent GPU capacity

## Testing

```bash
# Run workflow tests
pytest tests/core/test_workflow_nodes.py -v
pytest tests/integration/test_workflow_resilience.py -v
```

## Directory Structure

```
src/workflow/
├── executor.py          # Base workflow executor
├── enhanced_executor.py # WebSocket-enabled executor
├── nodes.py             # Multi-domain node handlers
└── gpu_nodes.py         # GPU-specific nodes
```
