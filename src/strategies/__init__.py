"""
Strategy abstraction layer for multi-strategy trading bots.

Supports various trading strategies:
- Arbitrage (binary, cross-exchange, triangular)
- Market making (spread, grid)
- Copy trading
- Hybrid/combined strategies
"""

from .base import BaseStrategy, Opportunity, TradeResult, StrategyStatus
from .binary_arbitrage import BinaryArbitrageStrategy
from .multi_strategy import MultiStrategyBot
from .factory import create_strategy

__all__ = [
    "BaseStrategy",
    "Opportunity",
    "TradeResult",
    "StrategyStatus",
    "BinaryArbitrageStrategy",
    "MultiStrategyBot",
    "create_strategy",
]
