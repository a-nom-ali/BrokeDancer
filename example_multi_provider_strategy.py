"""
Example: Multi-Provider Multi-Strategy Trading Bot

Demonstrates how to use the provider and strategy abstraction layers.
"""

import asyncio
import logging

from src.providers import create_provider
from src.strategies import create_strategy, MultiStrategyBot
from src.config import load_settings, get_provider_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_single_strategy():
    """Example: Single strategy with single provider."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Single Strategy (Binary Arbitrage on Polymarket)")
    logger.info("=" * 70)

    # Load configuration
    settings = load_settings()

    # Create Polymarket provider
    provider_config = get_provider_config(settings)
    provider = create_provider("polymarket", provider_config)
    provider.connect()

    # Create binary arbitrage strategy
    strategy_config = {
        "target_pair_cost": settings.target_pair_cost,
        "order_size": settings.order_size,
        "order_type": settings.order_type,
        "scan_interval": 1.0,
        "dry_run": settings.dry_run,
        "yes_token_id": settings.yes_token_id,
        "no_token_id": settings.no_token_id,
    }

    strategy = create_strategy("binary_arbitrage", provider, strategy_config)

    # Run strategy
    try:
        await strategy.start()
    except KeyboardInterrupt:
        logger.info("Strategy stopped by user")
        await strategy.stop()


async def example_multi_strategy():
    """Example: Multiple strategies on same provider."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 2: Multi-Strategy Bot (Multiple strategies on Polymarket)")
    logger.info("=" * 70)

    # Load configuration
    settings = load_settings()

    # Create Polymarket provider
    provider_config = get_provider_config(settings)
    provider = create_provider("polymarket", provider_config)
    provider.connect()

    # Create multiple strategies
    strategies = []

    # Strategy 1: Binary arbitrage on Market A
    arb_config_1 = {
        "target_pair_cost": 0.99,
        "order_size": 50,
        "order_type": "FOK",
        "scan_interval": 1.0,
        "dry_run": True,
        "yes_token_id": settings.yes_token_id,
        "no_token_id": settings.no_token_id,
    }
    arb_strategy_1 = create_strategy("binary_arbitrage", provider, arb_config_1)
    arb_strategy_1.name = "BinaryArb_Market_A"
    strategies.append(arb_strategy_1)

    # Strategy 2: Binary arbitrage on Market B (different tokens, more conservative)
    # arb_config_2 = {
    #     "target_pair_cost": 0.98,  # More conservative
    #     "order_size": 25,
    #     "order_type": "FOK",
    #     "scan_interval": 2.0,
    #     "dry_run": True,
    #     "yes_token_id": "different_yes_token",
    #     "no_token_id": "different_no_token",
    # }
    # arb_strategy_2 = create_strategy("binary_arbitrage", provider, arb_config_2)
    # arb_strategy_2.name = "BinaryArb_Market_B"
    # strategies.append(arb_strategy_2)

    # Create multi-strategy bot
    bot = MultiStrategyBot(strategies)

    # Run bot
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.print_stats()


async def example_cross_provider():
    """Example: Different strategies on different providers."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 3: Cross-Provider Strategies")
    logger.info("=" * 70)

    # Note: This is a conceptual example - Luno requires different strategy
    settings = load_settings()

    # Create Polymarket provider
    poly_config = {
        "private_key": settings.private_key,
        "signature_type": settings.signature_type,
        "funder": settings.funder,
        "yes_token_id": settings.yes_token_id,
        "no_token_id": settings.no_token_id,
    }
    poly_provider = create_provider("polymarket", poly_config)
    poly_provider.connect()

    # Create Luno provider
    luno_config = {
        "api_key_id": settings.luno_api_key_id,
        "api_key_secret": settings.luno_api_key_secret,
        "default_pair": "XBTZAR",
    }
    luno_provider = create_provider("luno", luno_config)
    luno_provider.connect()

    # Strategy on Polymarket: Binary arbitrage
    poly_strategy = create_strategy("binary_arbitrage", poly_provider, {
        "target_pair_cost": 0.99,
        "order_size": 50,
        "yes_token_id": settings.yes_token_id,
        "no_token_id": settings.no_token_id,
        "dry_run": True,
    })

    # Strategy on Luno: Would need a different strategy type
    # (Cross-exchange arbitrage, market making, etc.)
    # luno_strategy = create_strategy("cross_exchange", luno_provider, {...})

    strategies = [poly_strategy]  # Add luno_strategy when implemented

    bot = MultiStrategyBot(strategies)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.print_stats()


if __name__ == "__main__":
    # Run example
    logger.info("\n" + "=" * 70)
    logger.info("MULTI-PROVIDER MULTI-STRATEGY BOT EXAMPLES")
    logger.info("=" * 70 + "\n")

    # Choose which example to run
    asyncio.run(example_single_strategy())

    # Or run multi-strategy example:
    # asyncio.run(example_multi_strategy())

    # Or run cross-provider example:
    # asyncio.run(example_cross_provider())
