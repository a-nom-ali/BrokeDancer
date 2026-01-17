"""
Base provider interface for exchange abstractions.

Defines common interface for all trading providers (Polymarket, Luno, etc.).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side: BUY or SELL."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order execution type."""
    LIMIT = "LIMIT"          # Limit order (price specified)
    MARKET = "MARKET"        # Market order (immediate execution at best price)
    FOK = "FOK"              # Fill-or-Kill (all or nothing)
    IOC = "IOC"              # Immediate-or-Cancel (partial fills OK)
    GTC = "GTC"              # Good-til-Cancelled


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"      # Order submitted, not yet processed
    OPEN = "OPEN"            # Order active in orderbook
    FILLED = "FILLED"        # Order completely filled
    PARTIAL = "PARTIAL"      # Order partially filled
    CANCELLED = "CANCELLED"  # Order cancelled
    REJECTED = "REJECTED"    # Order rejected by exchange


@dataclass
class Balance:
    """Account balance information."""
    asset: str               # Currency/token symbol (e.g., "USDC", "BTC", "ZAR")
    available: float         # Available balance for trading
    reserved: float          # Reserved in open orders
    total: float             # Total balance (available + reserved)


@dataclass
class OrderbookEntry:
    """Single entry in orderbook (bid or ask)."""
    price: float
    volume: float


@dataclass
class Orderbook:
    """Market orderbook with bids and asks."""
    pair: str                # Trading pair (e.g., "BTCUSDC", "XBTZAR")
    bids: List[OrderbookEntry]  # Buy orders (sorted descending by price)
    asks: List[OrderbookEntry]  # Sell orders (sorted ascending by price)
    timestamp: int           # Unix timestamp (milliseconds)

    @property
    def best_bid(self) -> Optional[OrderbookEntry]:
        """Get highest bid (best buy price)."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[OrderbookEntry]:
        """Get lowest ask (best sell price)."""
        return self.asks[0] if self.asks else None

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if not self.best_bid or not self.best_ask:
            return 0.0
        return self.best_ask.price - self.best_bid.price

    @property
    def mid_price(self) -> float:
        """Calculate mid-market price."""
        if not self.best_bid or not self.best_ask:
            return 0.0
        return (self.best_bid.price + self.best_ask.price) / 2.0


@dataclass
class Order:
    """Order information."""
    order_id: str
    pair: str
    side: OrderSide
    type: OrderType
    price: Optional[float]   # None for market orders
    size: float              # Order size
    filled_size: float       # Amount filled so far
    status: OrderStatus
    created_at: int          # Unix timestamp (milliseconds)
    updated_at: int          # Unix timestamp (milliseconds)

    @property
    def is_complete(self) -> bool:
        """Check if order is in terminal state."""
        return self.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.size == 0:
            return 0.0
        return (self.filled_size / self.size) * 100.0


class BaseProvider(ABC):
    """
    Abstract base class for all trading providers.

    Defines common interface that must be implemented by all providers
    (Polymarket, Luno, Binance, etc.).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.

        Args:
            config: Provider-specific configuration dict
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the exchange/platform.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance(s).

        Args:
            asset: Specific asset to query (None = all assets)

        Returns:
            Dict mapping asset symbol to Balance object

        Raises:
            Exception: If balance fetch fails
        """
        pass

    @abstractmethod
    def get_orderbook(self, pair: str, depth: int = 100) -> Orderbook:
        """
        Get current orderbook for a trading pair.

        Args:
            pair: Trading pair symbol (e.g., "BTCUSDC", "XBTZAR")
            depth: Number of levels to retrieve per side

        Returns:
            Orderbook object with bids and asks

        Raises:
            Exception: If orderbook fetch fails
        """
        pass

    @abstractmethod
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
        Place a new order.

        Args:
            pair: Trading pair symbol
            side: BUY or SELL
            order_type: Order execution type (LIMIT, MARKET, FOK, etc.)
            size: Order size (in base currency)
            price: Limit price (required for LIMIT orders, ignored for MARKET)
            **kwargs: Provider-specific parameters

        Returns:
            Order object with order details

        Raises:
            ValueError: If parameters are invalid
            Exception: If order placement fails
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Order:
        """
        Get order status by ID.

        Args:
            order_id: Unique order identifier

        Returns:
            Order object with current status

        Raises:
            Exception: If order fetch fails
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Unique order identifier

        Returns:
            True if cancelled successfully, False otherwise

        Raises:
            Exception: If cancellation fails
        """
        pass

    @abstractmethod
    def get_markets(self) -> List[str]:
        """
        Get list of available trading pairs.

        Returns:
            List of trading pair symbols

        Raises:
            Exception: If market list fetch fails
        """
        pass

    def disconnect(self) -> None:
        """Clean up and disconnect from the exchange."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
