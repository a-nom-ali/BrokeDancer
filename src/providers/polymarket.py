"""
Polymarket provider implementation.

Wraps the existing Polymarket trading functionality into the provider interface.
Polymarket is a prediction market, not a traditional exchange, so some methods
are adapted to fit the binary outcome structure (UP/DOWN tokens).
"""

import logging
import time
from typing import Dict, List, Optional, Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    BalanceAllowanceParams,
    AssetType,
    OrderArgs,
    OrderType as PolyOrderType,
    PartialCreateOrderOptions,
)
from py_clob_client.order_builder.constants import BUY, SELL

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
from ..utils import mask_credential, retry_with_backoff, safe_float_conversion

logger = logging.getLogger(__name__)


class PolymarketProvider(BaseProvider):
    """
    Polymarket prediction market provider.

    Polymarket is NOT a traditional exchange - it's a binary prediction market
    where users trade on outcomes (e.g., "BTC goes UP" vs "BTC goes DOWN").

    Key differences from traditional exchanges:
    - Trading "pairs" are actually binary outcome tokens (YES/NO, UP/DOWN)
    - Prices represent probability (0.00 to 1.00)
    - Payouts are $1.00 per winning token
    - No traditional orderbook "pairs" like BTC/USD

    For arbitrage:
    - Buy both sides when total cost < $1.00
    - Guaranteed profit regardless of outcome
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Polymarket provider.

        Args:
            config: Configuration dict with:
                - private_key: Ethereum private key
                - signature_type: 0=EOA, 1=Magic.link, 2=Gnosis Safe
                - funder: Proxy wallet address (Magic.link only)
                - market_id: Polymarket market ID (optional)
                - yes_token_id: YES outcome token ID (optional)
                - no_token_id: NO outcome token ID (optional)

        Raises:
            ValueError: If required config is missing
        """
        super().__init__(config)

        self.private_key = config.get("private_key")
        self.signature_type = config.get("signature_type", 1)
        self.funder = config.get("funder", "")
        self.market_id = config.get("market_id", "")
        self.yes_token_id = config.get("yes_token_id", "")
        self.no_token_id = config.get("no_token_id", "")

        if not self.private_key:
            raise ValueError("Polymarket requires 'private_key' in config")

        self.client: Optional[ClobClient] = None
        self._connected = False

    def connect(self) -> None:
        """Establish connection to Polymarket CLOB."""
        if self._connected:
            return

        host = "https://clob.polymarket.com"

        # Create client
        self.client = ClobClient(
            host,
            key=self.private_key.strip(),
            chain_id=137,  # Polygon
            signature_type=self.signature_type,
            funder=self.funder.strip() if self.funder else None
        )

        # Derive API credentials
        self.logger.info("Deriving Polymarket API credentials from private key...")
        derived_creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(derived_creds)

        self._connected = True
        self.logger.info("✅ Connected to Polymarket")
        self.logger.info(f"   API Key: {mask_credential(derived_creds.api_key)}")
        self.logger.info(f"   Wallet: {self.client.get_address()}")
        self.logger.info(f"   Funder: {self.funder if self.funder else 'None'}")

    def disconnect(self) -> None:
        """Disconnect from Polymarket."""
        self.client = None
        self._connected = False
        self.logger.info("Disconnected from Polymarket")

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, exceptions=(Exception,))
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get USDC balance from Polymarket account.

        Args:
            asset: Ignored (Polymarket only supports USDC collateral)

        Returns:
            Dict with "USDC" balance

        Note:
            Polymarket uses USDC as collateral for all markets.
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        params = BalanceAllowanceParams(
            asset_type=AssetType.COLLATERAL,
            signature_type=self.signature_type
        )
        result = self.client.get_balance_allowance(params)

        if isinstance(result, dict):
            balance_raw = result.get("balance", "0")
            balance_wei = safe_float_conversion(balance_raw, 0.0)
            # USDC has 6 decimals
            balance_usdc = balance_wei / 1_000_000

            balances = {
                "USDC": Balance(
                    asset="USDC",
                    available=balance_usdc,
                    reserved=0.0,  # Polymarket API doesn't separate reserved
                    total=balance_usdc
                )
            }

            self.logger.debug(f"Fetched balance: ${balance_usdc:.2f} USDC")
            return balances

        return {}

    def get_orderbook(self, pair: str, depth: int = 100) -> Orderbook:
        """
        Get orderbook for a Polymarket outcome token.

        Args:
            pair: Token ID (e.g., YES token ID or NO token ID)
            depth: Number of levels to retrieve

        Returns:
            Orderbook with bids and asks

        Note:
            For Polymarket, "pair" is actually a token_id, not a traditional pair.
            The orderbook represents bids/asks for that specific outcome token.
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        # Get order book from Polymarket
        book_data = self.client.get_order_book(pair)

        # Parse bids
        bids = []
        for bid in book_data.get("bids", [])[:depth]:
            bids.append(OrderbookEntry(
                price=safe_float_conversion(bid.get("price", "0"), 0.0),
                volume=safe_float_conversion(bid.get("size", "0"), 0.0)
            ))

        # Parse asks
        asks = []
        for ask in book_data.get("asks", [])[:depth]:
            asks.append(OrderbookEntry(
                price=safe_float_conversion(ask.get("price", "0"), 0.0),
                volume=safe_float_conversion(ask.get("size", "0"), 0.0)
            ))

        orderbook = Orderbook(
            pair=pair,
            bids=bids,
            asks=asks,
            timestamp=int(book_data.get("timestamp", time.time() * 1000))
        )

        self.logger.debug(
            f"Orderbook {pair[:8]}: best_bid={orderbook.best_bid.price if orderbook.best_bid else None}, "
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
        Place order on Polymarket.

        Args:
            pair: Token ID to trade
            side: BUY or SELL
            order_type: FOK, GTC, etc.
            size: Number of outcome tokens
            price: Price per token (0.00 to 1.00)
            **kwargs: Optional parameters

        Returns:
            Order object

        Note:
            Polymarket prices are probabilities (0.00 to 1.00).
            Payout is always $1.00 per winning token.
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        if price is None or price <= 0:
            raise ValueError(f"Price required for Polymarket orders: {price}")
        if size <= 0:
            raise ValueError(f"Invalid size: {size}")

        # Map order type
        tif_map = {
            OrderType.FOK: PolyOrderType.FOK,
            OrderType.GTC: PolyOrderType.GTC,
            OrderType.IOC: PolyOrderType.FAK,  # Polymarket uses FAK for IOC
        }
        poly_order_type = tif_map.get(order_type, PolyOrderType.GTC)

        # Create order args
        order_args = OrderArgs(
            token_id=pair,
            price=price,
            size=size,
            side=BUY if side == OrderSide.BUY else SELL
        )

        # BTC 15min markets are neg_risk
        options = PartialCreateOrderOptions(neg_risk=True)
        signed_order = self.client.create_order(order_args, options)

        # Post order
        result = self.client.post_order(signed_order, poly_order_type)

        order_id = result.get("orderID", "")

        order = Order(
            order_id=order_id,
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=0.0,  # Query later for fill status
            status=OrderStatus.PENDING,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000)
        )

        self.logger.info(f"✅ Order placed: {order_id[:8]} ({side.value} {size} @ ${price:.4f})")
        return order

    def get_order(self, order_id: str) -> Order:
        """
        Get order status by ID.

        Args:
            order_id: Polymarket order ID

        Returns:
            Order object with current status
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self.client.get_order(order_id)

        # Parse order details
        order_id = result.get("id", order_id)
        token_id = result.get("asset_id", "")

        # Map side
        side_str = result.get("side", "BUY")
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

        # Map status
        status_str = result.get("status", "PENDING")
        status_map = {
            "LIVE": OrderStatus.OPEN,
            "MATCHED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "PENDING": OrderStatus.PENDING,
        }
        status = status_map.get(status_str, OrderStatus.PENDING)

        price = safe_float_conversion(result.get("price", "0"), 0.0)
        size = safe_float_conversion(result.get("original_size", "0"), 0.0)
        size_matched = safe_float_conversion(result.get("size_matched", "0"), 0.0)

        created_at = int(result.get("created_at", time.time() * 1000))

        order = Order(
            order_id=order_id,
            pair=token_id,
            side=side,
            type=OrderType.GTC,  # Polymarket doesn't return order type
            price=price,
            size=size,
            filled_size=size_matched,
            status=status,
            created_at=created_at,
            updated_at=int(time.time() * 1000)
        )

        return order

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Polymarket order ID

        Returns:
            True if cancelled successfully
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            result = self.client.cancel(order_id)
            success = result.get("success", False)

            if success:
                self.logger.info(f"✅ Order cancelled: {order_id[:8]}")
            else:
                self.logger.warning(f"⚠️ Order cancellation failed: {order_id[:8]}")

            return success

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id[:8]}: {e}")
            return False

    def get_markets(self) -> List[str]:
        """
        Get list of available markets.

        Returns:
            List of market IDs

        Note:
            This is a simplified implementation. Polymarket has many markets
            and would require pagination/filtering for production use.
        """
        # Polymarket doesn't have a simple "list all markets" endpoint
        # This would need to query their API or use the current market
        if self.market_id:
            return [self.market_id]
        return []

    def get_market_tokens(self, market_id: str) -> Dict[str, str]:
        """
        Get YES and NO token IDs for a market.

        Args:
            market_id: Polymarket market ID

        Returns:
            Dict with "yes" and "no" token IDs
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        # Query market details from Polymarket API
        # This would use the Gamma API or simplified markets endpoint
        # For now, return configured tokens if available
        return {
            "yes": self.yes_token_id,
            "no": self.no_token_id
        }
