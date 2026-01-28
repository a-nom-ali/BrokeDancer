---
name: brokedancer-strategy
description: |
  Trading strategy implementations for BrokeDancer. Use when:
  (1) Creating a new trading strategy (arbitrage, market making, momentum)
  (2) Modifying existing strategy logic
  (3) Understanding the BaseStrategy interface and execution modes
  (4) Debugging strategy execution or opportunity detection
  (5) Working with multi-strategy orchestration
  Strategies are provider-agnostic and implement trading logic using the BaseProvider interface.
---

# BrokeDancer Strategy Layer

## Quick Reference

**BaseStrategy Interface** (`src/strategies/base.py`):
```python
class BaseStrategy(ABC):
    def __init__(provider: BaseProvider, config: Dict, name: str = None)
    async def start() -> None               # Start strategy
    async def stop() -> None                # Stop strategy
    async def run() -> None                 # Main loop (abstract)
    async def find_opportunity() -> Opportunity  # Polling mode
    def on_orderbook_update(pair, orderbook)    # Event mode
    async def execute(opportunity) -> TradeResult
    def should_execute(opportunity) -> (bool, str)
    def get_stats() -> Dict
```

**Data Models**:
- `StrategyStatus`: IDLE, SCANNING, EXECUTING, WAITING, ERROR, STOPPED
- `Opportunity`: strategy_name, timestamp, confidence, expected_profit, metadata
- `TradeResult`: opportunity, success, actual_profit, orders[], error, execution_time_ms

## Execution Modes

**PollingStrategy**: Scans at intervals
```python
class MyStrategy(PollingStrategy):
    async def find_opportunity(self) -> Optional[Opportunity]:
        # Scan markets, return opportunity or None

    async def execute(self, opp: Opportunity) -> TradeResult:
        # Execute the trade
```

**EventDrivenStrategy**: Reacts to market events
```python
class MyStrategy(EventDrivenStrategy):
    def on_orderbook_update(self, pair: str, orderbook: Orderbook):
        # React to orderbook changes

    async def run(self):
        # Subscribe to WebSocket events
```

## Creating a New Strategy

1. Create `src/strategies/<name>.py`
2. Subclass `PollingStrategy` or `EventDrivenStrategy`
3. Implement `find_opportunity()` and `execute()` (or event handlers)
4. Add to factory (`src/strategies/factory.py`)
5. Add config example

**Template**:
```python
from .base import PollingStrategy, Opportunity, TradeResult

class MyStrategy(PollingStrategy):
    def __init__(self, provider, config, name=None):
        super().__init__(provider, config, name or "MyStrategy")
        self.threshold = config.get("threshold", 0.01)

    async def find_opportunity(self) -> Optional[Opportunity]:
        orderbook = self.provider.get_orderbook(self.config["pair"])
        # Analyze and return Opportunity if found
        return None

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        if self.dry_run:
            return TradeResult(opportunity=opportunity, success=True)
        # Place orders via self.provider
        return TradeResult(...)
```

## Implemented Strategies

| Strategy | Type | Description |
|----------|------|-------------|
| binary_arbitrage | Arbitrage | Polymarket YES/NO mispricing |
| cross_exchange_arbitrage | Arbitrage | Buy low/sell high across exchanges |
| cross_platform_arbitrage | Arbitrage | Kalshi vs Polymarket |
| funding_rate_arbitrage | Arbitrage | Derivatives funding rate |
| basis_trading | Spread | Spot-futures basis |
| triangular_arbitrage | Arbitrage | 3-leg currency cycle |
| momentum_trading | Trend | Price momentum |
| simple_market_making | Market Making | Bid/ask spread capture |
| statistical_arbitrage | Statistical | Mean reversion |
| liquidation_sniping | Event | Liquidation cascade |
| high_probability_bond | Value | High-confidence Polymarket |

See `references/strategies.md` for detailed strategy documentation.

## Multi-Strategy Orchestration

```python
from src.strategies.multi_strategy import MultiStrategyBot

bot = MultiStrategyBot([
    strategy1,
    strategy2,
    strategy3
])
await bot.start()  # Runs all in parallel
```

## Configuration Options

Common config keys (all strategies):
- `scan_interval`: Polling interval in seconds (default: 1.0)
- `min_profit`: Minimum profit to execute (default: 0.01)
- `dry_run`: Test mode without real trades (default: False)
- `min_confidence`: Minimum confidence threshold (default: 0.0)

## Testing

```bash
pytest tests/ -k "strategy" -v
```
