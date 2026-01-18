"""
Kraken provider for cryptocurrency trading.

Kraken is one of the oldest and most trusted cryptocurrency exchanges.
Perfect for cross-exchange arbitrage with deep liquidity and regulatory compliance.

API Documentation: https://docs.kraken.com/rest/
"""

import logging
import time
import hmac
import hashlib
import base64
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


class KrakenProvider(BaseProvider):
    """
    Kraken cryptocurrency exchange provider.

    One of the oldest and most trusted exchanges with deep liquidity.
    Ideal for cross-exchange arbitrage and fiat on-ramps.
    """

    BASE_URL = "https://api.kraken.com"
    API_VERSION = "0"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Kraken provider.

        Args:
            config: Configuration with:
                - api_key: Kraken API key
                - api_secret: Kraken API private key (base64 encoded)
                - default_pair: Optional default trading pair (e.g., "XXBTZUSD")
        """
        super().__init__(config)

        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.default_pair = config.get("default_pair", "XXBTZUSD")

        if not self.api_key or not self.api_secret:
            raise ValueError("Kraken requires api_key and api_secret")

        self.session = requests.Session()
        self._connected = False

        # Kraken uses base64-encoded API secret
        self.api_secret_decoded = base64.b64decode(self.api_secret)

        logger.info("Kraken provider initialized")

    def connect(self) -> None:
        """Test connection to Kraken API."""
        try:
            # Test connectivity
            url = f"{self.BASE_URL}/{self.API_VERSION}/public/Time"
            response = self.session.get(url)
            response.raise_for_status()

            # Test authentication
            self.get_balance()

            self._connected = True
            logger.info("✅ Connected to Kraken")

        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from Kraken."""
        self.session.close()
        self._connected = False
        logger.info("Disconnected from Kraken")

    def _generate_signature(self, urlpath: str, data: Dict[str, Any], nonce: str) -> str:
        """
        Generate signature for authenticated requests.

        Kraken uses HMAC-SHA512 of (URI path + SHA256(nonce + POST data)).
        """
        postdata = urlencode(data)
        encoded = (nonce + postdata).encode('utf-8')
        message = urlpath.encode('utf-8') + hashlib.sha256(encoded).digest()

        signature = hmac.new(
            self.api_secret_decoded,
            message,
            hashlib.sha512
        )

        return base64.b64encode(signature.digest()).decode('utf-8')

    def _signed_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a signed request to Kraken private API."""
        if params is None:
            params = {}

        # Add nonce
        nonce = str(int(time.time() * 1000))
        params['nonce'] = nonce

        # Build URL path
        urlpath = f"/{self.API_VERSION}/private/{endpoint}"

        # Generate signature
        signature = self._generate_signature(urlpath, params, nonce)

        # Set headers
        headers = {
            "API-Key": self.api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        url = f"{self.BASE_URL}{urlpath}"
        response = self.session.post(url, headers=headers, data=params)
        response.raise_for_status()

        data = response.json()

        # Check for errors
        if data.get("error"):
            raise Exception(f"Kraken API error: {data['error']}")

        return data.get("result", {})

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Optional asset filter (e.g., "XXBT", "ZUSD")

        Returns:
            Dict mapping asset to Balance
        """
        try:
            data = self._signed_request("Balance")

            balances = {}
            for asset_name, balance_str in data.items():
                # Skip if filtering and doesn't match
                if asset and asset_name != asset:
                    continue

                balance = float(balance_str)

                # Only include assets with non-zero balance
                if balance > 0:
                    balances[asset_name] = Balance(
                        asset=asset_name,
                        available=balance,  # Kraken doesn't separate available/locked in this endpoint
                        reserved=0,
                        total=balance
                    )

            return balances

        except Exception as e:
            logger.error(f"Error getting Kraken balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 100) -> Orderbook:
        """
        Get orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "XXBTZUSD")
            depth: Orderbook depth (max 500)

        Returns:
            Orderbook with bids and asks
        """
        try:
            # Kraken public endpoint doesn't require authentication
            url = f"{self.BASE_URL}/{self.API_VERSION}/public/Depth"
            params = {
                "pair": pair,
                "count": min(depth, 500)
            }

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("error"):
                raise Exception(f"Kraken API error: {data['error']}")

            result = data.get("result", {})

            # Kraken returns data keyed by pair name (which may be different from input)
            pair_data = list(result.values())[0] if result else {}

            # Parse bids and asks
            bids = [
                OrderbookEntry(price=float(bid[0]), volume=float(bid[1]))
                for bid in pair_data.get("bids", [])
            ]

            asks = [
                OrderbookEntry(price=float(ask[0]), volume=float(ask[1]))
                for ask in pair_data.get("asks", [])
            ]

            return Orderbook(
                pair=pair,
                bids=bids,
                asks=asks,
                timestamp=int(time.time() * 1000)
            )

        except Exception as e:
            logger.error(f"Error getting Kraken orderbook for {pair}: {e}")
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
        Place an order on Kraken.

        Args:
            pair: Trading pair (e.g., "XXBTZUSD")
            side: BUY or SELL
            order_type: MARKET, LIMIT, FOK, IOC
            size: Order quantity
            price: Limit price (required for limit orders)
            **kwargs: Additional parameters (leverage, oflags, etc.)

        Returns:
            Order object
        """
        try:
            params = {
                "pair": pair,
                "type": "buy" if side == OrderSide.BUY else "sell",
                "volume": str(size)
            }

            # Map order type
            if order_type == OrderType.MARKET:
                params["ordertype"] = "market"
            elif order_type in [OrderType.LIMIT, OrderType.GTC]:
                params["ordertype"] = "limit"
                params["price"] = str(price)
            elif order_type == OrderType.FOK:
                params["ordertype"] = "limit"
                params["price"] = str(price)
                params["oflags"] = "fciq"  # Fill-or-Kill
            elif order_type == OrderType.IOC:
                params["ordertype"] = "limit"
                params["price"] = str(price)
                params["oflags"] = "fcib"  # Immediate-or-Cancel
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            # Add additional parameters
            if "leverage" in kwargs:
                params["leverage"] = kwargs["leverage"]
            if "post_only" in kwargs and kwargs["post_only"]:
                params["oflags"] = "post"

            data = self._signed_request("AddOrder", params)

            # Extract order ID
            order_ids = data.get("txid", [])
            order_id = order_ids[0] if order_ids else ""

            return Order(
                order_id=order_id,
                pair=pair,
                side=side,
                type=order_type,
                price=float(price or 0),
                size=size,
                filled_size=0,
                status=OrderStatus.OPEN
            )

        except Exception as e:
            logger.error(f"Error placing Kraken order: {e}")
            raise

    def get_order(self, order_id: str, pair: Optional[str] = None) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID (txid)
            pair: Trading pair (not required for Kraken)

        Returns:
            Order object with current status
        """
        try:
            params = {
                "txid": order_id
            }

            data = self._signed_request("QueryOrders", params)

            # Kraken returns orders keyed by txid
            order_data = data.get(order_id, {})
            if not order_data:
                raise Exception(f"Order {order_id} not found")

            descr = order_data.get("descr", {})

            return Order(
                order_id=order_id,
                pair=descr.get("pair", pair or self.default_pair),
                side=OrderSide.BUY if descr.get("type") == "buy" else OrderSide.SELL,
                type=self._map_order_type(descr.get("ordertype")),
                price=float(descr.get("price", 0)) or float(order_data.get("price", 0)),
                size=float(order_data.get("vol", 0)),
                filled_size=float(order_data.get("vol_exec", 0)),
                status=self._map_order_status(order_data.get("status"))
            )

        except Exception as e:
            logger.error(f"Error getting Kraken order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str, pair: Optional[str] = None) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID (txid) to cancel
            pair: Trading pair (not required for Kraken)

        Returns:
            True if successfully cancelled
        """
        try:
            params = {
                "txid": order_id
            }

            self._signed_request("CancelOrder", params)

            logger.info(f"Cancelled Kraken order: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling Kraken order {order_id}: {e}")
            return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all trading pairs.

        Returns:
            List of market dictionaries
        """
        try:
            url = f"{self.BASE_URL}/{self.API_VERSION}/public/AssetPairs"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("error"):
                raise Exception(f"Kraken API error: {data['error']}")

            result = []
            for pair_name, pair_data in data.get("result", {}).items():
                result.append({
                    "id": pair_name,
                    "base": pair_data.get("base"),
                    "quote": pair_data.get("quote"),
                    "status": pair_data.get("status"),
                    "ordermin": pair_data.get("ordermin"),
                    "costmin": pair_data.get("costmin"),
                    "lot_decimals": pair_data.get("lot_decimals"),
                    "pair_decimals": pair_data.get("pair_decimals")
                })

            return result

        except Exception as e:
            logger.error(f"Error getting Kraken markets: {e}")
            raise

    def _map_order_status(self, kraken_status: str) -> OrderStatus:
        """Map Kraken order status to OrderStatus enum."""
        status_map = {
            "pending": OrderStatus.PENDING,
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
        }
        return status_map.get(kraken_status, OrderStatus.OPEN)

    def _map_order_type(self, type_str: str) -> OrderType:
        """Map Kraken order type to OrderType enum."""
        type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
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
            url = f"{self.BASE_URL}/{self.API_VERSION}/public/Ticker"
            params = {"pair": pair}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("error"):
                raise Exception(f"Kraken API error: {data['error']}")

            result = data.get("result", {})
            pair_data = list(result.values())[0] if result else {}

            # Get last trade price
            last_trade = pair_data.get("c", [0])
            return float(last_trade[0]) if last_trade else 0.0

        except Exception as e:
            logger.error(f"Error getting Kraken ticker for {pair}: {e}")
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
            url = f"{self.BASE_URL}/{self.API_VERSION}/public/Ticker"
            params = {"pair": pair}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("error"):
                raise Exception(f"Kraken API error: {data['error']}")

            result = data.get("result", {})
            pair_data = list(result.values())[0] if result else {}

            return {
                "last": pair_data.get("c", [0])[0],  # Last trade
                "volume": pair_data.get("v", [0])[1],  # 24h volume
                "high": pair_data.get("h", [0])[1],  # 24h high
                "low": pair_data.get("l", [0])[1],  # 24h low
                "open": pair_data.get("o"),  # Today's opening price
            }

        except Exception as e:
            logger.error(f"Error getting Kraken 24h ticker for {pair}: {e}")
            raise
