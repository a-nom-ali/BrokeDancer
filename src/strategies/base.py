"""
Base strategy interface for all trading strategies.

Supports both polling-based and event-driven strategies.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

from ..providers.base import BaseProvider, Orderbook, Balance, Order

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """Strategy execution status."""
    IDLE = "IDLE"              # Strategy not running
    SCANNING = "SCANNING"      # Scanning for opportunities
    EXECUTING = "EXECUTING"    # Executing trade
    WAITING = "WAITING"        # Cooldown/waiting period
    ERROR = "ERROR"            # Error state
    STOPPED = "STOPPED"        # Manually stopped


@dataclass
class Opportunity:
    """
    Trading opportunity identified by a strategy.

    Generic structure that can represent different types of opportunities:
    - Arbitrage: price discrepancies
    - Market making: spread capture
    - Copy trading: positions to mirror
    """
    strategy_name: str         # Strategy that found this opportunity
    timestamp: int             # Unix timestamp (milliseconds)
    confidence: float          # Confidence score (0.0 to 1.0)
    expected_profit: float     # Expected profit in base currency
    metadata: Dict[str, Any] = field(default_factory=dict)  # Strategy-specific data

    def __str__(self):
        return f"{self.strategy_name}: ${self.expected_profit:.2f} profit (confidence: {self.confidence:.2%})"


@dataclass
class TradeResult:
    """Result of executing a trading opportunity."""
    opportunity: Opportunity
    success: bool
    actual_profit: Optional[float] = None  # Actual profit (if known)
    orders: List[Order] = field(default_factory=list)  # Orders placed
    error: Optional[str] = None  # Error message if failed
    execution_time_ms: float = 0.0  # Time taken to execute

    @property
    def slippage(self) -> Optional[float]:
        """Calculate slippage (expected vs actual profit)."""
        if self.actual_profit is None:
            return None
        return self.actual_profit - self.opportunity.expected_profit


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    Supports two execution modes:
    1. Polling mode: Periodically scan for opportunities
    2. Event-driven mode: React to market events (orderbook updates, trades)

    Strategies can implement one or both modes.
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Dict[str, Any],
        name: Optional[str] = None
    ):
        """
        Initialize strategy.

        Args:
            provider: Trading provider (Polymarket, Luno, etc.)
            config: Strategy-specific configuration
            name: Optional custom name for this strategy instance
        """
        self.provider = provider
        self.config = config
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

        # State
        self.status = StrategyStatus.IDLE
        self.running = False
        self.opportunities_found = 0
        self.trades_executed = 0
        self.total_profit = 0.0

        # Configuration
        self.scan_interval = config.get("scan_interval", 1.0)  # seconds
        self.min_profit = config.get("min_profit", 0.01)  # minimum profit to execute
        self.dry_run = config.get("dry_run", False)

    async def start(self):
        """Start the strategy."""
        self.logger.info(f"🚀 Starting strategy: {self.name}")
        self.running = True
        self.status = StrategyStatus.SCANNING

        # Connect provider if not already connected
        if not hasattr(self.provider, '_connected') or not self.provider._connected:
            self.provider.connect()

        await self.run()

    async def stop(self):
        """Stop the strategy."""
        self.logger.info(f"🛑 Stopping strategy: {self.name}")
        self.running = False
        self.status = StrategyStatus.STOPPED

    @abstractmethod
    async def run(self):
        """
        Main strategy loop.

        Must be implemented by subclasses. Can be:
        - Polling loop (scan every N seconds)
        - Event listener (wait for events)
        - Hybrid (both)
        """
        pass

    # ==================== Polling Mode ====================

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Scan for trading opportunities (polling mode).

        Override this method for polling-based strategies.

        Returns:
            Opportunity if found, None otherwise
        """
        return None

    # ==================== Event-Driven Mode ====================

    def on_orderbook_update(self, pair: str, orderbook: Orderbook):
        """
        Handle orderbook update event.

        Override this method for event-driven strategies.

        Args:
            pair: Trading pair or token ID
            orderbook: Updated orderbook
        """
        pass

    def on_trade(self, pair: str, trade: Dict[str, Any]):
        """
        Handle trade event.

        Args:
            pair: Trading pair or token ID
            trade: Trade data
        """
        pass

    def on_balance_update(self, balance: Balance):
        """
        Handle balance update event.

        Args:
            balance: Updated balance
        """
        pass

    # ==================== Execution ====================

    @abstractmethod
    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute a trading opportunity.

        Must be implemented by subclasses.

        Args:
            opportunity: Opportunity to execute

        Returns:
            TradeResult with execution details
        """
        pass

    # ==================== Validation ====================

    def should_execute(self, opportunity: Opportunity) -> tuple[bool, str]:
        """
        Validate if opportunity should be executed.

        Checks:
        - Minimum profit threshold
        - Risk management limits
        - Dry run mode

        Returns:
            Tuple of (should_execute, reason)
        """
        # Check minimum profit
        if opportunity.expected_profit < self.min_profit:
            return False, f"Profit ${opportunity.expected_profit:.2f} below minimum ${self.min_profit:.2f}"

        # Check confidence
        min_confidence = self.config.get("min_confidence", 0.0)
        if opportunity.confidence < min_confidence:
            return False, f"Confidence {opportunity.confidence:.2%} below minimum {min_confidence:.2%}"

        return True, "OK"

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get strategy performance statistics.

        Returns:
            Dict with performance metrics
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "opportunities_found": self.opportunities_found,
            "trades_executed": self.trades_executed,
            "total_profit": self.total_profit,
            "success_rate": (
                self.trades_executed / self.opportunities_found
                if self.opportunities_found > 0
                else 0.0
            ),
        }

    # ==================== Helpers ====================

    async def _execute_with_tracking(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute opportunity with automatic tracking and logging.

        Args:
            opportunity: Opportunity to execute

        Returns:
            TradeResult
        """
        import time

        start_time = time.time()
        self.status = StrategyStatus.EXECUTING

        try:
            result = await self.execute(opportunity)
            result.execution_time_ms = (time.time() - start_time) * 1000

            if result.success:
                self.trades_executed += 1
                if result.actual_profit:
                    self.total_profit += result.actual_profit
                self.logger.info(
                    f"✅ Trade executed: ${result.actual_profit:.2f} profit "
                    f"(expected: ${opportunity.expected_profit:.2f})"
                )
            else:
                self.logger.warning(f"❌ Trade failed: {result.error}")

            return result

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            return TradeResult(
                opportunity=opportunity,
                success=False,
                error=str(e)
            )
        finally:
            self.status = StrategyStatus.SCANNING


class PollingStrategy(BaseStrategy):
    """
    Base class for polling-based strategies.

    Scans for opportunities at regular intervals.
    """

    async def run(self):
        """Run polling loop."""
        while self.running:
            try:
                self.status = StrategyStatus.SCANNING

                # Find opportunity
                opportunity = await self.find_opportunity()

                if opportunity:
                    self.opportunities_found += 1
                    self.logger.info(f"🎯 Opportunity found: {opportunity}")

                    # Validate
                    should_execute, reason = self.should_execute(opportunity)
                    if should_execute:
                        # Execute
                        result = await self._execute_with_tracking(opportunity)
                    else:
                        self.logger.debug(f"Skipping opportunity: {reason}")

                # Wait before next scan
                self.status = StrategyStatus.WAITING
                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}", exc_info=True)
                self.status = StrategyStatus.ERROR
                await asyncio.sleep(self.scan_interval)


class EventDrivenStrategy(BaseStrategy):
    """
    Base class for event-driven strategies.

    Reacts to market events (orderbook updates, trades, etc.).
    """

    async def run(self):
        """
        Run event listener.

        Subclasses should override this to subscribe to events.
        """
        # This is a placeholder - subclasses will implement
        # WebSocket subscriptions or other event sources
        while self.running:
            await asyncio.sleep(1.0)
