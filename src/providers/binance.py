"""
Binance provider for cryptocurrency trading.

Binance is the world's largest cryptocurrency exchange by volume.
Perfect for cross-exchange arbitrage, triangular arbitrage, and market making.

API Documentation: https://binance-docs.github.io/apidocs/spot/en/
"""

import logging
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from .base import (
    BaseProvider,
    Balance,
    Order,
    Orderbook,
    OrderbookEntry,
    OrderSide,
    OrderType,
    OrderStatus
)


logger = logging.getLogger(__name__)


class BinanceProvider(BaseProvider):
    """
    Binance cryptocurrency exchange provider.

    Largest global exchange with unmatched liquidity.
    Ideal for cross-exchange arbitrage and triangular arbitrage.
    """

    BASE_URL = "https://api.binance.com"
    WS_URL = "wss://stream.binance.com:9443"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Binance provider.

        Args:
            config: Configuration with:
                - api_key: Binance API key
                - api_secret: Binance API secret
                - default_pair: Optional default trading pair (e.g., "BTCUSDT")
                - testnet: Use testnet (default: False)
        """
        super().__init__(config)

        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.default_pair = config.get("default_pair", "BTCUSDT")
        self.testnet = config.get("testnet", False)

        if not self.api_key or not self.api_secret:
            raise ValueError("Binance requires api_key and api_secret")

        # Use testnet if enabled
        if self.testnet:
            self.BASE_URL = "https://testnet.binance.vision"

        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key
        })

        self._connected = False

        logger.info(f"Binance provider initialized ({'testnet' if self.testnet else 'mainnet'})")

    def connect(self) -> None:
        """Test connection to Binance API."""
        try:
            # Test connectivity
            url = f"{self.BASE_URL}/api/v3/ping"
            response = self.session.get(url)
            response.raise_for_status()

            # Test authentication
            self.get_balance()

            self._connected = True
            logger.info("✅ Connected to Binance")

        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Binance."""
        self.session.close()
        self._connected = False
        logger.info("Disconnected from Binance")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for authenticated requests."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _signed_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a signed request to Binance API."""
        if params is None:
            params = {}

        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._generate_signature(params)

        url = f"{self.BASE_URL}{endpoint}"

        if method == "GET":
            response = self.session.get(url, params=params)
        elif method == "POST":
            response = self.session.post(url, params=params)
        elif method == "DELETE":
            response = self.session.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Optional asset filter (e.g., "BTC", "USDT")

        Returns:
            Dict mapping asset to Balance
        """
        try:
            data = self._signed_request("GET", "/api/v3/account")

            balances = {}
            for bal in data.get("balances", []):
                asset_name = bal["asset"]

                # Skip if filtering and doesn't match
                if asset and asset_name != asset:
                    continue

                free = float(bal["free"])
                locked = float(bal["locked"])

                # Only include assets with non-zero balance
                if free > 0 or locked > 0:
                    balances[asset_name] = Balance(
                        asset=asset_name,
                        available=free,
                        reserved=locked,
                        total=free + locked
                    )

            return balances

        except Exception as e:
            logger.error(f"Error getting Binance balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 20) -> Orderbook:
        """
        Get orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            depth: Orderbook depth (5, 10, 20, 50, 100, 500, 1000, 5000)

        Returns:
            Orderbook with bids and asks
        """
        try:
            # Validate depth
            valid_depths = [5, 10, 20, 50, 100, 500, 1000, 5000]
            if depth not in valid_depths:
                depth = min(valid_depths, key=lambda x: abs(x - depth))

            url = f"{self.BASE_URL}/api/v3/depth"
            params = {"symbol": pair, "limit": depth}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse bids and asks
            bids = [
                OrderbookEntry(price=float(price), volume=float(qty))
                for price, qty in data.get("bids", [])
            ]

            asks = [
                OrderbookEntry(price=float(price), volume=float(qty))
                for price, qty in data.get("asks", [])
            ]

            return Orderbook(
                pair=pair,
                bids=bids,
                asks=asks,
                timestamp=data.get("lastUpdateId", int(time.time() * 1000))
            )

        except Exception as e:
            logger.error(f"Error getting Binance orderbook for {pair}: {e}")
            raise

    def place_order(
        self,
        pair: str,
        side: OrderSide,
        order_type: OrderType,
        size: float,
        price: Optional[float] = None,
        **kwargs
    ) -> Order:
        """
        Place an order on Binance.

        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            side: BUY or SELL
            order_type: MARKET, LIMIT, FOK, IOC, GTC
            size: Order quantity
            price: Limit price (required for limit orders)
            **kwargs: Additional parameters (timeInForce, etc.)

        Returns:
            Order object
        """
        try:
            params = {
                "symbol": pair,
                "side": side.name,
                "quantity": size
            }

            # Map order type
            if order_type == OrderType.MARKET:
                params["type"] = "MARKET"
            elif order_type in [OrderType.LIMIT, OrderType.GTC]:
                params["type"] = "LIMIT"
                params["timeInForce"] = "GTC"
                params["price"] = price
            elif order_type == OrderType.FOK:
                params["type"] = "LIMIT"
                params["timeInForce"] = "FOK"
                params["price"] = price
            elif order_type == OrderType.IOC:
                params["type"] = "LIMIT"
                params["timeInForce"] = "IOC"
                params["price"] = price
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Add additional parameters
            params.update(kwargs)

            data = self._signed_request("POST", "/api/v3/order", params)

            return Order(
                order_id=str(data.get("orderId")),
                pair=pair,
                side=side,
                type=order_type,
                price=float(data.get("price", price or 0)),
                size=float(data.get("origQty", size)),
                filled_size=float(data.get("executedQty", 0)),
                status=self._map_order_status(data.get("status"))
            )

        except Exception as e:
            logger.error(f"Error placing Binance order: {e}")
            raise

    def get_order(self, order_id: str, pair: Optional[str] = None) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID
            pair: Trading pair (required for Binance)

        Returns:
            Order object with current status
        """
        if not pair:
            pair = self.default_pair

        try:
            params = {
                "symbol": pair,
                "orderId": order_id
            }

            data = self._signed_request("GET", "/api/v3/order", params)

            return Order(
                order_id=str(data.get("orderId")),
                pair=data.get("symbol"),
                side=OrderSide.BUY if data.get("side") == "BUY" else OrderSide.SELL,
                type=self._map_order_type(data.get("type"), data.get("timeInForce")),
                price=float(data.get("price", 0)),
                size=float(data.get("origQty", 0)),
                filled_size=float(data.get("executedQty", 0)),
                status=self._map_order_status(data.get("status"))
            )

        except Exception as e:
            logger.error(f"Error getting Binance order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str, pair: Optional[str] = None) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            pair: Trading pair (required for Binance)

        Returns:
            True if successfully cancelled
        """
        if not pair:
            pair = self.default_pair

        try:
            params = {
                "symbol": pair,
                "orderId": order_id
            }

            self._signed_request("DELETE", "/api/v3/order", params)

            logger.info(f"Cancelled Binance order: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling Binance order {order_id}: {e}")
            return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all trading pairs.

        Returns:
            List of market dictionaries
        """
        try:
            url = f"{self.BASE_URL}/api/v3/exchangeInfo"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            symbols = data.get("symbols", [])

            result = []
            for symbol in symbols:
                if symbol.get("status") == "TRADING":
                    result.append({
                        "id": symbol.get("symbol"),
                        "base": symbol.get("baseAsset"),
                        "quote": symbol.get("quoteAsset"),
                        "status": symbol.get("status"),
                        "filters": symbol.get("filters", [])
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting Binance markets: {e}")
            raise

    def _map_order_status(self, binance_status: str) -> OrderStatus:
        """Map Binance order status to OrderStatus enum."""
        status_map = {
            "NEW": OrderStatus.OPEN,
            "PARTIALLY_FILLED": OrderStatus.OPEN,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "PENDING_CANCEL": OrderStatus.PENDING,
            "REJECTED": OrderStatus.CANCELLED,
            "EXPIRED": OrderStatus.CANCELLED,
        }
        return status_map.get(binance_status, OrderStatus.OPEN)

    def _map_order_type(self, type_str: str, time_in_force: str) -> OrderType:
        """Map Binance order type to OrderType enum."""
        if type_str == "MARKET":
            return OrderType.MARKET
        elif type_str == "LIMIT":
            if time_in_force == "FOK":
                return OrderType.FOK
            elif time_in_force == "IOC":
                return OrderType.IOC
            elif time_in_force == "GTC":
                return OrderType.GTC
            return OrderType.LIMIT
        return OrderType.LIMIT

    def get_ticker_price(self, pair: str) -> float:
        """
        Get current ticker price.

        Args:
            pair: Trading pair

        Returns:
            Current price
        """
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/price"
            params = {"symbol": pair}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            return float(data.get("price", 0))

        except Exception as e:
            logger.error(f"Error getting Binance ticker for {pair}: {e}")
            raise

    def get_24h_ticker(self, pair: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker statistics.

        Args:
            pair: Trading pair

        Returns:
            Dict with 24h volume, price change, etc.
        """
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            params = {"symbol": pair}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Error getting Binance 24h ticker for {pair}: {e}")
            raise
