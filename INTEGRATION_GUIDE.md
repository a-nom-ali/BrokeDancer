# Integration Guide: Abstraction Layer ↔ Existing System

This guide shows how to integrate the new generic abstraction layer with the existing trading bot system, ensuring seamless compatibility and gradual migration.

---

## Overview

The integration provides **bidirectional compatibility**:

1. **Legacy → New**: Existing `BaseProvider` and `BaseStrategy` work with new generic system
2. **New → Legacy**: New `Venue` and `Strategy` can be used by existing code
3. **Incremental Migration**: Add domains one at a time without breaking existing functionality

---

## Quick Start: Using Existing Providers with New System

### Wrap a Provider as a Venue

```python
from src.providers.binance import BinanceProvider
from src.core.bridge import wrap_provider_as_venue

# Existing provider
provider = BinanceProvider(api_key="...", api_secret="...")

# Wrap as generic Venue
venue = wrap_provider_as_venue(provider)

# Now works with new system
await venue.connect()
assets = await venue.list_assets()
position = await venue.get_position(assets[0])

# Execute actions using new interface
from src.core.venue import ActionRequest, ActionType

action = ActionRequest(
    action_type=ActionType.PLACE_ORDER,
    asset=assets[0],
    quantity=0.1,
    price=50000.0,
    side="buy",
    order_type="limit"
)

result = await venue.execute_action(action)
```

### Wrap a Strategy to Use New Interface

```python
from src.strategies.binary_arbitrage import BinaryArbitrageStrategy
from src.core.bridge import wrap_legacy_strategy

# Existing strategy
legacy_strategy = BinaryArbitrageStrategy(
    provider=polymarket_provider,
    config={"min_profit": 5.0, "scan_interval": 10.0}
)

# Wrap as generic Strategy
generic_strategy = wrap_legacy_strategy(legacy_strategy)

# Now works with new system
await generic_strategy.initialize()
opportunities = await generic_strategy.find_opportunities()

for opp in opportunities:
    result = await generic_strategy.execute_opportunity(opp)
    print(f"Profit: ${result.actual_profit}")
```

---

## Integration Patterns

### Pattern 1: Hybrid Strategy (Old + New)

Mix legacy and new systems in the same strategy:

```python
from src.core.strategy import Strategy, Opportunity, OpportunityType
from src.core.bridge import wrap_provider_as_venue
from src.providers.binance import BinanceProvider
from src.providers.coinbase import CoinbaseProvider

class HybridArbitrageStrategy(Strategy):
    """Uses new abstraction but wraps legacy providers"""

    def __init__(self):
        # Wrap legacy providers
        binance_venue = wrap_provider_as_venue(
            BinanceProvider(api_key="...", api_secret="...")
        )
        coinbase_venue = wrap_provider_as_venue(
            CoinbaseProvider(api_key="...", api_secret="...")
        )

        super().__init__(
            strategy_id="hybrid_arb",
            strategy_name="Hybrid Arbitrage",
            venues=[binance_venue, coinbase_venue],
            config=StrategyConfig(min_expected_profit=10.0)
        )

    async def find_opportunities(self):
        # Use new abstraction layer
        binance_btc = await self.venues[0].get_asset("BTC-USDT")
        coinbase_btc = await self.venues[1].get_asset("BTC-USD")

        binance_price = await binance_btc.fetch_current_valuation()
        coinbase_price = await coinbase_btc.fetch_current_valuation()

        spread = coinbase_price.current_value - binance_price.current_value

        if spread > self.config.min_expected_profit:
            return [Opportunity(
                opportunity_id=f"arb_{time.time()}",
                opportunity_type=OpportunityType.ARBITRAGE,
                strategy_name=self.strategy_name,
                confidence=0.9,
                expected_profit=spread,
                expected_cost=binance_price.current_value,
                expected_roi=(spread / binance_price.current_value) * 100,
                primary_venue=self.venues[0],
                secondary_venue=self.venues[1]
            )]

        return []
```

### Pattern 2: Gradual Provider Migration

Migrate one provider at a time:

```python
from src.core.adapters.trading import TradingVenueAdapter
from src.providers.binance import BinanceProvider

# Old way (still works)
old_provider = BinanceProvider(api_key="...", api_secret="...")
old_provider.connect()
orderbook = old_provider.get_orderbook("BTCUSDT")

# New way (same provider, new interface)
new_venue = TradingVenueAdapter(provider=old_provider)
await new_venue.connect()
asset = await new_venue.get_asset("BTCUSDT")
valuation = await asset.fetch_current_valuation()

# Both work simultaneously! Choose based on context
```

### Pattern 3: Multi-Domain Bot Manager

Run bots across different domains from one manager:

```python
from src.web.multi_bot_manager import MultiBotManager
from src.core.bridge import wrap_legacy_strategy
from src.strategies.binary_arbitrage import BinaryArbitrageStrategy
from src.core.adapters.compute import ComputeMarketplaceAdapter, GPUCapacityStrategy

# Existing trading strategy
trading_strategy = wrap_legacy_strategy(
    BinaryArbitrageStrategy(provider=polymarket_provider, config={})
)

# New GPU strategy
gpu_marketplace = ComputeMarketplaceAdapter(
    marketplace_name="vast.ai",
    api_key="...",
    owned_gpus=[...]
)
gpu_strategy = GPUCapacityStrategy(
    gpu_asset=rtx4090,
    marketplace=gpu_marketplace,
    power_cost_per_hour=0.12
)

# Run both in the same manager
bot_manager = MultiBotManager()
bot_manager.add_bot("trading", trading_strategy)
bot_manager.add_bot("gpu_optimization", gpu_strategy)

# Both bots run in parallel, same UI, same risk management
await bot_manager.start_all()
```

---

## Workflow Integration

### Extending Existing Workflow System

The existing workflow executor (`src/workflow/executor.py`) now supports multi-domain blocks:

#### Example: Cross-Domain Workflow

```json
{
  "name": "Multi-Domain Arbitrage",
  "blocks": [
    {
      "id": "binance_price",
      "category": "source",
      "type": "venue_price",
      "properties": {
        "venue_type": "trading",
        "venue_id": "binance",
        "asset_symbol": "BTC-USDT"
      }
    },
    {
      "id": "coinbase_price",
      "category": "source",
      "type": "venue_price",
      "properties": {
        "venue_type": "trading",
        "venue_id": "coinbase",
        "asset_symbol": "BTC-USD"
      }
    },
    {
      "id": "spread_calc",
      "category": "transform",
      "type": "calculate_spread"
    },
    {
      "id": "threshold",
      "category": "condition",
      "type": "threshold_check",
      "properties": {
        "threshold": 50.0,
        "operator": ">="
      }
    },
    {
      "id": "execute",
      "category": "executor",
      "type": "execute_action",
      "properties": {
        "action_type": "PLACE_ORDER",
        "venue_id": "binance"
      }
    }
  ],
  "connections": [
    {"from": "binance_price", "to": "spread_calc"},
    {"from": "coinbase_price", "to": "spread_calc"},
    {"from": "spread_calc", "to": "threshold"},
    {"from": "threshold", "to": "execute"}
  ]
}
```

### Using New Workflow Nodes

```python
from src.workflow.nodes import (
    VenuePriceNode,
    CalculateSpreadNode,
    ThresholdCheckNode,
    ExecuteActionNode
)
from src.core.graph_runtime import StrategyGraph, GraphRuntime

# Create graph
graph = StrategyGraph(
    graph_id="arb_workflow",
    name="Arbitrage Workflow"
)

# Add nodes (works with any venue type)
price_a = VenuePriceNode(
    node_id="price_a",
    venue=binance_venue,
    asset_symbol="BTC-USDT"
)

price_b = VenuePriceNode(
    node_id="price_b",
    venue=coinbase_venue,
    asset_symbol="BTC-USD"
)

spread = CalculateSpreadNode(node_id="spread")
threshold = ThresholdCheckNode(node_id="threshold", threshold=50.0)
execute = ExecuteActionNode(
    node_id="execute",
    venue=binance_venue,
    action_type=ActionType.PLACE_ORDER
)

# Add to graph
graph.add_node(price_a)
graph.add_node(price_b)
graph.add_node(spread)
graph.add_node(threshold)
graph.add_node(execute)

# Connect nodes
from src.core.graph_runtime import NodeConnection

graph.add_connection(NodeConnection(
    from_node_id="price_a", from_output_index=0,
    to_node_id="spread", to_input_index=0
))
# ... more connections

# Execute
runtime = GraphRuntime(graph)
result = await runtime.execute()
```

---

## Risk Management Integration

### Use Same Risk Manager Across All Domains

```python
from src.core.risk import DefaultRiskManager, RiskConstraint, ConstraintType
from datetime import timedelta

# Create global risk manager
global_risk = DefaultRiskManager(constraints=[
    RiskConstraint(
        constraint_type=ConstraintType.DAILY_LOSS,
        name="global_daily_loss",
        limit=500.0,  # $500 max loss per day
        enforce=True
    ),
    RiskConstraint(
        constraint_type=ConstraintType.POSITION_SIZE,
        name="max_position",
        limit=10000.0,  # $10k max per position
        enforce=True
    ),
    RiskConstraint(
        constraint_type=ConstraintType.FREQUENCY,
        name="action_frequency",
        limit=100,  # Max 100 actions per hour
        time_window=timedelta(hours=1),
        enforce=True
    )
])

# Apply to all strategies (trading, GPU, ads, ecommerce)
trading_bot.set_risk_manager(global_risk)
gpu_bot.set_risk_manager(global_risk)
ad_bot.set_risk_manager(global_risk)
ecommerce_bot.set_risk_manager(global_risk)

# Now if trading loses $300, all other bots have only $200 budget left
```

---

## Migration Roadmap

### Phase 1: Wrapper Layer (Week 1) ✅ DONE

- [x] Created bridge layer (`src/core/bridge.py`)
- [x] Wrapped existing providers with `TradingVenueAdapter`
- [x] Wrapped existing strategies with `StrategyBridge`
- [x] Added convenience functions (`wrap_legacy_strategy`, `wrap_provider_as_venue`)

**Status**: Existing system fully compatible with new abstractions

### Phase 2: Workflow Extension (Week 2) ✅ DONE

- [x] Added multi-domain workflow nodes (`src/workflow/nodes.py`)
- [x] Implemented universal node types (price, position, spread, profit, etc.)
- [x] Created tests for all node types
- [x] Documented workflow integration patterns

**Status**: Workflow system works across all domains

### Phase 3: First Non-Trading Domain (Week 3-4)

- [ ] Implement GPU marketplace integration
  - [ ] Create Vast.ai API client
  - [ ] Build `ComputeMarketplaceAdapter` with real API
  - [ ] Implement `GPUCapacityStrategy` with backtesting
- [ ] Add GPU-specific workflow blocks
- [ ] Create GPU bot dashboard UI
- [ ] Test cross-domain risk management (trading + GPU)

**Goal**: Prove abstraction layer works for non-trading domain

### Phase 4: Dashboard Unification (Month 2)

- [ ] Extend web UI to show all bot types
- [ ] Unified P&L tracking across domains
- [ ] Cross-domain portfolio view
- [ ] Domain-agnostic bot configuration UI

**Goal**: Single interface for all automation domains

### Phase 5: Signal Marketplace (Month 3)

- [ ] Create opportunity signal publishing system
- [ ] Build subscription/payment infrastructure
- [ ] Allow users to share workflows across domains
- [ ] Implement signal backtesting and ratings

**Goal**: Monetize platform through signal marketplace

---

## Testing Integration

### Run Bridge Tests

```bash
pytest tests/core/test_bridge.py -v
```

### Run Workflow Node Tests

```bash
pytest tests/core/test_workflow_nodes.py -v
```

### Run Integration Tests

```bash
# Test legacy provider wrapped as venue
pytest tests/integration/test_provider_venue_integration.py

# Test legacy strategy wrapped as generic
pytest tests/integration/test_strategy_bridge_integration.py

# Test workflow with multi-domain nodes
pytest tests/integration/test_multi_domain_workflow.py
```

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution**: Ensure `src/core/` is in Python path:

```python
import sys
sys.path.insert(0, '/path/to/project/src')
```

### Issue: Async/sync mismatch when wrapping providers

**Cause**: Old providers use sync methods, new system is async.

**Solution**: Use `asyncio.run()` wrapper or upgrade provider to async:

```python
# Quick fix: Use wrapper
result = asyncio.run(sync_function())

# Better fix: Make provider async
class AsyncBinanceProvider(BinanceProvider):
    async def get_orderbook(self, pair):
        return await asyncio.to_thread(super().get_orderbook, pair)
```

### Issue: Legacy strategy not finding opportunities

**Cause**: Different opportunity format between legacy and new.

**Solution**: Use `OpportunityConverter`:

```python
from src.core.bridge import OpportunityConverter

legacy_opp = await legacy_strategy.find_opportunity()
generic_opp = OpportunityConverter.to_generic(legacy_opp)
```

---

## Best Practices

### 1. Start with Wrappers

Always wrap existing code before writing new implementations:

```python
# Good: Wrap first
venue = wrap_provider_as_venue(existing_provider)

# Avoid: Rewriting immediately
# Don't rewrite BinanceProvider from scratch yet
```

### 2. Test Both Interfaces

When wrapping, test that both old and new interfaces work:

```python
# Test old interface
assert old_provider.get_orderbook("BTCUSDT") is not None

# Test new interface
asset = await new_venue.get_asset("BTCUSDT")
assert await asset.fetch_current_valuation() is not None
```

### 3. Gradual Type Migration

Migrate type hints gradually:

```python
# Phase 1: Accept both types
def execute_strategy(strategy: Union[LegacyBaseStrategy, Strategy]):
    if isinstance(strategy, LegacyBaseStrategy):
        strategy = wrap_legacy_strategy(strategy)
    # ... use generic interface

# Phase 2: Only new types (after full migration)
def execute_strategy(strategy: Strategy):
    # ... use generic interface
```

### 4. Document Domain-Specific Behavior

When adapting, document quirks:

```python
class PolymarketAdapter(TradingVenueAdapter):
    """
    Adapter for Polymarket prediction markets.

    Note: Polymarket uses YES/NO tokens, not traditional pairs.
    Price is always 0-1 (probability). Handle conversion internally.
    """
    async def execute_action(self, request):
        # Convert price from USD to probability
        if request.price:
            request.price = min(request.price / 100, 1.0)
        # ...
```

---

## Summary

The bridge layer ensures **zero disruption** to existing functionality while enabling **gradual migration** to the multi-domain abstraction layer.

**Key Takeaways**:

- ✅ All existing providers work with new `Venue` interface
- ✅ All existing strategies work with new `Strategy` interface
- ✅ Workflow system supports multi-domain blocks
- ✅ Risk management works across all domains
- ✅ Migration can happen incrementally, one domain at a time

**Next Steps**:

1. Test wrapper layer with your existing bots
2. Experiment with new workflow nodes
3. Plan first non-trading domain (GPU, ads, or ecommerce)
4. Gradually adopt new patterns as you add features

The platform is now ready to expand beyond trading into any domain where profit can be automated! 🚀
