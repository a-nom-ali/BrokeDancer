"""
Bybit provider for cryptocurrency derivatives trading.

Bybit is a leading derivatives exchange with high leverage and deep liquidity.
Perfect for perpetual futures, options, and advanced derivative strategies.

API Documentation: https://bybit-exchange.github.io/docs/v5/intro
"""

import logging
import time
import hmac
import hashlib
import requests
import json
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


class BybitProvider(BaseProvider):
    """
    Bybit derivatives exchange provider.

    Leading derivatives platform with high leverage and deep liquidity.
    Ideal for perpetual futures, funding rate arbitrage, and volatility strategies.
    """

    BASE_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bybit provider.

        Args:
            config: Configuration with:
                - api_key: Bybit API key
                - api_secret: Bybit API secret
                - default_pair: Optional default trading pair (e.g., "BTCUSDT")
                - testnet: Use testnet (default: False)
                - category: Trading category ("spot", "linear", "inverse", "option")
        """
        super().__init__(config)

        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.default_pair = config.get("default_pair", "BTCUSDT")
        self.testnet = config.get("testnet", False)
        self.category = config.get("category", "linear")  # linear = USDT perpetuals

        if not self.api_key or not self.api_secret:
            raise ValueError("Bybit requires api_key and api_secret")

        # Use testnet if enabled
        if self.testnet:
            self.BASE_URL = self.TESTNET_URL

        self.session = requests.Session()
        self.session.headers.update({
            "X-BAPI-API-KEY": self.api_key
        })

        self._connected = False
        self._recv_window = 5000  # 5 second receive window

        logger.info(f"Bybit provider initialized ({'testnet' if self.testnet else 'mainnet'}, category: {self.category})")

    def connect(self) -> None:
        """Test connection to Bybit API."""
        try:
            # Test connectivity
            url = f"{self.BASE_URL}/v5/market/time"
            response = self.session.get(url)
            response.raise_for_status()

            # Test authentication
            self.get_balance()

            self._connected = True
            logger.info("✅ Connected to Bybit")

        except Exception as e:
            logger.error(f"Failed to connect to Bybit: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Bybit."""
        self.session.close()
        self._connected = False
        logger.info("Disconnected from Bybit")

    def _generate_signature(self, timestamp: str, params_str: str) -> str:
        """
        Generate HMAC SHA256 signature for authenticated requests.

        Bybit V5 signature: HMAC_SHA256(timestamp + api_key + recv_window + params)
        """
        param_str = f"{timestamp}{self.api_key}{self._recv_window}{params_str}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make a signed request to Bybit V5 API."""
        timestamp = str(int(time.time() * 1000))

        if params is None:
            params = {}

        # Sort parameters and create query string
        sorted_params = dict(sorted(params.items()))
        params_str = urlencode(sorted_params) if sorted_params else ""

        # Generate signature
        signature = self._generate_signature(timestamp, params_str)

        # Set headers
        headers = {
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": str(self._recv_window),
            "Content-Type": "application/json"
        }

        url = f"{self.BASE_URL}{endpoint}"

        if method == "GET":
            response = self.session.get(url, params=params, headers=headers)
        elif method == "POST":
            response = self.session.post(url, json=params, headers=headers)
        elif method == "DELETE":
            response = self.session.delete(url, json=params, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        data = response.json()

        # Check Bybit response code
        if data.get("retCode") != 0:
            raise Exception(f"Bybit API error: {data.get('retMsg')}")

        return data.get("result", {})

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Optional asset filter (e.g., "USDT", "BTC")

        Returns:
            Dict mapping asset to Balance
        """
        try:
            params = {
                "accountType": "UNIFIED"  # Unified trading account
            }

            data = self._signed_request("GET", "/v5/account/wallet-balance", params)

            balances = {}
            for account in data.get("list", []):
                for coin in account.get("coin", []):
                    asset_name = coin.get("coin")

                    # Skip if filtering and doesn't match
                    if asset and asset_name != asset:
                        continue

                    equity = float(coin.get("equity", 0))
                    available = float(coin.get("availableToWithdraw", 0))
                    locked = equity - available

                    # Only include assets with non-zero balance
                    if equity > 0:
                        balances[asset_name] = Balance(
                            asset=asset_name,
                            available=available,
                            reserved=locked,
                            total=equity
                        )

            return balances

        except Exception as e:
            logger.error(f"Error getting Bybit balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 50) -> Orderbook:
        """
        Get orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            depth: Orderbook depth (1, 50, 200, 500)

        Returns:
            Orderbook with bids and asks
        """
        try:
            # Validate depth
            valid_depths = [1, 50, 200, 500]
            if depth not in valid_depths:
                depth = min(valid_depths, key=lambda x: abs(x - depth))

            params = {
                "category": self.category,
                "symbol": pair,
                "limit": depth
            }

            url = f"{self.BASE_URL}/v5/market/orderbook"
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")

            result = data.get("result", {})

            # Parse bids and asks
            bids = [
                OrderbookEntry(price=float(bid[0]), volume=float(bid[1]))
                for bid in result.get("b", [])
            ]

            asks = [
                OrderbookEntry(price=float(ask[0]), volume=float(ask[1]))
                for ask in result.get("a", [])
            ]

            return Orderbook(
                pair=pair,
                bids=bids,
                asks=asks,
                timestamp=int(result.get("ts", time.time() * 1000))
            )

        except Exception as e:
            logger.error(f"Error getting Bybit orderbook for {pair}: {e}")
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
        Place an order on Bybit.

        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            side: BUY or SELL
            order_type: MARKET, LIMIT, FOK, IOC, GTC
            size: Order quantity
            price: Limit price (required for limit orders)
            **kwargs: Additional parameters (reduce_only, close_on_trigger, etc.)

        Returns:
            Order object
        """
        try:
            params = {
                "category": self.category,
                "symbol": pair,
                "side": "Buy" if side == OrderSide.BUY else "Sell",
                "qty": str(size)
            }

            # Map order type
            if order_type == OrderType.MARKET:
                params["orderType"] = "Market"
            elif order_type in [OrderType.LIMIT, OrderType.GTC]:
                params["orderType"] = "Limit"
                params["timeInForce"] = "GTC"
                params["price"] = str(price)
            elif order_type == OrderType.FOK:
                params["orderType"] = "Limit"
                params["timeInForce"] = "FOK"
                params["price"] = str(price)
            elif order_type == OrderType.IOC:
                params["orderType"] = "Limit"
                params["timeInForce"] = "IOC"
                params["price"] = str(price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Add additional parameters
            if "reduce_only" in kwargs:
                params["reduceOnly"] = kwargs["reduce_only"]
            if "position_idx" in kwargs:
                params["positionIdx"] = kwargs["position_idx"]

            data = self._signed_request("POST", "/v5/order/create", params)

            return Order(
                order_id=data.get("orderId", ""),
                pair=pair,
                side=side,
                type=order_type,
                price=float(price or 0),
                size=size,
                filled_size=0,
                status=OrderStatus.OPEN
            )

        except Exception as e:
            logger.error(f"Error placing Bybit order: {e}")
            raise

    def get_order(self, order_id: str, pair: Optional[str] = None) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID
            pair: Trading pair (required for Bybit)

        Returns:
            Order object with current status
        """
        if not pair:
            pair = self.default_pair

        try:
            params = {
                "category": self.category,
                "symbol": pair,
                "orderId": order_id
            }

            data = self._signed_request("GET", "/v5/order/realtime", params)

            orders = data.get("list", [])
            if not orders:
                raise Exception(f"Order {order_id} not found")

            order_data = orders[0]

            return Order(
                order_id=order_data.get("orderId"),
                pair=order_data.get("symbol"),
                side=OrderSide.BUY if order_data.get("side") == "Buy" else OrderSide.SELL,
                type=self._map_order_type(order_data.get("orderType"), order_data.get("timeInForce")),
                price=float(order_data.get("price", 0)),
                size=float(order_data.get("qty", 0)),
                filled_size=float(order_data.get("cumExecQty", 0)),
                status=self._map_order_status(order_data.get("orderStatus"))
            )

        except Exception as e:
            logger.error(f"Error getting Bybit order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str, pair: Optional[str] = None) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            pair: Trading pair (required for Bybit)

        Returns:
            True if successfully cancelled
        """
        if not pair:
            pair = self.default_pair

        try:
            params = {
                "category": self.category,
                "symbol": pair,
                "orderId": order_id
            }

            self._signed_request("POST", "/v5/order/cancel", params)

            logger.info(f"Cancelled Bybit order: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling Bybit order {order_id}: {e}")
            return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all trading pairs.

        Returns:
            List of market dictionaries
        """
        try:
            params = {
                "category": self.category
            }

            url = f"{self.BASE_URL}/v5/market/instruments-info"
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")

            result = []
            for instrument in data.get("result", {}).get("list", []):
                if instrument.get("status") == "Trading":
                    result.append({
                        "id": instrument.get("symbol"),
                        "base": instrument.get("baseCoin"),
                        "quote": instrument.get("quoteCoin"),
                        "status": instrument.get("status"),
                        "contract_type": instrument.get("contractType"),
                        "leverage": instrument.get("leverageFilter", {})
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting Bybit markets: {e}")
            raise

    def _map_order_status(self, bybit_status: str) -> OrderStatus:
        """Map Bybit order status to OrderStatus enum."""
        status_map = {
            "Created": OrderStatus.OPEN,
            "New": OrderStatus.OPEN,
            "PartiallyFilled": OrderStatus.OPEN,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "PartiallyFilledCanceled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.CANCELLED,
        }
        return status_map.get(bybit_status, OrderStatus.OPEN)

    def _map_order_type(self, type_str: str, time_in_force: str) -> OrderType:
        """Map Bybit order type to OrderType enum."""
        if type_str == "Market":
            return OrderType.MARKET
        elif type_str == "Limit":
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
            params = {
                "category": self.category,
                "symbol": pair
            }

            url = f"{self.BASE_URL}/v5/market/tickers"
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")

            tickers = data.get("result", {}).get("list", [])
            if tickers:
                return float(tickers[0].get("lastPrice", 0))
            return 0.0

        except Exception as e:
            logger.error(f"Error getting Bybit ticker for {pair}: {e}")
            raise

    def get_funding_rate(self, pair: str) -> Dict[str, Any]:
        """
        Get current and predicted funding rate (perpetuals only).

        Args:
            pair: Trading pair

        Returns:
            Dict with current and predicted funding rates
        """
        try:
            params = {
                "category": self.category,
                "symbol": pair
            }

            url = f"{self.BASE_URL}/v5/market/tickers"
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")

            tickers = data.get("result", {}).get("list", [])
            if tickers:
                ticker = tickers[0]
                return {
                    "funding_rate": float(ticker.get("fundingRate", 0)),
                    "predicted_funding_rate": float(ticker.get("predictedFundingRate", 0)),
                    "next_funding_time": ticker.get("nextFundingTime")
                }
            return {}

        except Exception as e:
            logger.error(f"Error getting Bybit funding rate for {pair}: {e}")
            raise
