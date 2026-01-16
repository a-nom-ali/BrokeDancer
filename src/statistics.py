"""
Statistics and performance tracking module for the arbitrage bot.

Tracks trade history, performance metrics, and provides reporting functionality.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single arbitrage trade execution."""
    timestamp: str
    market_slug: str
    price_up: float
    price_down: float
    total_cost: float
    order_size: float
    total_investment: float
    expected_payout: float
    expected_profit: float
    profit_percentage: float
    order_ids: List[str] = field(default_factory=list)
    filled: bool = False
    market_result: Optional[str] = None
    actual_profit: Optional[float] = None
    # Enhanced tracking fields
    actual_price_up: Optional[float] = None  # Actual fill price for UP side
    actual_price_down: Optional[float] = None  # Actual fill price for DOWN side
    slippage_up: Optional[float] = None  # Slippage on UP side
    slippage_down: Optional[float] = None  # Slippage on DOWN side
    total_slippage: Optional[float] = None  # Total slippage
    fees_paid: Optional[float] = None  # Trading fees if applicable
    execution_time_ms: Optional[float] = None  # Time to execute in milliseconds
    was_unwound: bool = False  # Whether position needed unwinding
    unwind_order_ids: List[str] = field(default_factory=list)  # Unwind order IDs


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    total_trades: int = 0
    successful_trades: int = 0
    total_invested: float = 0.0
    total_expected_profit: float = 0.0
    total_actual_profit: float = 0.0
    total_opportunities_found: int = 0
    win_rate: float = 0.0
    average_profit_per_trade: float = 0.0
    average_profit_percentage: float = 0.0
    total_shares_traded: int = 0
    start_time: Optional[str] = None
    last_trade_time: Optional[str] = None
    # Enhanced analytics
    total_slippage: float = 0.0
    average_slippage: float = 0.0
    total_fees: float = 0.0
    average_execution_time_ms: float = 0.0
    trades_unwound: int = 0
    unwind_rate: float = 0.0
    best_trade_profit: float = 0.0
    worst_trade_profit: float = 0.0
    profit_std_dev: float = 0.0
    sharpe_ratio: float = 0.0  # Risk-adjusted return


class StatisticsTracker:
    """Tracks trade statistics and performance metrics."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize statistics tracker.
        
        Args:
            log_file: Optional path to JSON file for persisting trade history
        """
        self.trades: List[TradeRecord] = []
        self.log_file = log_file
        self.start_time = datetime.now().isoformat()
        
        # Load existing trades if log file exists
        if log_file and Path(log_file).exists():
            try:
                self._load_from_file()
            except Exception as e:
                logger.warning(f"Could not load trade history from {log_file}: {e}")
    
    def record_trade(
        self,
        market_slug: str,
        price_up: float,
        price_down: float,
        total_cost: float,
        order_size: float,
        order_ids: Optional[List[str]] = None,
        filled: bool = True,
    ) -> TradeRecord:
        """
        Record a new trade execution.
        
        Args:
            market_slug: Market identifier
            price_up: UP side price
            price_down: DOWN side price
            total_cost: Total cost per share pair
            order_size: Number of shares per side
            order_ids: List of order IDs (optional)
            filled: Whether the order was successfully filled
            
        Returns:
            TradeRecord instance
        """
        total_investment = total_cost * order_size
        expected_payout = 1.0 * order_size
        expected_profit = expected_payout - total_investment
        profit_percentage = (expected_profit / total_investment * 100) if total_investment > 0 else 0.0
        
        trade = TradeRecord(
            timestamp=datetime.now().isoformat(),
            market_slug=market_slug,
            price_up=price_up,
            price_down=price_down,
            total_cost=total_cost,
            order_size=order_size,
            total_investment=total_investment,
            expected_payout=expected_payout,
            expected_profit=expected_profit,
            profit_percentage=profit_percentage,
            order_ids=order_ids or [],
            filled=filled,
        )
        
        self.trades.append(trade)
        self._save_to_file()
        return trade
    
    def update_trade_result(self, trade: TradeRecord, market_result: str, actual_profit: Optional[float] = None):
        """Update a trade record with market result and actual profit."""
        trade.market_result = market_result
        trade.actual_profit = actual_profit
        self._save_to_file()

    def update_trade_execution(
        self,
        trade: TradeRecord,
        actual_price_up: Optional[float] = None,
        actual_price_down: Optional[float] = None,
        execution_time_ms: Optional[float] = None,
        fees_paid: Optional[float] = None
    ):
        """
        Update trade record with actual execution details.

        Args:
            trade: Trade record to update
            actual_price_up: Actual fill price for UP side
            actual_price_down: Actual fill price for DOWN side
            execution_time_ms: Time taken to execute trade in milliseconds
            fees_paid: Trading fees (if applicable)
        """
        if actual_price_up is not None:
            trade.actual_price_up = actual_price_up
            trade.slippage_up = actual_price_up - trade.price_up

        if actual_price_down is not None:
            trade.actual_price_down = actual_price_down
            trade.slippage_down = actual_price_down - trade.price_down

        # Calculate total slippage
        if trade.slippage_up is not None and trade.slippage_down is not None:
            trade.total_slippage = trade.slippage_up + trade.slippage_down

        if execution_time_ms is not None:
            trade.execution_time_ms = execution_time_ms

        if fees_paid is not None:
            trade.fees_paid = fees_paid

        self._save_to_file()

    def mark_trade_unwound(self, trade: TradeRecord, unwind_order_ids: List[str]):
        """Mark a trade as having been unwound due to partial fill."""
        trade.was_unwound = True
        trade.unwind_order_ids = unwind_order_ids
        self._save_to_file()
    
    def get_stats(self) -> PerformanceStats:
        """Calculate and return aggregated performance statistics with enhanced analytics."""
        if not self.trades:
            return PerformanceStats(start_time=self.start_time)

        filled_trades = [t for t in self.trades if t.filled]
        trades_with_profit = [t for t in filled_trades if t.actual_profit is not None]

        total_invested = sum(t.total_investment for t in filled_trades)
        total_expected_profit = sum(t.expected_profit for t in filled_trades)
        total_actual_profit = sum(t.actual_profit for t in trades_with_profit if t.actual_profit is not None)
        total_shares = sum(int(t.order_size * 2) for t in filled_trades)

        successful_trades = len([t for t in trades_with_profit if t.actual_profit and t.actual_profit > 0])

        avg_profit_per_trade = (total_actual_profit / len(trades_with_profit)) if trades_with_profit else 0.0
        avg_profit_pct = (total_actual_profit / total_invested * 100) if total_invested > 0 else 0.0
        win_rate = (successful_trades / len(trades_with_profit) * 100) if trades_with_profit else 0.0

        # Enhanced analytics
        trades_with_slippage = [t for t in filled_trades if t.total_slippage is not None]
        total_slippage = sum(t.total_slippage for t in trades_with_slippage if t.total_slippage is not None)
        avg_slippage = (total_slippage / len(trades_with_slippage)) if trades_with_slippage else 0.0

        trades_with_fees = [t for t in filled_trades if t.fees_paid is not None]
        total_fees = sum(t.fees_paid for t in trades_with_fees if t.fees_paid is not None)

        trades_with_exec_time = [t for t in filled_trades if t.execution_time_ms is not None]
        avg_exec_time = (sum(t.execution_time_ms for t in trades_with_exec_time if t.execution_time_ms is not None) / len(trades_with_exec_time)) if trades_with_exec_time else 0.0

        trades_unwound = len([t for t in filled_trades if t.was_unwound])
        unwind_rate = (trades_unwound / len(filled_trades) * 100) if filled_trades else 0.0

        # Best/worst trades
        profits = [t.actual_profit for t in trades_with_profit if t.actual_profit is not None]
        best_trade = max(profits) if profits else 0.0
        worst_trade = min(profits) if profits else 0.0

        # Profit standard deviation and Sharpe ratio
        profit_std_dev = 0.0
        sharpe_ratio = 0.0
        if len(profits) > 1:
            import statistics
            profit_std_dev = statistics.stdev(profits)
            # Sharpe ratio: (average return) / (std dev of returns)
            # Simplified version without risk-free rate
            if profit_std_dev > 0:
                sharpe_ratio = avg_profit_per_trade / profit_std_dev

        last_trade = max(self.trades, key=lambda t: t.timestamp) if self.trades else None

        return PerformanceStats(
            total_trades=len(filled_trades),
            successful_trades=successful_trades,
            total_invested=total_invested,
            total_expected_profit=total_expected_profit,
            total_actual_profit=total_actual_profit,
            total_opportunities_found=len(self.trades),
            win_rate=win_rate,
            average_profit_per_trade=avg_profit_per_trade,
            average_profit_percentage=avg_profit_pct,
            total_shares_traded=total_shares,
            start_time=self.start_time,
            last_trade_time=last_trade.timestamp if last_trade else None,
            # Enhanced analytics
            total_slippage=total_slippage,
            average_slippage=avg_slippage,
            total_fees=total_fees,
            average_execution_time_ms=avg_exec_time,
            trades_unwound=trades_unwound,
            unwind_rate=unwind_rate,
            best_trade_profit=best_trade,
            worst_trade_profit=worst_trade,
            profit_std_dev=profit_std_dev,
            sharpe_ratio=sharpe_ratio,
        )
    
    def _save_to_file(self):
        """Save trade history to JSON file."""
        if not self.log_file:
            return
        
        try:
            data = {
                "trades": [asdict(trade) for trade in self.trades],
                "start_time": self.start_time,
            }
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trade history: {e}")
    
    def _load_from_file(self):
        """Load trade history from JSON file."""
        if not self.log_file or not Path(self.log_file).exists():
            return
        
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
            
            self.trades = [TradeRecord(**trade_data) for trade_data in data.get("trades", [])]
            self.start_time = data.get("start_time", self.start_time)
        except Exception as e:
            logger.error(f"Failed to load trade history: {e}")
    
    def export_csv(self, output_file: str):
        """Export trade history to CSV file with enhanced fields."""
        import csv

        if not self.trades:
            logger.warning("No trades to export")
            return

        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp', 'market_slug', 'price_up', 'price_down', 'total_cost',
                    'order_size', 'total_investment', 'expected_payout', 'expected_profit',
                    'profit_percentage', 'filled', 'market_result', 'actual_profit',
                    'actual_price_up', 'actual_price_down', 'slippage_up', 'slippage_down',
                    'total_slippage', 'fees_paid', 'execution_time_ms', 'was_unwound',
                    'order_ids', 'unwind_order_ids'
                ])
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow({
                        'timestamp': trade.timestamp,
                        'market_slug': trade.market_slug,
                        'price_up': trade.price_up,
                        'price_down': trade.price_down,
                        'total_cost': trade.total_cost,
                        'order_size': trade.order_size,
                        'total_investment': trade.total_investment,
                        'expected_payout': trade.expected_payout,
                        'expected_profit': trade.expected_profit,
                        'profit_percentage': trade.profit_percentage,
                        'filled': trade.filled,
                        'market_result': trade.market_result or '',
                        'actual_profit': trade.actual_profit if trade.actual_profit is not None else '',
                        'actual_price_up': trade.actual_price_up if trade.actual_price_up is not None else '',
                        'actual_price_down': trade.actual_price_down if trade.actual_price_down is not None else '',
                        'slippage_up': trade.slippage_up if trade.slippage_up is not None else '',
                        'slippage_down': trade.slippage_down if trade.slippage_down is not None else '',
                        'total_slippage': trade.total_slippage if trade.total_slippage is not None else '',
                        'fees_paid': trade.fees_paid if trade.fees_paid is not None else '',
                        'execution_time_ms': trade.execution_time_ms if trade.execution_time_ms is not None else '',
                        'was_unwound': trade.was_unwound,
                        'order_ids': '|'.join(trade.order_ids) if trade.order_ids else '',
                        'unwind_order_ids': '|'.join(trade.unwind_order_ids) if trade.unwind_order_ids else '',
                    })
            logger.info(f"Enhanced trade history exported to {output_file}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise

