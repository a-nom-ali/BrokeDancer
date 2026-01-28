# Strategy Reference

## Table of Contents
- [Binary Arbitrage](#binary-arbitrage)
- [Cross-Exchange Arbitrage](#cross-exchange-arbitrage)
- [Cross-Platform Arbitrage](#cross-platform-arbitrage)
- [Funding Rate Arbitrage](#funding-rate-arbitrage)
- [Basis Trading](#basis-trading)
- [Triangular Arbitrage](#triangular-arbitrage)
- [Momentum Trading](#momentum-trading)
- [Simple Market Making](#simple-market-making)
- [Statistical Arbitrage](#statistical-arbitrage)
- [Liquidation Sniping](#liquidation-sniping)
- [High Probability Bond](#high-probability-bond)

---

## Binary Arbitrage

**File**: `src/strategies/binary_arbitrage.py`
**Provider**: Polymarket
**Type**: Risk-free arbitrage

**Logic**: Buy both YES and NO tokens when combined price < $1.00
- Payout is always $1.00 regardless of outcome
- Profit = $1.00 - (YES price + NO price)

**Config**:
```python
{
    "min_spread": 0.01,        # Minimum arbitrage spread
    "max_position": 1000,      # Max USDC per trade
    "yes_token_id": "...",
    "no_token_id": "..."
}
```

**Example**: YES @ $0.48, NO @ $0.50 → Buy both for $0.98, profit $0.02

---

## Cross-Exchange Arbitrage

**File**: `src/strategies/cross_exchange_arbitrage.py`
**Providers**: Any two exchanges (Binance, Coinbase, etc.)
**Type**: Price discrepancy arbitrage

**Logic**: Buy on exchange A, sell on exchange B when price differs
- Accounts for fees and slippage
- Requires capital on both exchanges

**Config**:
```python
{
    "provider_a": "binance",
    "provider_b": "coinbase",
    "pair": "BTCUSDT",
    "min_spread_pct": 0.1,     # Minimum spread percentage
    "fee_pct": 0.1             # Combined fee estimate
}
```

---

## Cross-Platform Arbitrage

**File**: `src/strategies/cross_platform_arbitrage.py`
**Providers**: Polymarket + Kalshi
**Type**: Prediction market arbitrage

**Logic**: Same event priced differently on Polymarket vs Kalshi
- Both are prediction markets with similar contracts
- Exploit pricing inefficiencies

**Config**:
```python
{
    "polymarket_market_id": "...",
    "kalshi_event_ticker": "...",
    "min_spread": 0.02
}
```

---

## Funding Rate Arbitrage

**File**: `src/strategies/funding_rate_arbitrage.py`
**Providers**: Bybit, dYdX (derivatives)
**Type**: Carry trade

**Logic**: Collect funding payments by being on the paying side
- When funding is positive, shorts pay longs
- Go long spot, short perp = delta neutral + collect funding

**Config**:
```python
{
    "spot_provider": "binance",
    "perp_provider": "bybit",
    "pair": "BTCUSDT",
    "min_funding_rate": 0.01   # 0.01% per 8 hours
}
```

---

## Basis Trading

**File**: `src/strategies/basis_trading.py`
**Providers**: Spot + Futures exchanges
**Type**: Cash and carry

**Logic**: Profit from spot-futures price convergence
- Buy spot, short futures when futures premium is high
- Close at expiry when prices converge

**Config**:
```python
{
    "spot_provider": "binance",
    "futures_provider": "bybit",
    "pair": "BTCUSDT",
    "min_basis_pct": 0.5       # Minimum annualized basis
}
```

---

## Triangular Arbitrage

**File**: `src/strategies/triangular_arbitrage.py`
**Provider**: Single exchange with multiple pairs
**Type**: Cycle arbitrage

**Logic**: A → B → C → A where cycle profit > 0
- Example: USD → BTC → ETH → USD
- Must execute all three legs atomically

**Config**:
```python
{
    "provider": "binance",
    "pairs": ["BTCUSDT", "ETHBTC", "ETHUSDT"],
    "min_profit_pct": 0.05
}
```

---

## Momentum Trading

**File**: `src/strategies/momentum_trading.py`
**Provider**: Any
**Type**: Trend following

**Logic**: Enter in direction of recent price movement
- Uses moving average crossovers or breakouts
- Exit on reversal signals

**Config**:
```python
{
    "pair": "BTCUSDT",
    "fast_period": 10,         # Fast MA period
    "slow_period": 30,         # Slow MA period
    "position_size": 0.1       # 10% of balance
}
```

---

## Simple Market Making

**File**: `src/strategies/simple_market_making.py`
**Provider**: Any
**Type**: Spread capture

**Logic**: Place bid and ask orders, profit from spread
- Continuously quote two-sided markets
- Risk: inventory accumulation

**Config**:
```python
{
    "pair": "BTCUSDT",
    "spread_pct": 0.1,         # Bid-ask spread
    "order_size": 0.01,        # Size per order
    "max_inventory": 1.0       # Max position size
}
```

---

## Statistical Arbitrage

**File**: `src/strategies/statistical_arbitrage.py`
**Provider**: Any
**Type**: Mean reversion

**Logic**: Trade on deviations from statistical relationships
- Pairs trading, cointegration
- Enter when spread deviates, exit on reversion

**Config**:
```python
{
    "pair_a": "BTCUSDT",
    "pair_b": "ETHUSDT",
    "lookback_period": 100,
    "entry_zscore": 2.0,
    "exit_zscore": 0.5
}
```

---

## Liquidation Sniping

**File**: `src/strategies/liquidation_sniping.py`
**Provider**: Derivatives (Bybit, dYdX)
**Type**: Event-driven

**Logic**: Profit from liquidation cascades
- Detect large liquidations about to occur
- Position ahead of cascade

**Config**:
```python
{
    "provider": "bybit",
    "pair": "BTCUSDT",
    "min_liquidation_size": 100000  # USD
}
```

---

## High Probability Bond

**File**: `src/strategies/high_probability_bond.py`
**Provider**: Polymarket
**Type**: Value investing

**Logic**: Buy high-probability outcomes at discount
- Example: 95% likely outcome priced at $0.90
- Hold until resolution for 5.5% return

**Config**:
```python
{
    "min_probability": 0.90,   # Only trade >90% outcomes
    "max_price": 0.95,         # Buy below $0.95
    "max_position": 5000       # Max USDC allocation
}
```
