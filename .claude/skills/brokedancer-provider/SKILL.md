---
name: brokedancer-provider
description: |
  Exchange/platform provider integrations for BrokeDancer trading bot. Use when:
  (1) Adding a new exchange provider (Binance, Coinbase, etc.)
  (2) Modifying existing provider implementations
  (3) Debugging provider connection or API issues
  (4) Understanding the BaseProvider interface contract
  (5) Working with provider-specific configurations
  Providers abstract exchange APIs into a unified interface for strategies.
---

# BrokeDancer Provider Layer

## Quick Reference

**BaseProvider Interface** (`src/providers/base.py`):
```python
class BaseProvider(ABC):
    def connect(self) -> None                              # Establish connection
    def disconnect(self) -> None                           # Clean up
    def get_balance(asset: str = None) -> Dict[str, Balance]
    def get_orderbook(pair: str, depth: int = 100) -> Orderbook
    def place_order(pair, side, order_type, size, price=None) -> Order
    def get_order(order_id: str) -> Order
    def cancel_order(order_id: str) -> bool
    def get_markets() -> List[str]
```

**Data Models**:
- `OrderSide`: BUY, SELL
- `OrderType`: LIMIT, MARKET, FOK, IOC, GTC
- `OrderStatus`: PENDING, OPEN, FILLED, PARTIAL, CANCELLED, REJECTED
- `Balance`: asset, available, reserved, total
- `Orderbook`: pair, bids[], asks[], timestamp, best_bid, best_ask, spread, mid_price
- `Order`: order_id, pair, side, type, price, size, filled_size, status, is_complete

## Creating a New Provider

1. Create `src/providers/<name>.py`
2. Subclass `BaseProvider`
3. Implement all abstract methods
4. Add to factory (`src/providers/factory.py`)
5. Add config example (`.env.example.<name>`)

**Template**:
```python
from .base import BaseProvider, Balance, Order, Orderbook, OrderbookEntry, OrderSide, OrderStatus, OrderType

class NewProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self._connected = False

    def connect(self) -> None:
        # Initialize API client
        self._connected = True

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        # Return standardized Balance objects
        pass

    # ... implement remaining methods
```

## Supported Providers

| Provider | Type | Markets | Config Keys |
|----------|------|---------|-------------|
| polymarket | Prediction | Binary (YES/NO) | private_key, signature_type, funder |
| luno | Crypto | ZAR pairs | api_key_id, api_key_secret |
| kalshi | Prediction | US regulated | api_key, private_key_path |
| binance | Crypto | Global | api_key, api_secret |
| coinbase | Crypto | US | api_key, api_secret, passphrase |
| bybit | Derivatives | Perpetuals | api_key, api_secret |
| kraken | Crypto | Fiat pairs | api_key, private_key |
| dydx | DeFi | Perpetuals | stark_private_key, api_key |

## Provider-Specific Notes

See `references/providers.md` for detailed configuration and quirks per provider.

## Testing Providers

```bash
# Run provider tests
pytest tests/ -k "provider" -v

# Test specific provider connection
python -c "
from src.providers.factory import create_provider
p = create_provider('binance', {'api_key': '...', 'api_secret': '...'})
p.connect()
print(p.get_markets()[:5])
"
```

## Common Patterns

**Retry with backoff** (use the decorator):
```python
from src.utils import retry_with_backoff

@retry_with_backoff(max_attempts=3, initial_delay=1.0)
def get_balance(self, asset=None):
    ...
```

**WebSocket support** (optional):
- See `src/providers/luno_websocket.py` for event-driven pattern
- Implement `on_orderbook_update()`, `on_trade()` callbacks
