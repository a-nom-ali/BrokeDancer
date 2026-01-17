"""
Binary arbitrage strategy for Polymarket prediction markets.

Strategy: Buy both YES and NO tokens when total cost < $1.00
Result: Guaranteed profit regardless of outcome ($1.00 payout - cost)

Based on Jeremy Whittaker's strategy for BTC 15-minute markets.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

from .base import PollingStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider, OrderSide, OrderType, Orderbook

logger = logging.getLogger(__name__)


class BinaryArbitrageStrategy(PollingStrategy):
    """
    Binary arbitrage strategy for prediction markets.

    Scans YES and NO token orderbooks for opportunities where:
    - best_ask_yes + best_ask_no < $1.00

    When found, buys both sides to guarantee profit.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Dict[str, Any],
        yes_token_id: str,
        no_token_id: str,
        name: Optional[str] = None
    ):
        """
        Initialize binary arbitrage strategy.

        Args:
            provider: Trading provider (typically Polymarket)
            config: Strategy configuration with:
                - target_pair_cost: Maximum total cost (e.g., 0.99 for 1% profit)
                - order_size: Number of tokens to buy per side
                - order_type: FOK, GTC, etc.
                - scan_interval: Seconds between scans (default: 1.0)
                - dry_run: Simulation mode (default: False)
            yes_token_id: YES outcome token ID
            no_token_id: NO outcome token ID
            name: Optional custom name
        """
        super().__init__(provider, config, name or "BinaryArbitrage")

        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id

        # Strategy-specific config
        self.target_pair_cost = config.get("target_pair_cost", 0.99)
        self.order_size = config.get("order_size", 50.0)
        self.order_type_str = config.get("order_type", "FOK")

        # Map string to OrderType enum
        order_type_map = {
            "FOK": OrderType.FOK,
            "GTC": OrderType.GTC,
            "IOC": OrderType.IOC,
        }
        self.order_type = order_type_map.get(self.order_type_str.upper(), OrderType.FOK)

        self.logger.info(f"Binary arbitrage configured:")
        self.logger.info(f"  Target pair cost: ${self.target_pair_cost}")
        self.logger.info(f"  Order size: {self.order_size} shares")
        self.logger.info(f"  Order type: {self.order_type_str}")

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan YES and NO orderbooks for arbitrage opportunities.

        Returns:
            Opportunity if found, None otherwise
        """
        try:
            # Fetch both orderbooks
            yes_book = self.provider.get_orderbook(self.yes_token_id, depth=10)
            no_book = self.provider.get_orderbook(self.no_token_id, depth=10)

            # Validate orderbooks
            if not yes_book.best_ask or not no_book.best_ask:
                self.logger.debug("No asks available in orderbook")
                return None

            # Check for inverted orderbook (sanity check)
            if yes_book.best_bid and yes_book.best_ask:
                if yes_book.best_ask.price < yes_book.best_bid.price:
                    self.logger.warning("YES orderbook inverted (ask < bid)")
                    return None

            if no_book.best_bid and no_book.best_ask:
                if no_book.best_ask.price < no_book.best_bid.price:
                    self.logger.warning("NO orderbook inverted (ask < bid)")
                    return None

            # Get best ask prices
            price_yes = yes_book.best_ask.price
            price_no = no_book.best_ask.price
            total_cost = price_yes + price_no

            # Check if arbitrage opportunity exists
            if total_cost >= self.target_pair_cost:
                return None  # No opportunity

            # Calculate profit
            profit_per_share = 1.0 - total_cost
            expected_profit = profit_per_share * self.order_size
            profit_pct = (profit_per_share / total_cost) * 100

            # Check minimum liquidity
            min_size = min(yes_book.best_ask.volume, no_book.best_ask.volume)
            if min_size < self.order_size:
                self.logger.debug(
                    f"Insufficient liquidity: need {self.order_size}, available {min_size}"
                )
                return None

            # Create opportunity
            opportunity = Opportunity(
                strategy_name=self.name,
                timestamp=int(time.time() * 1000),
                confidence=1.0,  # Arbitrage is guaranteed (if fills execute)
                expected_profit=expected_profit,
                metadata={
                    "price_yes": price_yes,
                    "price_no": price_no,
                    "total_cost": total_cost,
                    "profit_per_share": profit_per_share,
                    "profit_pct": profit_pct,
                    "order_size": self.order_size,
                    "yes_token_id": self.yes_token_id,
                    "no_token_id": self.no_token_id,
                    "expected_payout": self.order_size * 1.0,  # $1.00 per share
                    "total_investment": total_cost * self.order_size,
                }
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error finding opportunity: {e}", exc_info=True)
            return None

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute binary arbitrage by buying both YES and NO tokens.

        Args:
            opportunity: Arbitrage opportunity

        Returns:
            TradeResult with execution details
        """
        metadata = opportunity.metadata

        # Extract prices and tokens
        price_yes = metadata["price_yes"]
        price_no = metadata["price_no"]
        yes_token_id = metadata["yes_token_id"]
        no_token_id = metadata["no_token_id"]
        order_size = metadata["order_size"]

        self.logger.info("=" * 70)
        self.logger.info("🎯 EXECUTING BINARY ARBITRAGE")
        self.logger.info("=" * 70)
        self.logger.info(f"YES price:       ${price_yes:.4f}")
        self.logger.info(f"NO price:        ${price_no:.4f}")
        self.logger.info(f"Total cost:      ${metadata['total_cost']:.4f}")
        self.logger.info(f"Order size:      {order_size} shares")
        self.logger.info(f"Expected profit: ${opportunity.expected_profit:.2f}")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("🔸 DRY RUN MODE - No real orders placed")
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,  # Assume perfect execution
                orders=[],
            )

        orders = []

        try:
            # Place YES order
            self.logger.info(f"📤 Placing YES order: BUY {order_size} @ ${price_yes:.4f}")
            yes_order = self.provider.place_order(
                pair=yes_token_id,
                side=OrderSide.BUY,
                order_type=self.order_type,
                size=order_size,
                price=price_yes,
            )
            orders.append(yes_order)
            self.logger.info(f"✅ YES order placed: {yes_order.order_id}")

            # Place NO order
            self.logger.info(f"📤 Placing NO order: BUY {order_size} @ ${price_no:.4f}")
            no_order = self.provider.place_order(
                pair=no_token_id,
                side=OrderSide.BUY,
                order_type=self.order_type,
                size=order_size,
                price=price_no,
            )
            orders.append(no_order)
            self.logger.info(f"✅ NO order placed: {no_order.order_id}")

            # For FOK orders, check if both filled
            if self.order_type == OrderType.FOK:
                # Query order status
                await asyncio.sleep(1.0)  # Brief delay for order processing

                yes_status = self.provider.get_order(yes_order.order_id)
                no_status = self.provider.get_order(no_order.order_id)

                if yes_status.is_complete and no_status.is_complete:
                    self.logger.info("✅ Both orders filled successfully")
                    return TradeResult(
                        opportunity=opportunity,
                        success=True,
                        actual_profit=opportunity.expected_profit,
                        orders=orders,
                    )
                else:
                    self.logger.warning("⚠️ One or more orders not filled")
                    return TradeResult(
                        opportunity=opportunity,
                        success=False,
                        orders=orders,
                        error="Partial fill or order not executed"
                    )

            # For GTC/IOC, assume success (would need to track fills)
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,
                orders=orders,
            )

        except Exception as e:
            self.logger.error(f"Error executing arbitrage: {e}", exc_info=True)

            # Attempt to cancel any placed orders
            for order in orders:
                try:
                    self.provider.cancel_order(order.order_id)
                    self.logger.info(f"Cancelled order: {order.order_id}")
                except Exception as cancel_err:
                    self.logger.error(f"Failed to cancel order {order.order_id}: {cancel_err}")

            return TradeResult(
                opportunity=opportunity,
                success=False,
                orders=orders,
                error=str(e)
            )
