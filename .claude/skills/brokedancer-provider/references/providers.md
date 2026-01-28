# Provider-Specific Configuration

## Table of Contents
- [Polymarket](#polymarket)
- [Luno](#luno)
- [Kalshi](#kalshi)
- [Binance](#binance)
- [Coinbase](#coinbase)
- [Bybit](#bybit)
- [Kraken](#kraken)
- [dYdX](#dydx)

---

## Polymarket

**Type**: Prediction market (binary outcomes)
**File**: `src/providers/polymarket.py`
**SDK**: `py-clob-client`

**Config**:
```python
{
    "private_key": "0x...",        # Ethereum private key
    "signature_type": 1,           # 0=EOA, 1=Magic.link, 2=Gnosis Safe
    "funder": "0x...",             # Proxy wallet (Magic.link only)
    "market_id": "...",            # Optional: specific market
    "yes_token_id": "...",         # Optional: YES token
    "no_token_id": "..."           # Optional: NO token
}
```

**Quirks**:
- NOT a traditional exchange - trades binary outcome tokens
- Prices are probabilities (0.00-1.00), payout is $1.00 per winning token
- Only supports USDC collateral (6 decimals)
- Arbitrage: buy both sides when total < $1.00

---

## Luno

**Type**: Crypto exchange
**File**: `src/providers/luno.py`
**Markets**: ZAR pairs (XBTZAR, ETHZAR)

**Config**:
```python
{
    "api_key_id": "...",
    "api_key_secret": "...",
    "default_pair": "XBTZAR"
}
```

**WebSocket**: See `src/providers/luno_websocket.py` for real-time streams.

**Quirks**:
- South African exchange, ZAR-denominated
- Lower liquidity than global exchanges
- Useful for ZAR-crypto arbitrage

---

## Kalshi

**Type**: US-regulated prediction market
**File**: `src/providers/kalshi.py`
**Markets**: Event contracts (elections, economics)

**Config**:
```python
{
    "api_key": "...",
    "private_key_path": "/path/to/key.pem",  # RSA key for signing
    "api_base": "https://api.kalshi.com"
}
```

**Quirks**:
- CFTC-regulated, US residents only
- Higher volumes than Polymarket for some markets
- Cross-platform arbitrage opportunity with Polymarket

---

## Binance

**Type**: Crypto exchange (spot + futures)
**File**: `src/providers/binance.py`
**Markets**: Global (BTCUSDT, ETHUSDT, 500+ pairs)

**Config**:
```python
{
    "api_key": "...",
    "api_secret": "...",
    "testnet": False,              # Use testnet
    "recv_window": 5000            # Request timeout
}
```

**Quirks**:
- Highest global liquidity
- Rate limits: 1200 req/min (order), 10 orders/sec
- US users restricted (use Binance.US)

---

## Coinbase

**Type**: Crypto exchange (spot)
**File**: `src/providers/coinbase.py`
**Markets**: US regulated (BTC-USD, ETH-USD)

**Config**:
```python
{
    "api_key": "...",
    "api_secret": "...",
    "passphrase": "..."            # Coinbase Pro requirement
}
```

**Quirks**:
- Most regulated US exchange
- Lower fees for high volume
- Good for USD on/off ramps

---

## Bybit

**Type**: Derivatives exchange
**File**: `src/providers/bybit.py`
**Markets**: Perpetual futures (BTCUSDT, ETHUSDT)

**Config**:
```python
{
    "api_key": "...",
    "api_secret": "...",
    "testnet": False
}
```

**Quirks**:
- High leverage available (up to 100x)
- Funding rate arbitrage opportunities
- Inverse and USDT perpetuals

---

## Kraken

**Type**: Crypto exchange
**File**: `src/providers/kraken.py`
**Markets**: Fiat pairs (XBTUSD, XBTEUR)

**Config**:
```python
{
    "api_key": "...",
    "private_key": "..."           # Base64 encoded
}
```

**Quirks**:
- Deep EUR/USD liquidity
- Staking available
- Slower API than competitors

---

## dYdX

**Type**: Decentralized perpetuals
**File**: `src/providers/dydx.py`
**Markets**: Perps (BTC-USD, ETH-USD)

**Config**:
```python
{
    "stark_private_key": "0x...",  # StarkEx key
    "api_key": "...",
    "api_passphrase": "...",
    "api_secret": "...",
    "ethereum_address": "0x..."
}
```

**Quirks**:
- Layer 2 (StarkEx), low fees
- Self-custody (non-custodial)
- Complex key derivation process
