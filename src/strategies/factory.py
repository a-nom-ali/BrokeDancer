"""
Strategy factory for instantiating trading strategies.
"""

import logging
from typing import Dict, Any

from .base import BaseStrategy
from .binary_arbitrage import BinaryArbitrageStrategy
from ..providers.base import BaseProvider

logger = logging.getLogger(__name__)


def create_strategy(
    strategy_name: str,
    provider: BaseProvider,
    config: Dict[str, Any]
) -> BaseStrategy:
    """
    Factory function to create a strategy instance.

    Args:
        strategy_name: Strategy identifier ("binary_arbitrage", "copy_trading", etc.)
        provider: Trading provider instance
        config: Strategy-specific configuration

    Returns:
        Initialized strategy instance

    Raises:
        ValueError: If strategy_name is unknown

    Examples:
        >>> from src.providers import create_provider
        >>> provider = create_provider("polymarket", {...})
        >>>
        >>> # Create binary arbitrage strategy
        >>> config = {
        ...     "target_pair_cost": 0.99,
        ...     "order_size": 50,
        ...     "yes_token_id": "...",
        ...     "no_token_id": "..."
        ... }
        >>> strategy = create_strategy("binary_arbitrage", provider, config)
    """
    strategy_name_lower = strategy_name.lower().strip().replace("_", "").replace("-", "")

    if strategy_name_lower == "binaryarbitrage":
        logger.info("🎯 Creating Binary Arbitrage strategy")

        # Extract required parameters
        yes_token_id = config.get("yes_token_id")
        no_token_id = config.get("no_token_id")

        if not yes_token_id or not no_token_id:
            raise ValueError(
                "Binary arbitrage requires 'yes_token_id' and 'no_token_id' in config"
            )

        return BinaryArbitrageStrategy(
            provider=provider,
            config=config,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id
        )

    # Placeholder for future strategies
    elif strategy_name_lower == "copytrading":
        raise NotImplementedError(
            "Copy trading strategy not yet implemented. "
            "Coming soon!"
        )

    elif strategy_name_lower == "crossexchange":
        raise NotImplementedError(
            "Cross-exchange arbitrage strategy not yet implemented. "
            "Coming soon!"
        )

    elif strategy_name_lower == "triangular":
        raise NotImplementedError(
            "Triangular arbitrage strategy not yet implemented. "
            "Coming soon!"
        )

    elif strategy_name_lower == "marketmaking":
        raise NotImplementedError(
            "Market making strategy not yet implemented. "
            "Coming soon!"
        )

    else:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Supported strategies: binary_arbitrage (more coming soon)"
        )


def get_supported_strategies() -> Dict[str, str]:
    """
    Get list of supported strategies with descriptions.

    Returns:
        Dict mapping strategy name to description
    """
    return {
        "binary_arbitrage": "Buy both sides of binary prediction market when total < $1.00",
        "copy_trading": "Mirror another trader's positions (coming soon)",
        "cross_exchange": "Buy low on one exchange, sell high on another (coming soon)",
        "triangular": "Exploit pricing inefficiencies across 3+ pairs (coming soon)",
        "market_making": "Post bid/ask spreads to capture liquidity (coming soon)",
    }
