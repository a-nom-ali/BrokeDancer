import os
import logging
from dataclasses import dataclass
from typing import Dict, Set, Optional

from dotenv import load_dotenv, dotenv_values

logger = logging.getLogger(__name__)

# Load .env file values without applying them
dotenv_vars = dotenv_values()

# Load .env file from project root if present.
# Do NOT override existing environment variables (so CI/terminal env wins over .env).
load_dotenv(override=False)

# Track which variables were overridden
_env_overrides: Set[str] = set()

def _check_env_override(var_name: str) -> None:
    """Check if environment variable was overridden and log warning."""
    if var_name in dotenv_vars and var_name in os.environ:
        dotenv_value = dotenv_vars[var_name]
        actual_value = os.environ[var_name]
        if dotenv_value != actual_value:
            _env_overrides.add(var_name)
            # Don't log sensitive values
            if 'KEY' in var_name or 'SECRET' in var_name or 'PASSPHRASE' in var_name:
                logger.warning(f"⚠️ Environment variable '{var_name}' overridden (system env value used)")
            else:
                logger.warning(f"⚠️ Environment variable '{var_name}' overridden: .env={dotenv_value} -> actual={actual_value}")


@dataclass
class Settings:
    api_key: str = os.getenv("POLYMARKET_API_KEY", "")
    api_secret: str = os.getenv("POLYMARKET_API_SECRET", "")
    api_passphrase: str = os.getenv("POLYMARKET_API_PASSPHRASE", "")
    private_key: str = os.getenv("POLYMARKET_PRIVATE_KEY", "")
    signature_type: int = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "1"))
    funder: str = os.getenv("POLYMARKET_FUNDER", "")
    market_slug: str = os.getenv("POLYMARKET_MARKET_SLUG", "")
    market_id: str = os.getenv("POLYMARKET_MARKET_ID", "")
    yes_token_id: str = os.getenv("POLYMARKET_YES_TOKEN_ID", "")
    no_token_id: str = os.getenv("POLYMARKET_NO_TOKEN_ID", "")
    ws_url: str = os.getenv("POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com")
    use_wss: bool = os.getenv("USE_WSS", "false").lower() == "true"

    # Trading profile configuration
    # Set TRADING_PROFILE to one of: learning, testing, scaling, advanced, professional
    # Or set to "auto" to auto-select based on balance
    trading_profile: str = os.getenv("TRADING_PROFILE", "auto")

    # Core trading parameters (can be overridden by profile)
    target_pair_cost: float = float(os.getenv("TARGET_PAIR_COST", "0.99"))
    balance_slack: float = float(os.getenv("BALANCE_SLACK", "0.15"))
    order_size: float = float(os.getenv("ORDER_SIZE", "50"))
    order_type: str = os.getenv("ORDER_TYPE", "FOK").upper()
    yes_buy_threshold: float = float(os.getenv("YES_BUY_THRESHOLD", "0.45"))
    no_buy_threshold: float = float(os.getenv("NO_BUY_THRESHOLD", "0.45"))
    verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    cooldown_seconds: float = float(os.getenv("COOLDOWN_SECONDS", "10"))
    sim_balance: float = float(os.getenv("SIM_BALANCE", "0"))

    # Risk management settings (can be overridden by profile)
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0"))  # 0 = disabled
    max_position_size: float = float(os.getenv("MAX_POSITION_SIZE", "0"))  # 0 = disabled
    max_trades_per_day: int = int(os.getenv("MAX_TRADES_PER_DAY", "0"))  # 0 = disabled
    min_balance_required: float = float(os.getenv("MIN_BALANCE_REQUIRED", "10.0"))
    max_balance_utilization: float = float(os.getenv("MAX_BALANCE_UTILIZATION", "0.8"))

    # Statistics and logging
    enable_stats: bool = os.getenv("ENABLE_STATS", "true").lower() == "true"
    trade_log_file: str = os.getenv("TRADE_LOG_FILE", "trades.json")
    use_rich_output: bool = os.getenv("USE_RICH_OUTPUT", "true").lower() == "true"


def load_settings() -> Settings:
    """Load settings and check for environment variable overrides."""
    # Check for overrides on key variables
    important_vars = [
        "POLYMARKET_PRIVATE_KEY", "POLYMARKET_API_KEY", "POLYMARKET_API_SECRET",
        "POLYMARKET_SIGNATURE_TYPE", "POLYMARKET_FUNDER", "TARGET_PAIR_COST",
        "ORDER_SIZE", "DRY_RUN", "MAX_DAILY_LOSS", "MAX_POSITION_SIZE",
        "TRADING_PROFILE"
    ]

    for var in important_vars:
        _check_env_override(var)

    if _env_overrides:
        logger.info(f"ℹ️ {len(_env_overrides)} environment variable(s) were overridden by system environment")

    return Settings()


def apply_profile_to_settings(
    settings: Settings,
    balance: float,
    force_profile: Optional[str] = None
) -> Settings:
    """
    Apply capital-based profile settings to override default configuration.

    This function modifies settings based on the selected trading profile,
    optimizing parameters for the available capital.

    Args:
        settings: Base settings loaded from environment
        balance: Current account balance in USDC
        force_profile: Optional profile name to force (overrides auto-selection)

    Returns:
        Settings object with profile-applied configuration

    Example:
        >>> settings = load_settings()
        >>> settings = apply_profile_to_settings(settings, balance=750.0)
        # Settings now optimized for $750 capital (Scaling profile)
    """
    from .profiles import (
        auto_select_profile,
        get_profile_by_name,
        validate_capital_for_profile,
        calculate_position_size,
    )

    # Determine which profile to use
    profile_name = force_profile or settings.trading_profile

    if profile_name == "auto":
        # Auto-select based on balance
        profile = auto_select_profile(balance)
        logger.info(f"🤖 Auto-selected trading profile: {profile.name} (balance: ${balance:.2f})")
    else:
        # Use explicitly specified profile
        profile = get_profile_by_name(profile_name)
        if profile is None:
            logger.warning(f"⚠️ Unknown trading profile '{profile_name}', using auto-selection")
            profile = auto_select_profile(balance)
        else:
            logger.info(f"📋 Using trading profile: {profile.name}")

    # Validate capital for this profile
    is_valid, msg = validate_capital_for_profile(balance, profile)
    logger.info(msg)

    # Display profile info
    logger.info(f"   Spread requirement: {profile.spread_requirement:.1f}%")
    logger.info(f"   Max daily trades: {profile.max_trades_per_day}")
    logger.info(f"   Position size: {profile.order_size:.0f} shares")
    logger.info(f"   Max daily loss: {profile.max_daily_loss * 100:.1f}%")

    # Apply profile settings (only if not explicitly set in environment)
    # Priority: ENV var > Profile defaults > Original settings

    # Profit threshold (most important for strategy)
    if os.getenv("TARGET_PAIR_COST") is None:
        settings.target_pair_cost = profile.profit_threshold
        logger.info(f"   ✓ Applied profit threshold: {profile.profit_threshold} ({profile.spread_requirement:.1f}% spread)")

    # Position sizing
    if os.getenv("ORDER_SIZE") is None:
        manual_override = None
    else:
        manual_override = settings.order_size

    calculated_size = calculate_position_size(balance, profile, manual_override)
    settings.order_size = calculated_size

    # Risk management
    if os.getenv("MAX_POSITION_SIZE") is None or settings.max_position_size == 0:
        settings.max_position_size = profile.max_position_size
        logger.info(f"   ✓ Applied max position size: {profile.max_position_size:.0f} shares")

    if os.getenv("MAX_TRADES_PER_DAY") is None or settings.max_trades_per_day == 0:
        settings.max_trades_per_day = profile.max_trades_per_day
        logger.info(f"   ✓ Applied max trades per day: {profile.max_trades_per_day}")

    if os.getenv("MAX_DAILY_LOSS") is None or settings.max_daily_loss == 0:
        settings.max_daily_loss = balance * profile.max_daily_loss
        logger.info(f"   ✓ Applied max daily loss: ${settings.max_daily_loss:.2f} ({profile.max_daily_loss * 100:.1f}%)")

    if os.getenv("MAX_BALANCE_UTILIZATION") is None:
        settings.max_balance_utilization = profile.balance_utilization
        logger.info(f"   ✓ Applied balance utilization: {profile.balance_utilization * 100:.0f}%")

    if os.getenv("COOLDOWN_SECONDS") is None:
        settings.cooldown_seconds = profile.cooldown_seconds
        logger.info(f"   ✓ Applied cooldown: {profile.cooldown_seconds:.0f}s")

    # DRY_RUN recommendation
    if profile.recommended_dry_run and not settings.dry_run:
        logger.warning(f"⚠️ {profile.name} profile recommends DRY_RUN mode for learning. Set DRY_RUN=true in .env")

    return settings


def get_env_overrides() -> Set[str]:
    """Get the set of environment variables that were overridden."""
    return _env_overrides.copy()
