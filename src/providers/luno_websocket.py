"""
Luno WebSocket streaming client for real-time market data.

Implements the Luno Streaming API protocol:
- Market stream: Real-time orderbook updates
- User stream: Order fills and balance updates

Protocol: https://www.luno.com/en/developers/api#tag/Streaming-API
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Any

import websockets
from websockets.exceptions import WebSocketException

from .base import OrderbookEntry

logger = logging.getLogger(__name__)


@dataclass
class LunoOrderbookState:
    """
    In-memory orderbook state for Luno streaming protocol.

    The client maintains a local copy of the orderbook and applies
    incremental updates from the server.
    """
    pair: str
    sequence: int = 0
    bids: Dict[str, OrderbookEntry] = field(default_factory=dict)  # order_id -> OrderbookEntry
    asks: Dict[str, OrderbookEntry] = field(default_factory=dict)  # order_id -> OrderbookEntry
    status: str = "UNKNOWN"
    timestamp: int = 0

    def apply_create(self, order_id: str, order_type: str, price: float, volume: float):
        """Apply create update: add order to orderbook."""
        entry = OrderbookEntry(price=price, volume=volume)

        if order_type == "BID":
            self.bids[order_id] = entry
        elif order_type == "ASK":
            self.asks[order_id] = entry
        else:
            logger.warning(f"Unknown order type in create update: {order_type}")

    def apply_delete(self, order_id: str):
        """Apply delete update: remove order from orderbook."""
        if order_id in self.bids:
            del self.bids[order_id]
        elif order_id in self.asks:
            del self.asks[order_id]
        else:
            logger.warning(f"Delete update for unknown order_id: {order_id}")

    def apply_trade(self, maker_order_id: str, base_volume: float):
        """Apply trade update: reduce volume of maker order."""
        if maker_order_id in self.bids:
            self.bids[maker_order_id].volume -= base_volume
            if self.bids[maker_order_id].volume <= 0:
                del self.bids[maker_order_id]
        elif maker_order_id in self.asks:
            self.asks[maker_order_id].volume -= base_volume
            if self.asks[maker_order_id].volume <= 0:
                del self.asks[maker_order_id]
        else:
            logger.warning(f"Trade update for unknown maker_order_id: {maker_order_id}")

    def apply_status(self, status: str):
        """Apply status update: set market status."""
        self.status = status

    def get_sorted_bids(self) -> List[OrderbookEntry]:
        """Get bids sorted by price descending."""
        return sorted(self.bids.values(), key=lambda x: x.price, reverse=True)

    def get_sorted_asks(self) -> List[OrderbookEntry]:
        """Get asks sorted by price ascending."""
        return sorted(self.asks.values(), key=lambda x: x.price)

    @property
    def best_bid(self) -> Optional[OrderbookEntry]:
        """Get highest bid."""
        bids = self.get_sorted_bids()
        return bids[0] if bids else None

    @property
    def best_ask(self) -> Optional[OrderbookEntry]:
        """Get lowest ask."""
        asks = self.get_sorted_asks()
        return asks[0] if asks else None

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if not self.best_bid or not self.best_ask:
            return 0.0
        return self.best_ask.price - self.best_bid.price


class LunoMarketStream:
    """
    Luno market stream WebSocket client.

    Maintains real-time orderbook state using Luno's streaming protocol:
    1. Connect to wss://ws.luno.com/api/1/stream/:pair
    2. Authenticate with API credentials
    3. Receive initial orderbook snapshot
    4. Apply incremental updates (create/delete/trade/status)
    5. Handle sequence numbers to ensure correct order
    """

    def __init__(
        self,
        pair: str,
        api_key_id: str,
        api_key_secret: str,
        on_update: Optional[Callable[[LunoOrderbookState], None]] = None
    ):
        """
        Initialize market stream.

        Args:
            pair: Trading pair (e.g., "XBTZAR")
            api_key_id: Luno API key ID
            api_key_secret: Luno API key secret
            on_update: Callback function called after each orderbook update
        """
        self.pair = pair
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.on_update = on_update

        self.url = f"wss://ws.luno.com/api/1/stream/{pair}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.orderbook: Optional[LunoOrderbookState] = None
        self.running = False
        self.last_update_time = 0
        self.keepalive_timeout = 30.0  # seconds

    async def connect(self):
        """Establish WebSocket connection and authenticate."""
        try:
            self.ws = await websockets.connect(self.url)
            logger.info(f"✅ Connected to Luno market stream: {self.pair}")

            # Send authentication credentials
            auth_msg = {
                "api_key_id": self.api_key_id,
                "api_key_secret": self.api_key_secret
            }
            await self.ws.send(json.dumps(auth_msg))
            logger.debug("Sent authentication credentials")

        except Exception as e:
            logger.error(f"Failed to connect to Luno market stream: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info(f"Disconnected from Luno market stream: {self.pair}")

    async def run(self):
        """
        Run the market stream event loop.

        Handles:
        - Initial orderbook snapshot
        - Incremental updates (create/delete/trade/status)
        - Sequence number validation
        - Keep-alive messages
        - Automatic reconnection on errors
        """
        self.running = True
        reconnect_delay = 1.0
        max_reconnect_delay = 60.0

        while self.running:
            try:
                await self.connect()
                reconnect_delay = 1.0  # Reset delay on successful connection

                # Process messages
                async for message in self.ws:
                    self.last_update_time = time.time()

                    if not message:
                        # Empty message = keep-alive
                        logger.debug("Received keep-alive")
                        continue

                    try:
                        data = json.loads(message)
                        await self._process_message(data)

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)

            except WebSocketException as e:
                logger.warning(f"WebSocket error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in market stream: {e}", exc_info=True)

            if self.running:
                logger.info(f"Reconnecting in {reconnect_delay:.1f}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming WebSocket message."""
        # Check if this is the initial snapshot
        if "asks" in data and "bids" in data:
            await self._process_snapshot(data)
        else:
            await self._process_update(data)

    async def _process_snapshot(self, data: Dict[str, Any]):
        """
        Process initial orderbook snapshot.

        Format:
        {
          "sequence": "24352",
          "asks": [{"id": "...", "price": "1234.00", "volume": "0.93"}],
          "bids": [{"id": "...", "price": "1201.00", "volume": "1.22"}],
          "status": "ACTIVE",
          "timestamp": 1528884331021
        }
        """
        sequence = int(data.get("sequence", 0))
        status = data.get("status", "UNKNOWN")
        timestamp = int(data.get("timestamp", time.time() * 1000))

        # Initialize orderbook state
        self.orderbook = LunoOrderbookState(
            pair=self.pair,
            sequence=sequence,
            status=status,
            timestamp=timestamp
        )

        # Load asks
        for ask in data.get("asks", []):
            order_id = ask.get("id")
            price = float(ask.get("price", 0))
            volume = float(ask.get("volume", 0))
            self.orderbook.apply_create(order_id, "ASK", price, volume)

        # Load bids
        for bid in data.get("bids", []):
            order_id = bid.get("id")
            price = float(bid.get("price", 0))
            volume = float(bid.get("volume", 0))
            self.orderbook.apply_create(order_id, "BID", price, volume)

        logger.info(
            f"📊 Orderbook snapshot loaded: {len(self.orderbook.bids)} bids, "
            f"{len(self.orderbook.asks)} asks, sequence={sequence}"
        )

        # Trigger callback
        if self.on_update and self.orderbook:
            self.on_update(self.orderbook)

    async def _process_update(self, data: Dict[str, Any]):
        """
        Process incremental orderbook update.

        Format:
        {
          "sequence": "24353",
          "trade_updates": [...],  // 0 or more trade updates
          "create_update": {...},  // null or 1 create update
          "delete_update": {...},  // null or 1 delete update
          "status_update": {...},  // null or 1 status update
          "timestamp": 1469031991
        }
        """
        if not self.orderbook:
            logger.warning("Received update before snapshot, ignoring")
            return

        sequence = int(data.get("sequence", 0))
        timestamp = int(data.get("timestamp", time.time() * 1000))

        # Validate sequence number
        expected_sequence = self.orderbook.sequence + 1
        if sequence != expected_sequence:
            logger.error(
                f"Out-of-sequence update: expected {expected_sequence}, got {sequence}. "
                f"Reconnecting to reinitialize state..."
            )
            # Out-of-sequence: must reconnect
            await self.disconnect()
            return

        # Apply updates atomically
        self.orderbook.sequence = sequence
        self.orderbook.timestamp = timestamp

        # Apply trade updates
        for trade in data.get("trade_updates") or []:
            maker_order_id = trade.get("maker_order_id")
            base_volume = float(trade.get("base", 0))
            self.orderbook.apply_trade(maker_order_id, base_volume)

        # Apply create update
        create = data.get("create_update")
        if create:
            order_id = create.get("order_id")
            order_type = create.get("type")  # BID or ASK
            price = float(create.get("price", 0))
            volume = float(create.get("volume", 0))
            self.orderbook.apply_create(order_id, order_type, price, volume)

        # Apply delete update
        delete = data.get("delete_update")
        if delete:
            order_id = delete.get("order_id")
            self.orderbook.apply_delete(order_id)

        # Apply status update
        status = data.get("status_update")
        if status:
            new_status = status.get("status")
            self.orderbook.apply_status(new_status)

        # Trigger callback
        if self.on_update:
            self.on_update(self.orderbook)


class LunoUserStream:
    """
    Luno user stream WebSocket client.

    Receives real-time updates for:
    - Order status changes (AWAITING, PENDING, COMPLETE)
    - Order fills (base/counter deltas)
    - Balance updates

    Protocol: wss://ws.luno.com/api/1/userstream
    """

    def __init__(
        self,
        api_key_id: str,
        api_key_secret: str,
        on_order_status: Optional[Callable[[Dict], None]] = None,
        on_order_fill: Optional[Callable[[Dict], None]] = None,
        on_balance_update: Optional[Callable[[Dict], None]] = None
    ):
        """
        Initialize user stream.

        Args:
            api_key_id: Luno API key ID
            api_key_secret: Luno API key secret
            on_order_status: Callback for order status updates
            on_order_fill: Callback for order fill updates
            on_balance_update: Callback for balance updates
        """
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.on_order_status = on_order_status
        self.on_order_fill = on_order_fill
        self.on_balance_update = on_balance_update

        self.url = "wss://ws.luno.com/api/1/userstream"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False

    async def connect(self):
        """Establish WebSocket connection and authenticate."""
        try:
            self.ws = await websockets.connect(self.url)
            logger.info("✅ Connected to Luno user stream")

            # Send authentication credentials
            auth_msg = {
                "api_key_id": self.api_key_id,
                "api_key_secret": self.api_key_secret
            }
            await self.ws.send(json.dumps(auth_msg))
            logger.debug("Sent user stream authentication")

        except Exception as e:
            logger.error(f"Failed to connect to Luno user stream: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("Disconnected from Luno user stream")

    async def run(self):
        """Run the user stream event loop."""
        self.running = True
        reconnect_delay = 1.0
        max_reconnect_delay = 60.0

        while self.running:
            try:
                await self.connect()
                reconnect_delay = 1.0

                async for message in self.ws:
                    if not message:
                        continue

                    try:
                        data = json.loads(message)
                        await self._process_message(data)
                    except Exception as e:
                        logger.error(f"Error processing user stream message: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"User stream error: {e}", exc_info=True)

            if self.running:
                logger.info(f"Reconnecting user stream in {reconnect_delay:.1f}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def _process_message(self, data: Dict[str, Any]):
        """
        Process user stream message.

        Format:
        {
          "type": "order_status" | "order_fill" | "balance_update",
          "timestamp": 1469031991,
          "order_status_update": {...},
          "order_fill_update": {...},
          "balance_update": {...}
        }
        """
        msg_type = data.get("type")

        if msg_type == "order_status" and self.on_order_status:
            update = data.get("order_status_update")
            if update:
                self.on_order_status(update)

        elif msg_type == "order_fill" and self.on_order_fill:
            update = data.get("order_fill_update")
            if update:
                self.on_order_fill(update)

        elif msg_type == "balance_update" and self.on_balance_update:
            update = data.get("balance_update")
            if update:
                self.on_balance_update(update)
