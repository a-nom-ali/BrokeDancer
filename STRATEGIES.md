# Trading Strategies Guide

This guide covers the trading strategies available in the bot and how to implement custom strategies.

## 📖 Table of Contents

- [Overview](#overview)
- [Available Strategies](#available-strategies)
- [Strategy Selection](#strategy-selection)
- [Creating Custom Strategies](#creating-custom-strategies)
- [Strategy Combinations](#strategy-combinations)
- [Best Practices](#best-practices)

---

## Overview

The bot uses a **strategy layer** that separates trading logic from provider implementations. This means:

- ✅ Same strategy can work across different providers
- ✅ Multiple strategies can run in parallel
- ✅ Strategies can be polling-based or event-driven
- ✅ Easy to test and backtest strategies

### Strategy Execution Modes

**Polling Mode** - Scans for opportunities at regular intervals
```python
class PollingStrategy(BaseStrategy):
    async def run(self):
        while running:
            opportunity = await self.find_opportunity()
            if opportunity:
                await self.execute(opportunity)
            await asyncio.sleep(scan_interval)
```

**Event-Driven Mode** - Reacts to real-time market events
```python
class EventDrivenStrategy(BaseStrategy):
    def on_orderbook_update(self, pair, orderbook):
        opportunity = self.analyze_orderbook(orderbook)
        if opportunity:
            asyncio.create_task(self.execute(opportunity))
```

---

## Available Strategies

### 1. Binary Arbitrage ✅ (Implemented)

**Type**: Polling
**Providers**: Polymarket
**Risk Level**: Low
**Capital Requirement**: $50 - $5,000+

#### How It Works

Buy both YES and NO tokens when their combined cost is less than $1.00.

```
Example:
- YES token: $0.52
- NO token: $0.46
- Total cost: $0.98
- Payout: $1.00 (guaranteed)
- Profit: $0.02 per share (2% return)
```

Since one outcome must occur, you always receive $1.00 per share at settlement.

#### Configuration

```bash
# .env
STRATEGY=binary_arbitrage
PROVIDER=polymarket

# Strategy parameters
TARGET_PAIR_COST=0.99        # Buy when total < $0.99
ORDER_SIZE=50                # 50 shares per side
ORDER_TYPE=FOK               # Fill-or-Kill
SCAN_INTERVAL=1.0            # Scan every second

# Risk management
MIN_PROFIT=0.01              # Minimum $0.01 profit
MIN_CONFIDENCE=0.95          # Minimum 95% confidence
```

#### When to Use

- **Best for**: Beginners, low-risk traders
- **Capital**: Works with any amount ($50+)
- **Markets**: BTC 15-minute prediction markets (high liquidity)
- **Expected ROI**: 0.5% - 3% per trade
- **Frequency**: 1-5 opportunities per day

#### Optimization Tips

1. **Scan Interval**: 1-2 seconds for BTC markets
2. **Target Cost**: 0.99 for beginners, 0.995 for aggressive
3. **Order Type**: FOK prevents partial fills
4. **Market Selection**: Focus on high-volume markets (BTC > $1M liquidity)

---

### 2. Copy Trading 🔜 (Coming Soon)

**Type**: Event-Driven
**Providers**: Polymarket, Luno
**Risk Level**: Medium
**Capital Requirement**: $200+

#### How It Will Work

Mirror the positions of successful traders in real-time.

```python
class CopyTradingStrategy(EventDrivenStrategy):
    def on_trade(self, pair, trade):
        # If trade is from followed wallet
        if trade.trader in self.followed_wallets:
            # Place same order with position sizing
            self.execute_copy_trade(trade)
```

#### Configuration (Planned)

```bash
STRATEGY=copy_trading
PROVIDER=polymarket

# Copy trading parameters
FOLLOWED_WALLETS=0xabc...,0xdef...  # Wallets to copy
COPY_PERCENTAGE=50                   # Copy 50% of their position
MAX_POSITION_SIZE=1000               # Max $1000 per position
```

---

### 3. Cross-Exchange Arbitrage 🔜 (Coming Soon)

**Type**: Polling
**Providers**: Luno + Binance/Kraken
**Risk Level**: Medium-High
**Capital Requirement**: $1,000+

#### How It Will Work

Buy cryptocurrency on one exchange where it's cheaper, sell on another where it's more expensive.

```
Example:
- BTC on Luno: 1,250,000 ZAR
- BTC on Binance: 1,252,000 ZAR
- Spread: 2,000 ZAR ($110)
- Profit after fees: ~$50 per BTC
```

#### Challenges

- Transfer time (risk of price movement)
- Withdrawal fees
- Liquidity on both exchanges
- Need balances on both exchanges

---

### 4. Triangular Arbitrage 🔜 (Coming Soon)

**Type**: Event-Driven
**Providers**: Luno
**Risk Level**: Medium
**Capital Requirement**: $500+

#### How It Will Work

Exploit pricing inefficiencies across three currency pairs.

```
Example cycle:
1. ZAR → BTC (buy BTC with ZAR)
2. BTC → ETH (buy ETH with BTC)
3. ETH → ZAR (sell ETH for ZAR)

If final ZAR > starting ZAR → Profit
```

#### Configuration (Planned)

```bash
STRATEGY=triangular
PROVIDER=luno

TRIANGLE_PAIRS=XBTZAR,ETHXBT,ETHZAR
MIN_PROFIT_PCT=0.2               # 0.2% minimum profit
CYCLE_SIZE=5000                  # 5000 ZAR per cycle
```

---

### 5. Market Making 🔜 (Coming Soon)

**Type**: Event-Driven
**Providers**: Polymarket, Luno
**Risk Level**: High
**Capital Requirement**: $2,000+

#### How It Will Work

Post both bid and ask orders to capture the spread.

```
Example:
- Buy orders at: $0.48, $0.47, $0.46
- Sell orders at: $0.52, $0.53, $0.54
- Spread: $0.04 per share
- Risk: Inventory risk if price moves
```

#### Challenges

- Inventory management
- Adverse selection (getting picked off)
- Requires significant capital
- High-frequency monitoring

---

### 6. Grid Trading 🔜 (Coming Soon)

**Type**: Polling
**Providers**: Luno
**Risk Level**: Medium
**Capital Requirement**: $1,000+

#### How It Will Work

Place buy/sell orders at predefined price levels.

```
Grid Example (BTC/ZAR):
Sell: 1,260,000 | 1,255,000 | 1,250,000
Buy:  1,245,000 | 1,240,000 | 1,235,000

Profit from volatility as price moves through grid.
```

---

## Strategy Selection

### Via Environment Variables

```bash
# .env
STRATEGY=binary_arbitrage
PROVIDER=polymarket
```

### Via Code

```python
from src.strategies import create_strategy
from src.providers import create_provider

provider = create_provider("polymarket", config)
strategy = create_strategy("binary_arbitrage", provider, {
    "target_pair_cost": 0.99,
    "order_size": 50,
    "yes_token_id": "...",
    "no_token_id": "..."
})

await strategy.start()
```

### Multiple Strategies

```python
from src.strategies import MultiStrategyBot

strategies = [
    create_strategy("binary_arbitrage", poly_provider, config1),
    create_strategy("copy_trading", poly_provider, config2),
    create_strategy("triangular", luno_provider, config3),
]

bot = MultiStrategyBot(strategies)
await bot.run()
```

---

## Creating Custom Strategies

### Step 1: Choose Base Class

**Polling Strategy** - For periodic scanning
```python
from src.strategies.base import PollingStrategy, Opportunity, TradeResult

class MyCustomStrategy(PollingStrategy):
    async def find_opportunity(self) -> Optional[Opportunity]:
        # Scan market for opportunities
        pass

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        # Execute the trade
        pass
```

**Event-Driven Strategy** - For real-time reactions
```python
from src.strategies.base import EventDrivenStrategy

class MyEventStrategy(EventDrivenStrategy):
    def on_orderbook_update(self, pair: str, orderbook: Orderbook):
        # React to orderbook changes
        pass

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        # Execute the trade
        pass
```

### Step 2: Implement Required Methods

#### `find_opportunity()` (for polling strategies)

```python
async def find_opportunity(self) -> Optional[Opportunity]:
    # 1. Fetch market data
    orderbook = self.provider.get_orderbook(pair)

    # 2. Analyze for opportunity
    if self.is_profitable(orderbook):
        # 3. Return opportunity
        return Opportunity(
            strategy_name=self.name,
            timestamp=int(time.time() * 1000),
            confidence=0.95,
            expected_profit=10.50,
            metadata={
                "pair": pair,
                "entry_price": 0.48,
                "exit_price": 0.52,
            }
        )

    return None
```

#### `execute()` (required for all strategies)

```python
async def execute(self, opportunity: Opportunity) -> TradeResult:
    try:
        # 1. Extract metadata
        pair = opportunity.metadata["pair"]
        price = opportunity.metadata["entry_price"]

        # 2. Place order(s)
        order = self.provider.place_order(
            pair=pair,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            size=100,
            price=price
        )

        # 3. Return result
        return TradeResult(
            opportunity=opportunity,
            success=True,
            actual_profit=opportunity.expected_profit,
            orders=[order]
        )

    except Exception as e:
        return TradeResult(
            opportunity=opportunity,
            success=False,
            error=str(e)
        )
```

### Step 3: Add to Factory

Edit `src/strategies/factory.py`:

```python
from .my_custom_strategy import MyCustomStrategy

def create_strategy(strategy_name: str, provider, config):
    # ... existing strategies ...

    elif strategy_name_lower == "mycustom":
        return MyCustomStrategy(provider, config)

    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")
```

### Step 4: Test Your Strategy

```python
# test_my_strategy.py
import pytest
from src.providers import create_provider
from src.strategies.my_custom_strategy import MyCustomStrategy

@pytest.mark.asyncio
async def test_find_opportunity():
    provider = create_provider("polymarket", test_config)
    strategy = MyCustomStrategy(provider, {"dry_run": True})

    opportunity = await strategy.find_opportunity()

    assert opportunity is not None
    assert opportunity.expected_profit > 0
```

---

## Strategy Combinations

### Parallel Execution

Run multiple strategies on different markets simultaneously:

```python
strategies = [
    BinaryArbitrageStrategy(poly_provider, btc_config),
    BinaryArbitrageStrategy(poly_provider, eth_config),
    TriangularArbitrageStrategy(luno_provider, tri_config),
]

bot = MultiStrategyBot(strategies)
await bot.run()
```

### Sequential Execution

Run strategies in sequence (one after another):

```python
# Strategy 1: Build position
await accumulation_strategy.start()
await accumulation_strategy.wait_for_completion()

# Strategy 2: Exit position
await exit_strategy.start()
```

### Hybrid Approach

Combine polling and event-driven:

```python
class HybridStrategy(BaseStrategy):
    async def run(self):
        # Start event listener
        await self.start_websocket_listener()

        # Run polling loop
        while self.running:
            opportunity = await self.find_opportunity()
            if opportunity:
                await self.execute(opportunity)
            await asyncio.sleep(60)
```

---

## Best Practices

### 1. Risk Management

Always implement safeguards:

```python
def should_execute(self, opportunity: Opportunity) -> tuple[bool, str]:
    # Check minimum profit
    if opportunity.expected_profit < self.min_profit:
        return False, "Profit too low"

    # Check daily loss limit
    if self.total_profit < -self.max_daily_loss:
        return False, "Daily loss limit reached"

    # Check position size
    if self.get_position_value() > self.max_position_size:
        return False, "Position size exceeded"

    return True, "OK"
```

### 2. Error Handling

Handle failures gracefully:

```python
async def execute(self, opportunity):
    orders = []
    try:
        order1 = self.provider.place_order(...)
        orders.append(order1)

        order2 = self.provider.place_order(...)
        orders.append(order2)

        return TradeResult(success=True, orders=orders)

    except Exception as e:
        # Cancel any placed orders
        for order in orders:
            try:
                self.provider.cancel_order(order.order_id)
            except:
                pass

        return TradeResult(success=False, error=str(e))
```

### 3. Logging

Log important events:

```python
self.logger.info(f"🎯 Opportunity found: {opportunity}")
self.logger.info(f"📤 Placing order: BUY {size} @ ${price}")
self.logger.info(f"✅ Trade executed: ${profit:.2f} profit")
self.logger.warning(f"⚠️ Low liquidity: {available} < {required}")
self.logger.error(f"❌ Execution failed: {error}")
```

### 4. Dry Run Testing

Always test with dry_run first:

```python
config = {
    "dry_run": True,  # Simulate trades
    "target_pair_cost": 0.99,
    "order_size": 50,
}

strategy = create_strategy("binary_arbitrage", provider, config)
await strategy.start()

# Review stats
stats = strategy.get_stats()
print(f"Simulated profit: ${stats['total_profit']:.2f}")
```

### 5. Monitoring

Track strategy performance:

```python
# Get real-time stats
stats = strategy.get_stats()
print(f"Opportunities: {stats['opportunities_found']}")
print(f"Executed: {stats['trades_executed']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Total profit: ${stats['total_profit']:.2f}")
```

### 6. Capital Allocation

Use trading profiles for automatic sizing:

```python
from src.profiles import apply_profile

# Auto-detect profile from balance
settings = load_settings()
balance = provider.get_balance("USDC")
settings = apply_profile_to_settings(settings, balance["USDC"].total)

# Now settings.order_size is optimized for your capital
```

---

## Strategy Comparison

| Strategy | Risk | Capital | ROI/Trade | Frequency | Complexity |
|----------|------|---------|-----------|-----------|------------|
| Binary Arbitrage | Low | $50+ | 0.5-3% | 1-5/day | Low |
| Copy Trading | Medium | $200+ | 5-20% | Varies | Medium |
| Cross-Exchange | Medium-High | $1,000+ | 0.2-1% | 1-10/day | High |
| Triangular | Medium | $500+ | 0.1-0.5% | 5-20/day | High |
| Market Making | High | $2,000+ | 0.05-0.2% | 100s/day | Very High |
| Grid Trading | Medium | $1,000+ | 1-5% | 10-50/day | Medium |

---

## Next Steps

1. **Review** the [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
2. **Choose** a strategy that fits your risk tolerance and capital
3. **Configure** using the appropriate `.env.example.*` template
4. **Test** with `dry_run=True` first
5. **Monitor** performance and adjust parameters
6. **Scale** gradually as you gain confidence

---

## Resources

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [PROFILES.md](./PROFILES.md) - Capital-based trading profiles
- [PROFIT_ANALYSIS.md](./PROFIT_ANALYSIS.md) - Budget and ROI analysis
- [README.md](./README.md) - General setup and usage

---

**⚠️ Disclaimer**: All strategies involve risk. Past performance doesn't guarantee future results. Start small, use dry_run mode, and never trade with money you can't afford to lose.
