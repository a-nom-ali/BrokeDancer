"""
dYdX v4 provider for decentralized perpetual trading.

dYdX is the largest DeFi derivatives exchange with fully on-chain orderbook.
Perfect for DeFi arbitrage, funding rate strategies, and decentralized trading.

API Documentation: https://docs.dydx.exchange/api_integration-indexer/indexer_api
"""

import logging
import time
import requests
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


class DydxProvider(BaseProvider):
    """
    dYdX v4 decentralized perpetuals exchange provider.

    Largest DeFi derivatives platform with $1.5T+ all-time volume.
    Ideal for DeFi arbitrage, funding rate strategies, and decentralized trading.
    """

    BASE_URL = "https://indexer.dydx.trade/v4"
    TESTNET_URL = "https://indexer.v4testnet.dydx.exchange/v4"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize dYdX provider.

        Args:
            config: Configuration with:
                - mnemonic: dYdX wallet mnemonic (24 words)
                - address: dYdX address (dydx1...)
                - default_pair: Optional default trading pair (e.g., "BTC-USD")
                - testnet: Use testnet (default: False)
                - network: Network ID (default: "dydx-mainnet-1")
        """
        super().__init__(config)

        self.mnemonic = config.get("mnemonic")
        self.address = config.get("address")
        self.default_pair = config.get("default_pair", "BTC-USD")
        self.testnet = config.get("testnet", False)
        self.network = config.get("network", "dydx-mainnet-1")

        if not self.address:
            raise ValueError("dYdX requires wallet address")

        # Use testnet if enabled
        if self.testnet:
            self.BASE_URL = self.TESTNET_URL
            self.network = "dydx-testnet-4"

        self.session = requests.Session()
        self._connected = False

        logger.info(f"dYdX provider initialized ({'testnet' if self.testnet else 'mainnet'}, address: {self.address[:10]}...)")

    def connect(self) -> None:
        """Test connection to dYdX API."""
        try:
            # Test connectivity by getting server time
            url = f"{self.BASE_URL}/time"
            response = self.session.get(url)
            response.raise_for_status()

            # Test account access
            self.get_balance()

            self._connected = True
            logger.info("✅ Connected to dYdX")

        except Exception as e:
            logger.error(f"Failed to connect to dYdX: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from dYdX."""
        self.session.close()
        self._connected = False
        logger.info("Disconnected from dYdX")

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance.

        Args:
            asset: Optional asset filter (dYdX uses USDC as collateral)

        Returns:
            Dict mapping asset to Balance
        """
        try:
            # Get subaccount balances
            url = f"{self.BASE_URL}/addresses/{self.address}/subaccountNumber/0"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            subaccount = data.get("subaccount", {})

            balances = {}

            # dYdX uses USDC as base collateral
            equity = float(subaccount.get("equity", 0))
            free_collateral = float(subaccount.get("freeCollateral", 0))
            margin_usage = equity - free_collateral if equity > 0 else 0

            if equity > 0:
                balances["USDC"] = Balance(
                    asset="USDC",
                    available=free_collateral,
                    reserved=margin_usage,
                    total=equity
                )

            # Add position values
            for position in subaccount.get("openPerpetualPositions", {}).values():
                market = position.get("market", "")
                size = float(position.get("size", 0))
                entry_price = float(position.get("entryPrice", 0))
                unrealized_pnl = float(position.get("unrealizedPnl", 0))

                if size != 0:
                    # Track position as separate "balance"
                    base_asset = market.split("-")[0]
                    balances[f"{base_asset}_POSITION"] = Balance(
                        asset=base_asset,
                        available=abs(size),
                        reserved=0,
                        total=abs(size)
                    )

            return balances

        except Exception as e:
            logger.error(f"Error getting dYdX balance: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 100) -> Orderbook:
        """
        Get orderbook for a trading pair.

        Args:
            pair: Trading pair (e.g., "BTC-USD")
            depth: Orderbook depth (not used, dYdX returns full book)

        Returns:
            Orderbook with bids and asks
        """
        try:
            url = f"{self.BASE_URL}/orderbooks/perpetualMarket/{pair}"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            # Parse bids and asks
            bids = [
                OrderbookEntry(
                    price=float(bid.get("price", 0)),
                    volume=float(bid.get("size", 0))
                )
                for bid in data.get("bids", [])
            ]

            asks = [
                OrderbookEntry(
                    price=float(ask.get("price", 0)),
                    volume=float(ask.get("size", 0))
                )
                for ask in data.get("asks", [])
            ]

            return Orderbook(
                pair=pair,
                bids=bids[:depth],
                asks=asks[:depth],
                timestamp=int(time.time() * 1000)
            )

        except Exception as e:
            logger.error(f"Error getting dYdX orderbook for {pair}: {e}")
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
        Place an order on dYdX.

        Note: dYdX v4 requires transaction signing which needs the full dYdX Python client.
        This implementation provides the structure but will need proper signing.

        Args:
            pair: Trading pair (e.g., "BTC-USD")
            side: BUY or SELL
            order_type: MARKET, LIMIT, FOK, IOC, GTC
            size: Order quantity
            price: Limit price (required for limit orders)
            **kwargs: Additional parameters

        Returns:
            Order object
        """
        logger.warning("dYdX order placement requires transaction signing - use official dYdX client for production")

        # For now, return a placeholder order
        # In production, this would use the dYdX Python client to sign and submit transactions
        return Order(
            order_id=f"dydx_{int(time.time() * 1000)}",
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=0,
            status=OrderStatus.PENDING
        )

    def get_order(self, order_id: str, pair: Optional[str] = None) -> Order:
        """
        Get order status.

        Args:
            order_id: Order ID
            pair: Trading pair (not required for dYdX)

        Returns:
            Order object with current status
        """
        try:
            # Get orders for address
            url = f"{self.BASE_URL}/orders/{order_id}"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            return Order(
                order_id=data.get("id", order_id),
                pair=data.get("ticker", pair or self.default_pair),
                side=OrderSide.BUY if data.get("side") == "BUY" else OrderSide.SELL,
                type=self._map_order_type(data.get("type"), data.get("timeInForce")),
                price=float(data.get("price", 0)),
                size=float(data.get("size", 0)),
                filled_size=float(data.get("totalFilled", 0)),
                status=self._map_order_status(data.get("status"))
            )

        except Exception as e:
            logger.error(f"Error getting dYdX order {order_id}: {e}")
            raise

    def cancel_order(self, order_id: str, pair: Optional[str] = None) -> bool:
        """
        Cancel an order.

        Note: Requires transaction signing with dYdX client.

        Args:
            order_id: Order ID to cancel
            pair: Trading pair (not required for dYdX)

        Returns:
            True if successfully cancelled
        """
        logger.warning("dYdX order cancellation requires transaction signing - use official dYdX client")
        return False

    def get_markets(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all trading pairs.

        Returns:
            List of market dictionaries
        """
        try:
            url = f"{self.BASE_URL}/perpetualMarkets"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            result = []
            for market_id, market_data in data.get("markets", {}).items():
                if market_data.get("status") == "ACTIVE":
                    result.append({
                        "id": market_id,
                        "ticker": market_data.get("ticker"),
                        "base": market_data.get("baseAsset"),
                        "quote": market_data.get("quoteAsset"),
                        "status": market_data.get("status"),
                        "step_size": market_data.get("stepSize"),
                        "tick_size": market_data.get("tickSize"),
                        "min_order_size": market_data.get("minOrderSize"),
                        "initial_margin_fraction": market_data.get("initialMarginFraction"),
                        "maintenance_margin_fraction": market_data.get("maintenanceMarginFraction")
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting dYdX markets: {e}")
            raise

    def _map_order_status(self, dydx_status: str) -> OrderStatus:
        """Map dYdX order status to OrderStatus enum."""
        status_map = {
            "OPEN": OrderStatus.OPEN,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "BEST_EFFORT_CANCELED": OrderStatus.CANCELLED,
            "PENDING": OrderStatus.PENDING,
            "UNTRIGGERED": OrderStatus.PENDING,
        }
        return status_map.get(dydx_status, OrderStatus.OPEN)

    def _map_order_type(self, type_str: str, time_in_force: str) -> OrderType:
        """Map dYdX order type to OrderType enum."""
        if type_str == "MARKET":
            return OrderType.MARKET
        elif type_str == "LIMIT":
            if time_in_force == "FOK":
                return OrderType.FOK
            elif time_in_force == "IOC":
                return OrderType.IOC
            elif time_in_force == "GTT":
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
            url = f"{self.BASE_URL}/perpetualMarkets/{pair}"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            market = data.get("markets", {}).get(pair, {})

            return float(market.get("oraclePrice", 0))

        except Exception as e:
            logger.error(f"Error getting dYdX ticker for {pair}: {e}")
            raise

    def get_funding_rate(self, pair: str) -> Dict[str, Any]:
        """
        Get current funding rate for perpetual contract.

        Args:
            pair: Trading pair

        Returns:
            Dict with funding rate and next funding time
        """
        try:
            url = f"{self.BASE_URL}/perpetualMarkets/{pair}"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            market = data.get("markets", {}).get(pair, {})

            return {
                "funding_rate": float(market.get("nextFundingRate", 0)),
                "next_funding_time": market.get("nextFundingAt"),
                "open_interest": float(market.get("openInterest", 0)),
                "volume_24h": float(market.get("volume24H", 0))
            }

        except Exception as e:
            logger.error(f"Error getting dYdX funding rate for {pair}: {e}")
            raise

    def get_historical_funding_rates(self, pair: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical funding rates.

        Args:
            pair: Trading pair
            limit: Number of historical rates to fetch

        Returns:
            List of funding rate records
        """
        try:
            url = f"{self.BASE_URL}/historicalFunding/{pair}"
            params = {"limit": limit}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            return [
                {
                    "rate": float(record.get("rate", 0)),
                    "price": float(record.get("price", 0)),
                    "effective_at": record.get("effectiveAt")
                }
                for record in data.get("historicalFunding", [])
            ]

        except Exception as e:
            logger.error(f"Error getting dYdX historical funding rates for {pair}: {e}")
            raise
