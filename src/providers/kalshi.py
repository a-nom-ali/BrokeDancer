"""
Kalshi provider for prediction market trading.

Kalshi is a US-regulated prediction market platform with $23.8B in 2025 volume.
Ideal for cross-platform arbitrage with Polymarket (documented $40M+ opportunity).

API Documentation: https://kalshi.com/api
"""

import logging
import time
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

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


class KalshiProvider(BaseProvider):
    """
    Kalshi prediction market provider.

    US-regulated platform for event contracts and prediction markets.
    Perfect for cross-platform arbitrage with Polymarket.
    """

    BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Kalshi provider.

        Args:
            config: Configuration with:
                - email: Kalshi account email
                - password: Kalshi account password
                - api_key: Optional API key (alternative to email/password)
                - default_market: Optional default market ticker
        """
        super().__init__(config)

        self.email = config.get("email")
        self.password = config.get("password")
        self.api_key = config.get("api_key")
        self.default_market = config.get("default_market", "")

        # Session management
        self.session = requests.Session()
        self.auth_token = None
        self.token_expiry = 0

        self._connected = False

        logger.info("Kalshi provider initialized")

    def connect(self) -> None:
        """Authenticate with Kalshi API."""
        try:
            if self.api_key:
                # Use API key authentication
                self.auth_token = self.api_key
                self.session.headers.update({
                    "Authorization": f"Bearer {self.api_key}"
                })
            else:
                # Use email/password login
                if not self.email or not self.password:
                    raise ValueError("Kalshi requires either api_key or email+password")

                login_url = f"{self.BASE_URL}/login"
                response = self.session.post(
                    login_url,
                    json={
                        "email": self.email,
                        "password": self.password
                    }
                )
                response.raise_for_status()

                data = response.json()
                self.auth_token = data.get("token")
                self.token_expiry = time.time() + (data.get("expires_in", 3600))

                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })

            self._connected = True
            logger.info("✅ Connected to Kalshi")

        except Exception as e:
            logger.error(f"Failed to connect to Kalshi: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Kalshi."""
        try:
            if self.auth_token and not self.api_key:
                # Logout if using email/password
                logout_url = f"{self.BASE_URL}/logout"
                self.session.post(logout_url)

            self.session.close()
            self._connected = False
            logger.info("Disconnected from Kalshi")

        except Exception as e:
            logger.error(f"Error disconnecting from Kalshi: {e}")

    def _ensure_authenticated(self):
        """Ensure we have a valid auth token."""
        if not self._connected:
            self.connect()

        # Check if token expired (for email/password auth)
        if not self.api_key and time.time() >= self.token_expiry - 300:
            logger.info("Auth token expiring soon, refreshing...")
            self.connect()

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Asset to get balance for (Kalshi uses USD)

        Returns:
            Dict mapping asset to Balance
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/portfolio/balance"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            # Kalshi balances are in cents, convert to dollars
            balance_cents = data.get("balance", 0)
            balance_usd = balance_cents / 100.0

            return {
                "USD": Balance(
                    asset="USD",
                    available=balance_usd,
                    reserved=0.0,  # Kalshi doesn't separate reserved
                    total=balance_usd
                )
            }

        except Exception as e:
            logger.error(f"Error getting Kalshi balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 20) -> Orderbook:
        """
        Get orderbook for a market.

        Args:
            pair: Market ticker (e.g., "INXD-24JAN17-B100")
            depth: Order book depth (not used by Kalshi API)

        Returns:
            Orderbook with bids and asks
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/markets/{pair}/orderbook"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            orderbook_data = data.get("orderbook", {})

            # Parse bids (YES side)
            yes_bids = []
            for level in orderbook_data.get("yes", []):
                # Kalshi prices are 0-100 (cents), convert to 0-1.00
                price = level[0] / 100.0
                volume = level[1]
                yes_bids.append(OrderbookEntry(price=price, volume=volume))

            # Parse asks (NO side)
            no_asks = []
            for level in orderbook_data.get("no", []):
                price = level[0] / 100.0
                volume = level[1]
                no_asks.append(OrderbookEntry(price=price, volume=volume))

            # Sort bids descending, asks ascending
            yes_bids.sort(key=lambda x: x.price, reverse=True)
            no_asks.sort(key=lambda x: x.price)

            return Orderbook(
                pair=pair,
                bids=yes_bids,
                asks=no_asks,
                timestamp=int(time.time() * 1000)
            )

        except Exception as e:
            logger.error(f"Error getting Kalshi orderbook for {pair}: {e}")
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
        Place an order on Kalshi.

        Args:
            pair: Market ticker
            side: BUY or SELL
            order_type: LIMIT, MARKET, FOK, etc.
            size: Number of contracts
            price: Limit price (0-1.00, converted to cents)
            **kwargs: Additional parameters

        Returns:
            Order object
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/portfolio/orders"

            # Convert price from 0-1.00 to 0-100 (cents)
            price_cents = int(price * 100) if price else None

            # Map order types
            kalshi_type = "limit" if order_type in [OrderType.LIMIT, OrderType.GTC] else "market"

            # Determine action (buy_yes, sell_yes, etc.)
            action_map = {
                (OrderSide.BUY, True): "buy",
                (OrderSide.SELL, True): "sell"
            }
            action = action_map.get((side, True), "buy")

            payload = {
                "ticker": pair,
                "action": action,
                "count": int(size),
                "type": kalshi_type,
                "side": "yes"  # Default to YES side
            }

            if price_cents is not None:
                payload["yes_price"] = price_cents

            # Add expiration for FOK orders
            if order_type == OrderType.FOK:
                payload["expiration_ts"] = int(time.time() + 60) * 1000  # 60 second expiry

            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            order_data = data.get("order", {})

            return Order(
                order_id=order_data.get("order_id", ""),
                pair=pair,
                side=side,
                type=order_type,
                price=price,
                size=size,
                filled_size=order_data.get("queue_position", 0),
                status=self._map_order_status(order_data.get("status", "open"))
            )

        except Exception as e:
            logger.error(f"Error placing Kalshi order: {e}")
            raise

    def get_order(self, order_id: str) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID

        Returns:
            Order object with current status
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/portfolio/orders/{order_id}"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            order_data = data.get("order", {})

            return Order(
                order_id=order_id,
                pair=order_data.get("ticker", ""),
                side=OrderSide.BUY if order_data.get("action") == "buy" else OrderSide.SELL,
                type=OrderType.LIMIT,
                price=order_data.get("yes_price", 0) / 100.0,
                size=order_data.get("count", 0),
                filled_size=order_data.get("count", 0) - order_data.get("queue_position", 0),
                status=self._map_order_status(order_data.get("status", "open"))
            )

        except Exception as e:
            logger.error(f"Error getting Kalshi order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successfully cancelled
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/portfolio/orders/{order_id}"
            response = self.session.delete(url)
            response.raise_for_status()

            logger.info(f"Cancelled Kalshi order: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling Kalshi order {order_id}: {e}")
            return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get available markets.

        Args:
            **kwargs: Optional filters (status, category, etc.)

        Returns:
            List of market dictionaries
        """
        self._ensure_authenticated()

        try:
            url = f"{self.BASE_URL}/markets"

            params = {}
            if "status" in kwargs:
                params["status"] = kwargs["status"]
            if "category" in kwargs:
                params["category"] = kwargs["category"]

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            markets = data.get("markets", [])

            # Convert to common format
            result = []
            for market in markets:
                result.append({
                    "id": market.get("ticker"),
                    "name": market.get("title"),
                    "type": "binary",
                    "end_date": market.get("close_time"),
                    "status": market.get("status"),
                    "category": market.get("category"),
                    "yes_price": market.get("yes_bid", 0) / 100.0,
                    "no_price": market.get("no_bid", 0) / 100.0,
                })

            return result

        except Exception as e:
            logger.error(f"Error getting Kalshi markets: {e}")
            raise

    def _map_order_status(self, kalshi_status: str) -> OrderStatus:
        """Map Kalshi order status to OrderStatus enum."""
        status_map = {
            "resting": OrderStatus.OPEN,
            "pending": OrderStatus.PENDING,
            "canceled": OrderStatus.CANCELLED,
            "executed": OrderStatus.FILLED,
        }
        return status_map.get(kalshi_status.lower(), OrderStatus.OPEN)

    def get_market_by_event(self, event_name: str) -> Optional[Dict[str, Any]]:
        """
        Find markets matching an event name (useful for cross-platform arb).

        Args:
            event_name: Event name to search for

        Returns:
            Market dict or None
        """
        try:
            markets = self.get_markets(status="open")

            # Search for matching market
            event_lower = event_name.lower()
            for market in markets:
                if event_lower in market["name"].lower():
                    return market

            return None

        except Exception as e:
            logger.error(f"Error searching Kalshi markets: {e}")
            return None
