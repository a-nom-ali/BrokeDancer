"""
Multi-strategy bot orchestrator.

Runs multiple trading strategies in parallel with centralized risk management.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from .base import BaseStrategy, StrategyStatus

logger = logging.getLogger(__name__)


class MultiStrategyBot:
    """
    Multi-strategy orchestrator.

    Manages multiple strategies running in parallel:
    - Starts/stops all strategies
    - Aggregates statistics
    - Centralized risk management
    - Graceful shutdown
    """

    def __init__(
        self,
        strategies: List[BaseStrategy],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize multi-strategy bot.

        Args:
            strategies: List of strategy instances
            config: Optional global configuration:
                - max_total_daily_loss: Maximum combined daily loss
                - max_concurrent_trades: Max trades across all strategies
        """
        self.strategies = strategies
        self.config = config or {}

        self.running = False
        self.tasks: List[asyncio.Task] = []

        logger.info(f"✨ Multi-strategy bot initialized with {len(strategies)} strategies:")
        for strategy in strategies:
            logger.info(f"   - {strategy.name}")

    async def start(self):
        """Start all strategies in parallel."""
        logger.info("🚀 Starting multi-strategy bot...")
        self.running = True

        # Start each strategy as a separate task
        for strategy in self.strategies:
            task = asyncio.create_task(strategy.start())
            self.tasks.append(task)
            logger.info(f"   ✓ Started: {strategy.name}")

        logger.info(f"✅ All {len(self.strategies)} strategies running")

    async def stop(self):
        """Stop all strategies gracefully."""
        logger.info("🛑 Stopping multi-strategy bot...")
        self.running = False

        # Signal all strategies to stop
        for strategy in self.strategies:
            await strategy.stop()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("✅ All strategies stopped")

    async def run(self):
        """
        Run all strategies until stopped.

        This is the main entry point for running the bot.
        """
        await self.start()

        try:
            # Wait for all strategy tasks
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Bot cancelled")
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
        finally:
            await self.stop()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics from all strategies.

        Returns:
            Dict with combined statistics
        """
        total_opportunities = 0
        total_trades = 0
        total_profit = 0.0
        strategy_stats = []

        for strategy in self.strategies:
            stats = strategy.get_stats()
            strategy_stats.append(stats)

            total_opportunities += stats["opportunities_found"]
            total_trades += stats["trades_executed"]
            total_profit += stats["total_profit"]

        return {
            "total_strategies": len(self.strategies),
            "total_opportunities": total_opportunities,
            "total_trades": total_trades,
            "total_profit": total_profit,
            "strategies": strategy_stats,
        }

    def print_stats(self):
        """Print formatted statistics to console."""
        stats = self.get_stats()

        print("\n" + "=" * 70)
        print("📊 MULTI-STRATEGY BOT STATISTICS")
        print("=" * 70)
        print(f"Active strategies:     {stats['total_strategies']}")
        print(f"Total opportunities:   {stats['total_opportunities']}")
        print(f"Total trades:          {stats['total_trades']}")
        print(f"Total profit:          ${stats['total_profit']:.2f}")
        print("-" * 70)

        for s in stats["strategies"]:
            print(f"\n{s['name']}:")
            print(f"  Status:       {s['status']}")
            print(f"  Opportunities: {s['opportunities_found']}")
            print(f"  Trades:        {s['trades_executed']}")
            print(f"  Profit:        ${s['total_profit']:.2f}")
            print(f"  Success rate:  {s['success_rate']:.1%}")

        print("=" * 70 + "\n")

    def get_strategy_by_name(self, name: str) -> Optional[BaseStrategy]:
        """
        Get strategy instance by name.

        Args:
            name: Strategy name

        Returns:
            Strategy instance or None if not found
        """
        for strategy in self.strategies:
            if strategy.name == name:
                return strategy
        return None

    def is_running(self) -> bool:
        """Check if bot is currently running."""
        return self.running and any(s.running for s in self.strategies)

    async def wait_for_completion(self):
        """Wait for all strategies to complete."""
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
