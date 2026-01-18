"""
Coinbase Advanced Trade provider for cryptocurrency trading.

Coinbase is the largest US-based cryptocurrency exchange.
Perfect for US market access, regulatory compliance, and cross-exchange arbitrage.

API Documentation: https://docs.cloud.coinbase.com/advanced-trade-api/docs/
"""

import logging
import time
import hmac
import hashlib
import requests
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal

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


class CoinbaseProvider(BaseProvider):
    """
    Coinbase Advanced Trade API provider.

    Largest US-based exchange with regulatory compliance.
    Ideal for US market access and cross-exchange arbitrage with Binance.
    """

    BASE_URL = "https://api.coinbase.com/api/v3/brokerage"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Coinbase provider.

        Args:
            config: Configuration with:
                - api_key: Coinbase API key
                - api_secret: Coinbase API secret
                - default_pair: Optional default trading pair (e.g., "BTC-USD")
                - sandbox: Use sandbox (default: False)
        """
        super().__init__(config)

        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.default_pair = config.get("default_pair", "BTC-USD")
        self.sandbox = config.get("sandbox", False)

        if not self.api_key or not self.api_secret:
            raise ValueError("Coinbase requires api_key and api_secret")

        # Use sandbox if enabled
        if self.sandbox:
            self.BASE_URL = "https://api-public.sandbox.exchange.coinbase.com"

        self.session = requests.Session()
        self._connected = False

        logger.info(f"Coinbase provider initialized ({'sandbox' if self.sandbox else 'production'})")

    def connect(self) -> None:
        """Test connection to Coinbase API."""
        try:
            # Test connectivity by getting accounts
            self.get_balance()

            self._connected = True
            logger.info("✅ Connected to Coinbase")

        except Exception as e:
            logger.error(f"Failed to connect to Coinbase: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Coinbase."""
        self.session.close()
        self._connected = False
        logger.info("Disconnected from Coinbase")

    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        Generate signature for authenticated requests.

        Uses CB-ACCESS-SIGN header with HMAC SHA256.
        """
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make a signed request to Coinbase Advanced Trade API."""
        timestamp = str(int(time.time()))

        # Build full path
        path = endpoint
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            path = f"{endpoint}?{query_string}"

        # Prepare body
        body = ""
        if data:
            body = json.dumps(data)

        # Generate signature
        signature = self._generate_signature(timestamp, method, path, body)

        # Set headers
        headers = {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

        url = f"{self.BASE_URL}{endpoint}"

        if method == "GET":
            response = self.session.get(url, headers=headers, params=params)
        elif method == "POST":
            response = self.session.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = self.session.delete(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Optional asset filter (e.g., "BTC", "USD")

        Returns:
            Dict mapping asset to Balance
        """
        try:
            data = self._signed_request("GET", "/accounts")

            balances = {}
            for account in data.get("accounts", []):
                currency = account.get("currency")

                # Skip if filtering and doesn't match
                if asset and currency != asset:
                    continue

                available = float(account.get("available_balance", {}).get("value", 0))
                hold = float(account.get("hold", {}).get("value", 0))

                # Only include assets with non-zero balance
                if available > 0 or hold > 0:
                    balances[currency] = Balance(
                        asset=currency,
                        available=available,
                        reserved=hold,
                        total=available + hold
                    )

            return balances

        except Exception as e:
            logger.error(f"Error getting Coinbase balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 50) -> Orderbook:
        """
        Get orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "BTC-USD")
            depth: Orderbook depth (default: 50)

        Returns:
            Orderbook with bids and asks
        """
        try:
            # Coinbase uses product_book endpoint
            endpoint = f"/products/{pair}/book"
            params = {"limit": min(depth, 500)}  # Max 500

            data = self._signed_request("GET", endpoint, params=params)

            # Parse bids and asks
            bids = [
                OrderbookEntry(price=float(bid["price"]), volume=float(bid["size"]))
                for bid in data.get("bids", [])
            ]

            asks = [
                OrderbookEntry(price=float(ask["price"]), volume=float(ask["size"]))
                for ask in data.get("asks", [])
            ]

            return Orderbook(
                pair=pair,
                bids=bids,
                asks=asks,
                timestamp=int(time.time() * 1000)
            )

        except Exception as e:
            logger.error(f"Error getting Coinbase orderbook for {pair}: {e}")
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
        Place an order on Coinbase.

        Args:
            pair: Trading pair (e.g., "BTC-USD")
            side: BUY or SELL
            order_type: MARKET, LIMIT, FOK, IOC, GTC
            size: Order quantity (in base currency)
            price: Limit price (required for limit orders)
            **kwargs: Additional parameters

        Returns:
            Order object
        """
        try:
            order_config = {}

            # Map order type
            if order_type == OrderType.MARKET:
                order_config = {
                    "market_market_ioc": {
                        "quote_size" if side == OrderSide.BUY else "base_size": str(size)
                    }
                }
            elif order_type in [OrderType.LIMIT, OrderType.GTC]:
                order_config = {
                    "limit_limit_gtc": {
                        "base_size": str(size),
                        "limit_price": str(price),
                        "post_only": kwargs.get("post_only", False)
                    }
                }
            elif order_type == OrderType.FOK:
                order_config = {
                    "limit_limit_fok": {
                        "base_size": str(size),
                        "limit_price": str(price)
                    }
                }
            elif order_type == OrderType.IOC:
                # Coinbase uses "limit_limit_gtd" with immediate expiry for IOC
                order_config = {
                    "limit_limit_gtd": {
                        "base_size": str(size),
                        "limit_price": str(price),
                        "end_time": str(int(time.time()) + 60)  # 1 minute expiry
                    }
                }
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            request_data = {
                "product_id": pair,
                "side": side.name,
                "client_order_id": kwargs.get("client_order_id", f"order_{int(time.time() * 1000)}"),
                "order_configuration": order_config
            }

            data = self._signed_request("POST", "/orders", data=request_data)

            # Parse response
            order_data = data.get("success_response", {})

            return Order(
                order_id=order_data.get("order_id", ""),
                pair=pair,
                side=side,
                type=order_type,
                price=float(price or 0),
                size=size,
                filled_size=0,  # New orders start unfilled
                status=OrderStatus.OPEN
            )

        except Exception as e:
            logger.error(f"Error placing Coinbase order: {e}")
            raise

    def get_order(self, order_id: str, pair: Optional[str] = None) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID
            pair: Trading pair (not required for Coinbase)

        Returns:
            Order object with current status
        """
        try:
            endpoint = f"/orders/historical/{order_id}"
            data = self._signed_request("GET", endpoint)

            order_data = data.get("order", {})

            return Order(
                order_id=order_data.get("order_id"),
                pair=order_data.get("product_id"),
                side=OrderSide.BUY if order_data.get("side") == "BUY" else OrderSide.SELL,
                type=self._map_order_type(order_data.get("order_type")),
                price=float(order_data.get("average_filled_price", 0)) or float(order_data.get("limit_price", 0)),
                size=float(order_data.get("order_size", 0)),
                filled_size=float(order_data.get("filled_size", 0)),
                status=self._map_order_status(order_data.get("status"))
            )

        except Exception as e:
            logger.error(f"Error getting Coinbase order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str, pair: Optional[str] = None) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            pair: Trading pair (not required for Coinbase)

        Returns:
            True if successfully cancelled
        """
        try:
            endpoint = f"/orders/batch_cancel"
            data = {
                "order_ids": [order_id]
            }

            response = self._signed_request("POST", endpoint, data=data)

            # Check if cancellation was successful
            results = response.get("results", [])
            if results and results[0].get("success"):
                logger.info(f"Cancelled Coinbase order: {order_id}")
                return True
            else:
                logger.warning(f"Failed to cancel Coinbase order: {order_id}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling Coinbase order {order_id}: {e}")
            return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all trading pairs.

        Returns:
            List of market dictionaries
        """
        try:
            data = self._signed_request("GET", "/products")

            result = []
            for product in data.get("products", []):
                # Only include active products
                if product.get("status") == "online":
                    result.append({
                        "id": product.get("product_id"),
                        "base": product.get("base_currency_id"),
                        "quote": product.get("quote_currency_id"),
                        "status": product.get("status"),
                        "min_size": product.get("base_min_size"),
                        "max_size": product.get("base_max_size"),
                        "price_increment": product.get("quote_increment")
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting Coinbase markets: {e}")
            raise

    def _map_order_status(self, coinbase_status: str) -> OrderStatus:
        """Map Coinbase order status to OrderStatus enum."""
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "FILLED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "EXPIRED": OrderStatus.CANCELLED,
            "FAILED": OrderStatus.CANCELLED,
            "PENDING": OrderStatus.PENDING,
        }
        return status_map.get(coinbase_status, OrderStatus.OPEN)

    def _map_order_type(self, type_str: str) -> OrderType:
        """Map Coinbase order type to OrderType enum."""
        type_map = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP": OrderType.LIMIT,
            "STOP_LIMIT": OrderType.LIMIT,
        }
        return type_map.get(type_str, OrderType.LIMIT)

    def get_ticker_price(self, pair: str) -> float:
        """
        Get current ticker price.

        Args:
            pair: Trading pair

        Returns:
            Current price
        """
        try:
            endpoint = f"/products/{pair}/ticker"
            data = self._signed_request("GET", endpoint)

            return float(data.get("price", 0))

        except Exception as e:
            logger.error(f"Error getting Coinbase ticker for {pair}: {e}")
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
            endpoint = f"/products/{pair}/stats"
            data = self._signed_request("GET", endpoint)

            return {
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "volume": data.get("volume"),
                "last": data.get("last")
            }

        except Exception as e:
            logger.error(f"Error getting Coinbase 24h ticker for {pair}: {e}")
            raise
