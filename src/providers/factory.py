"""
Provider factory for instantiating exchange providers.

Automatically selects the correct provider based on configuration.
"""

import logging
from typing import Dict, Any

from .base import BaseProvider
from .polymarket import PolymarketProvider
from .luno import LunoProvider
from .kalshi import KalshiProvider
from .binance import BinanceProvider
from .coinbase import CoinbaseProvider
from .bybit import BybitProvider
from .kraken import KrakenProvider
from .dydx import DydxProvider

logger = logging.getLogger(__name__)


def create_provider(provider_name: str, config: Dict[str, Any]) -> BaseProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_name: Provider identifier ("polymarket", "luno", "kalshi", "binance", "coinbase", "bybit", "kraken", "dydx")
        config: Provider-specific configuration

    Returns:
        Initialized provider instance

    Raises:
        ValueError: If provider_name is unknown

    Examples:
        >>> # Create Polymarket provider
        >>> poly_config = {
        ...     "private_key": "0x...",
        ...     "signature_type": 1,
        ...     "funder": "0x..."
        ... }
        >>> provider = create_provider("polymarket", poly_config)

        >>> # Create Luno provider
        >>> luno_config = {
        ...     "api_key_id": "...",
        ...     "api_key_secret": "...",
        ...     "default_pair": "XBTZAR"
        ... }
        >>> provider = create_provider("luno", luno_config)
    """
    provider_name_lower = provider_name.lower().strip()

    if provider_name_lower == "polymarket":
        logger.info("🎯 Creating Polymarket provider")
        return PolymarketProvider(config)

    elif provider_name_lower == "luno":
        logger.info("🚀 Creating Luno provider")
        return LunoProvider(config)

    elif provider_name_lower == "kalshi":
        logger.info("🎲 Creating Kalshi provider")
        return KalshiProvider(config)

    elif provider_name_lower == "binance":
        logger.info("🌐 Creating Binance provider")
        return BinanceProvider(config)

    elif provider_name_lower == "coinbase":
        logger.info("🇺🇸 Creating Coinbase provider")
        return CoinbaseProvider(config)

    elif provider_name_lower == "bybit":
        logger.info("📊 Creating Bybit provider")
        return BybitProvider(config)

    elif provider_name_lower == "kraken":
        logger.info("🐙 Creating Kraken provider")
        return KrakenProvider(config)

    elif provider_name_lower == "dydx":
        logger.info("⚡ Creating dYdX provider")
        return DydxProvider(config)

    else:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Supported providers: polymarket, luno, kalshi, binance, coinbase, bybit, kraken, dydx"
        )


def get_supported_providers() -> Dict[str, str]:
    """
    Get list of supported providers with descriptions.

    Returns:
        Dict mapping provider name to description
    """
    return {
        "polymarket": "Prediction market (BTC UP/DOWN, binary outcomes)",
        "luno": "Cryptocurrency exchange (BTC/ZAR, ETH/ZAR spot trading)",
        "kalshi": "US-regulated prediction market ($23.8B volume 2025)",
        "binance": "World's largest cryptocurrency exchange (global liquidity)",
        "coinbase": "Largest US-based exchange (regulatory compliance)",
        "bybit": "Leading derivatives exchange (perpetuals, high leverage)",
        "kraken": "Trusted exchange with deep liquidity (fiat on-ramps)",
        "dydx": "Decentralized perpetuals exchange ($1.5T+ volume)",
    }
