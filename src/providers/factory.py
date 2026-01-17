"""
Provider factory for instantiating exchange providers.

Automatically selects the correct provider based on configuration.
"""

import logging
from typing import Dict, Any

from .base import BaseProvider
from .polymarket import PolymarketProvider
from .luno import LunoProvider

logger = logging.getLogger(__name__)


def create_provider(provider_name: str, config: Dict[str, Any]) -> BaseProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_name: Provider identifier ("polymarket", "luno")
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

    else:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Supported providers: polymarket, luno"
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
    }
