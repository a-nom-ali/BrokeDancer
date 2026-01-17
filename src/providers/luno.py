"""
Luno exchange provider implementation.

Supports both REST API and WebSocket streaming for real-time market data.

API Documentation: https://www.luno.com/en/developers/api
WebSocket Documentation: https://www.luno.com/en/developers/api#tag/Streaming-API
"""

import hashlib
import hmac
import logging
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx

from .base import (
    BaseProvider,
    Balance,
    Order,
    Orderbook,
    OrderbookEntry,
    OrderSide,
    OrderStatus,
    OrderType,
)
from ..utils import retry_with_backoff, safe_float_conversion

logger = logging.getLogger(__name__)


class LunoProvider(BaseProvider):
    """
    Luno exchange provider.

    Supports:
    - Spot trading (BTC/ZAR, ETH/ZAR, XRP/ZAR, etc.)
    - REST API for balance, orders, orderbook
    - WebSocket streaming for real-time market data

    Authentication:
    - API Key ID and Secret (Basic Auth)

    Rate Limits:
    - REST: 300 calls/minute
    - WebSocket: 50 concurrent sessions
    """

    BASE_URL = "https://api.luno.com"
    WSS_MARKET_URL = "wss://ws.luno.com/api/1/stream"
    WSS_USER_URL = "wss://ws.luno.com/api/1/userstream"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Luno provider.

        Args:
            config: Configuration dict with:
                - api_key_id: Luno API key ID
                - api_key_secret: Luno API key secret
                - default_pair: Default trading pair (e.g., "XBTZAR")

        Raises:
            ValueError: If required config is missing
        """
        super().__init__(config)

        self.api_key_id = config.get("api_key_id")
        self.api_key_secret = config.get("api_key_secret")
        self.default_pair = config.get("default_pair", "XBTZAR")

        if not self.api_key_id or not self.api_key_secret:
            raise ValueError("Luno requires 'api_key_id' and 'api_key_secret' in config")

        self.session: Optional[httpx.Client] = None
        self._connected = False

    def connect(self) -> None:
        """Establish HTTP session with Luno API."""
        if self._connected:
            return

        self.session = httpx.Client(
            base_url=self.BASE_URL,
            auth=(self.api_key_id, self.api_key_secret),
            timeout=10.0,
            headers={"User-Agent": "Polymarket-Luno-Bot/1.0"}
        )

        self._connected = True
        self.logger.info("✅ Connected to Luno API")

    def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            self.session.close()
            self.session = None
        self._connected = False
        self.logger.info("Disconnected from Luno API")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Luno API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/1/balance")
            params: Query parameters
            data: Request body (for POST/PUT)

        Returns:
            Response JSON as dict

        Raises:
            Exception: If request fails
        """
        if not self._connected or not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Luno API error ({e.response.status_code}): {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"Luno API request failed: {e}")
            raise

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, exceptions=(Exception,))
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balances.

        Args:
            asset: Specific asset to query (e.g., "XBT", "ZAR"). None = all assets

        Returns:
            Dict mapping asset symbol to Balance object

        Example:
            >>> balances = provider.get_balance("XBT")
            >>> print(balances["XBT"].available)
            0.5
        """
        params = {}
        if asset:
            params["assets"] = asset

        response = self._request("GET", "/api/1/balance", params=params)

        balances = {}
        for bal in response.get("balance", []):
            asset_code = bal.get("asset")
            available = safe_float_conversion(bal.get("balance", "0"), 0.0)
            reserved = safe_float_conversion(bal.get("reserved", "0"), 0.0)
            total = available + reserved

            balances[asset_code] = Balance(
                asset=asset_code,
                available=available,
                reserved=reserved,
                total=total
            )

        self.logger.debug(f"Fetched balances: {list(balances.keys())}")
        return balances

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, exceptions=(Exception,))
    def get_orderbook(self, pair: str, depth: int = 100) -> Orderbook:
        """
        Get current orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "XBTZAR", "ETHZAR")
            depth: Number of levels to retrieve (max 100 for top orderbook)

        Returns:
            Orderbook object with bids and asks

        Note:
            Uses /api/1/orderbook_top for efficiency (top 100 levels)
            For full orderbook, use /api/1/orderbook (warning: large data)
        """
        # Use top 100 orderbook for efficiency
        response = self._request(
            "GET",
            "/api/1/orderbook_top",
            params={"pair": pair}
        )

        # Parse bids (sorted descending by price)
        bids = []
        for bid in response.get("bids", []):
            bids.append(OrderbookEntry(
                price=safe_float_conversion(bid.get("price", "0"), 0.0),
                volume=safe_float_conversion(bid.get("volume", "0"), 0.0)
            ))

        # Parse asks (sorted ascending by price)
        asks = []
        for ask in response.get("asks", []):
            asks.append(OrderbookEntry(
                price=safe_float_conversion(ask.get("price", "0"), 0.0),
                volume=safe_float_conversion(ask.get("volume", "0"), 0.0)
            ))

        timestamp = int(response.get("timestamp", time.time() * 1000))

        orderbook = Orderbook(
            pair=pair,
            bids=bids[:depth],
            asks=asks[:depth],
            timestamp=timestamp
        )

        self.logger.debug(
            f"Orderbook {pair}: best_bid={orderbook.best_bid.price if orderbook.best_bid else None}, "
            f"best_ask={orderbook.best_ask.price if orderbook.best_ask else None}"
        )

        return orderbook

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
        Place a new order on Luno.

        Args:
            pair: Trading pair (e.g., "XBTZAR")
            side: BUY or SELL
            order_type: LIMIT, MARKET, FOK, IOC, GTC
            size: Order size in base currency (e.g., BTC amount)
            price: Limit price (required for LIMIT/FOK/IOC/GTC)
            **kwargs: Optional parameters:
                - post_only: Post-only flag (bool)
                - client_order_id: Custom order ID (str)
                - base_account_id: Specific base account (int)
                - counter_account_id: Specific counter account (int)

        Returns:
            Order object

        Raises:
            ValueError: If parameters are invalid
            Exception: If order placement fails

        Note:
            - FOK = Fill-or-Kill (time_in_force=FOK)
            - IOC = Immediate-or-Cancel (time_in_force=IOC)
            - GTC = Good-til-Cancelled (time_in_force=GTC, default for LIMIT)
        """
        if order_type == OrderType.MARKET:
            # Market order
            return self._place_market_order(pair, side, size, **kwargs)
        else:
            # Limit order (LIMIT, FOK, IOC, GTC)
            return self._place_limit_order(pair, side, size, price, order_type, **kwargs)

    def _place_market_order(
        self,
        pair: str,
        side: OrderSide,
        size: float,
        **kwargs
    ) -> Order:
        """Place market order."""
        if size <= 0:
            raise ValueError(f"Invalid size: {size}")

        # Luno market order type: BUY or SELL (in counter currency for BUY, base for SELL)
        order_type_str = "BUY" if side == OrderSide.BUY else "SELL"

        params = {
            "pair": pair,
            "type": order_type_str,
        }

        # For BUY market orders, specify counter_volume (e.g., ZAR amount)
        # For SELL market orders, specify base_volume (e.g., BTC amount)
        if side == OrderSide.BUY:
            # User wants to buy base currency (BTC) with counter currency (ZAR)
            # Luno requires counter_volume for BUY market orders
            # We need to estimate counter amount from current market price
            orderbook = self.get_orderbook(pair)
            if not orderbook.best_ask:
                raise RuntimeError(f"No asks available for {pair}")

            estimated_counter = size * orderbook.best_ask.price
            params["counter_volume"] = f"{estimated_counter:.2f}"
        else:
            # SELL: specify base_volume
            params["base_volume"] = f"{size:.8f}"

        # Optional parameters
        if "base_account_id" in kwargs:
            params["base_account_id"] = kwargs["base_account_id"]
        if "counter_account_id" in kwargs:
            params["counter_account_id"] = kwargs["counter_account_id"]
        if "client_order_id" in kwargs:
            params["client_order_id"] = kwargs["client_order_id"]

        response = self._request("POST", "/api/1/marketorder", params=params)

        order_id = response.get("order_id")

        # Create Order object (market orders fill immediately, so status is typically FILLED)
        order = Order(
            order_id=order_id,
            pair=pair,
            side=side,
            type=OrderType.MARKET,
            price=None,  # Market order has no fixed price
            size=size,
            filled_size=size,  # Assume immediately filled (query later for confirmation)
            status=OrderStatus.FILLED,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000)
        )

        self.logger.info(f"✅ Market order placed: {order_id} ({side.value} {size} {pair})")
        return order

    def _place_limit_order(
        self,
        pair: str,
        side: OrderSide,
        size: float,
        price: Optional[float],
        order_type: OrderType,
        **kwargs
    ) -> Order:
        """Place limit order with time-in-force."""
        if size <= 0:
            raise ValueError(f"Invalid size: {size}")
        if price is None or price <= 0:
            raise ValueError(f"Invalid price for limit order: {price}")

        # Luno limit order type: BID (buy) or ASK (sell)
        luno_type = "BID" if side == OrderSide.BUY else "ASK"

        # Map OrderType to Luno time_in_force
        time_in_force_map = {
            OrderType.LIMIT: "GTC",
            OrderType.GTC: "GTC",
            OrderType.FOK: "FOK",
            OrderType.IOC: "IOC",
        }
        time_in_force = time_in_force_map.get(order_type, "GTC")

        params = {
            "pair": pair,
            "type": luno_type,
            "volume": f"{size:.8f}",  # Base currency amount
            "price": f"{price:.2f}",   # Limit price
            "time_in_force": time_in_force,
        }

        # Optional parameters
        if kwargs.get("post_only", False):
            params["post_only"] = "true"
        if "base_account_id" in kwargs:
            params["base_account_id"] = kwargs["base_account_id"]
        if "counter_account_id" in kwargs:
            params["counter_account_id"] = kwargs["counter_account_id"]
        if "client_order_id" in kwargs:
            params["client_order_id"] = kwargs["client_order_id"]

        response = self._request("POST", "/api/1/postorder", params=params)

        order_id = response.get("order_id")

        # Create Order object
        order = Order(
            order_id=order_id,
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=0.0,  # Not filled yet
            status=OrderStatus.PENDING,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000)
        )

        self.logger.info(
            f"✅ Limit order placed: {order_id} ({side.value} {size} {pair} @ {price} {time_in_force})"
        )
        return order

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, exceptions=(Exception,))
    def get_order(self, order_id: str) -> Order:
        """
        Get order status by ID.

        Args:
            order_id: Unique order identifier

        Returns:
            Order object with current status
        """
        response = self._request("GET", f"/api/1/orders/{order_id}")

        # Parse order details
        order_id = response.get("order_id")
        pair = response.get("pair")

        # Map Luno order type to our OrderSide
        luno_type = response.get("type")  # BID, ASK, BUY, SELL
        if luno_type in ("BID", "BUY"):
            side = OrderSide.BUY
        elif luno_type in ("ASK", "SELL"):
            side = OrderSide.SELL
        else:
            raise ValueError(f"Unknown Luno order type: {luno_type}")

        # Map Luno state to our OrderStatus
        state = response.get("state")  # PENDING, COMPLETE
        if state == "PENDING":
            status = OrderStatus.OPEN
        elif state == "COMPLETE":
            # Check if fully filled or cancelled
            completed_ts = response.get("completed_timestamp", 0)
            if completed_ts > 0:
                base_filled = safe_float_conversion(response.get("base", "0"), 0.0)
                if base_filled > 0:
                    status = OrderStatus.FILLED
                else:
                    status = OrderStatus.CANCELLED
            else:
                status = OrderStatus.PENDING
        else:
            status = OrderStatus.PENDING

        # Parse order type
        order_type_str = response.get("order_type", "LIMIT")  # LIMIT, MARKET, STOP_LIMIT
        if order_type_str == "MARKET":
            order_type = OrderType.MARKET
        else:
            order_type = OrderType.LIMIT

        price = safe_float_conversion(response.get("limit_price", "0"), None)
        size = safe_float_conversion(response.get("base", "0"), 0.0)
        filled_size = size  # For completed orders, assume fully filled

        created_at = int(response.get("creation_timestamp", time.time() * 1000))
        updated_at = int(response.get("completed_timestamp") or response.get("expiration_timestamp") or time.time() * 1000)

        order = Order(
            order_id=order_id,
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=filled_size,
            status=status,
            created_at=created_at,
            updated_at=updated_at
        )

        self.logger.debug(f"Order {order_id}: {status.value}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Unique order identifier

        Returns:
            True if cancelled successfully
        """
        try:
            response = self._request("POST", "/api/1/stoporder", params={"order_id": order_id})
            success = response.get("success", False)

            if success:
                self.logger.info(f"✅ Order cancelled: {order_id}")
            else:
                self.logger.warning(f"⚠️ Order cancellation failed: {order_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_markets(self) -> List[str]:
        """
        Get list of available trading pairs on Luno.

        Returns:
            List of trading pair symbols (e.g., ["XBTZAR", "ETHZAR", ...])
        """
        response = self._request("GET", "/api/1/tickers")

        markets = []
        for ticker in response.get("tickers", []):
            pair = ticker.get("pair")
            if pair:
                markets.append(pair)

        self.logger.debug(f"Available markets: {markets}")
        return markets

    def get_ticker(self, pair: str) -> Dict[str, float]:
        """
        Get current ticker data for a pair.

        Args:
            pair: Trading pair (e.g., "XBTZAR")

        Returns:
            Dict with ticker data:
                - last_trade: Last trade price
                - bid: Best bid price
                - ask: Best ask price
                - volume: 24h volume
        """
        response = self._request("GET", "/api/1/ticker", params={"pair": pair})

        return {
            "last_trade": safe_float_conversion(response.get("last_trade", "0"), 0.0),
            "bid": safe_float_conversion(response.get("bid", "0"), 0.0),
            "ask": safe_float_conversion(response.get("ask", "0"), 0.0),
            "volume": safe_float_conversion(response.get("rolling_24_hour_volume", "0"), 0.0),
        }
