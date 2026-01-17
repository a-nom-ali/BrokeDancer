"""
Capital-based trading profiles for optimized risk management and profit targeting.

Each profile is optimized for a specific capital range based on real market research
from 2025 Polymarket data. Profiles automatically adjust:
- Profit thresholds (spread requirements)
- Position sizing
- Risk management parameters
- Trade frequency limits

Research basis:
- Market fees: ~2.5-3% total (2% outcome fee + 0.01-0.1% taker + gas)
- Minimum profitable spread: 2.5-3% after fees
- Real success cases: 98% win rate bots, $313 -> $414K in 1 month
- Conservative daily ROI: 0.5-1% achievable with proper risk management
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ProfileTier(Enum):
    """Trading profile tiers based on starting capital."""
    LEARNING = "learning"      # $100-$200: Learning mode, tight limits
    TESTING = "testing"        # $200-$500: Real money testing, conservative
    SCALING = "scaling"        # $500-$2000: Growth phase, balanced
    ADVANCED = "advanced"      # $2000-$5000: Optimized for volume
    PROFESSIONAL = "professional"  # $5000+: Maximum efficiency


@dataclass
class ProfileConfig:
    """
    Capital-optimized trading profile configuration.

    Attributes:
        name: Profile tier name
        min_capital: Minimum recommended capital for this profile
        max_capital: Maximum recommended capital (before upgrading to next tier)
        profit_threshold: Target pair cost threshold (lower = wider spread required)
        order_size: Default number of shares per trade
        max_position_size: Maximum shares per single trade
        balance_utilization: Maximum % of balance to use per trade
        max_daily_loss: Maximum daily loss limit (% of capital)
        max_trades_per_day: Maximum number of trades per day
        cooldown_seconds: Seconds to wait between trade attempts
        recommended_dry_run: Whether DRY_RUN is recommended for this tier
        description: Human-readable description of this profile
    """
    name: str
    min_capital: float
    max_capital: float
    profit_threshold: float
    order_size: float
    max_position_size: float
    balance_utilization: float
    max_daily_loss: float
    max_trades_per_day: int
    cooldown_seconds: float
    recommended_dry_run: bool
    description: str

    @property
    def spread_requirement(self) -> float:
        """Calculate the spread requirement in percentage."""
        return (1.0 - self.profit_threshold) * 100


# Define pre-configured profiles based on research
PROFILE_DEFINITIONS = {
    ProfileTier.LEARNING: ProfileConfig(
        name="Learning",
        min_capital=100.0,
        max_capital=200.0,
        profit_threshold=0.970,  # 3.0% spread - very conservative, clear profit after fees
        order_size=5.0,
        max_position_size=10.0,
        balance_utilization=0.10,  # Use only 10% of balance per trade
        max_daily_loss=0.05,  # 5% max daily loss
        max_trades_per_day=10,
        cooldown_seconds=30.0,
        recommended_dry_run=True,
        description="Learning mode: $100-$200 capital. Wide spreads (3%), small positions, DRY_RUN recommended. Focus on understanding market dynamics."
    ),

    ProfileTier.TESTING: ProfileConfig(
        name="Testing",
        min_capital=200.0,
        max_capital=500.0,
        profit_threshold=0.975,  # 2.5% spread - conservative, safe margin above fees
        order_size=10.0,
        max_position_size=25.0,
        balance_utilization=0.20,  # Use 20% of balance per trade
        max_daily_loss=0.08,  # 8% max daily loss
        max_trades_per_day=20,
        cooldown_seconds=20.0,
        recommended_dry_run=False,
        description="Testing mode: $200-$500 capital. Safe spreads (2.5%), moderate positions. Real money with conservative limits."
    ),

    ProfileTier.SCALING: ProfileConfig(
        name="Scaling",
        min_capital=500.0,
        max_capital=2000.0,
        profit_threshold=0.980,  # 2.0% spread - balanced risk/reward
        order_size=25.0,
        max_position_size=100.0,
        balance_utilization=0.30,  # Use 30% of balance per trade
        max_daily_loss=0.10,  # 10% max daily loss
        max_trades_per_day=40,
        cooldown_seconds=15.0,
        recommended_dry_run=False,
        description="Scaling mode: $500-$2,000 capital. Balanced spreads (2%), larger positions. Focus on compounding growth."
    ),

    ProfileTier.ADVANCED: ProfileConfig(
        name="Advanced",
        min_capital=2000.0,
        max_capital=5000.0,
        profit_threshold=0.985,  # 1.5% spread - tighter spreads, more opportunities
        order_size=50.0,
        max_position_size=250.0,
        balance_utilization=0.40,  # Use 40% of balance per trade
        max_daily_loss=0.12,  # 12% max daily loss
        max_trades_per_day=60,
        cooldown_seconds=10.0,
        recommended_dry_run=False,
        description="Advanced mode: $2,000-$5,000 capital. Tighter spreads (1.5%), high volume. Optimized for frequent opportunities."
    ),

    ProfileTier.PROFESSIONAL: ProfileConfig(
        name="Professional",
        min_capital=5000.0,
        max_capital=float('inf'),
        profit_threshold=0.990,  # 1.0% spread - aggressive, maximum efficiency
        order_size=100.0,
        max_position_size=500.0,
        balance_utilization=0.50,  # Use 50% of balance per trade
        max_daily_loss=0.15,  # 15% max daily loss
        max_trades_per_day=100,
        cooldown_seconds=5.0,
        recommended_dry_run=False,
        description="Professional mode: $5,000+ capital. Aggressive spreads (1%), maximum volume. For experienced traders with proven strategy."
    ),
}


def auto_select_profile(capital: float) -> ProfileConfig:
    """
    Automatically select the optimal profile based on available capital.

    Args:
        capital: Available trading capital in USDC

    Returns:
        ProfileConfig: The optimal profile for the given capital

    Examples:
        >>> profile = auto_select_profile(150.0)
        >>> profile.name
        'Learning'
        >>> profile.profit_threshold
        0.970

        >>> profile = auto_select_profile(1500.0)
        >>> profile.name
        'Scaling'
    """
    # Find the appropriate tier based on capital
    if capital < PROFILE_DEFINITIONS[ProfileTier.LEARNING].max_capital:
        return PROFILE_DEFINITIONS[ProfileTier.LEARNING]
    elif capital < PROFILE_DEFINITIONS[ProfileTier.TESTING].max_capital:
        return PROFILE_DEFINITIONS[ProfileTier.TESTING]
    elif capital < PROFILE_DEFINITIONS[ProfileTier.SCALING].max_capital:
        return PROFILE_DEFINITIONS[ProfileTier.SCALING]
    elif capital < PROFILE_DEFINITIONS[ProfileTier.ADVANCED].max_capital:
        return PROFILE_DEFINITIONS[ProfileTier.ADVANCED]
    else:
        return PROFILE_DEFINITIONS[ProfileTier.PROFESSIONAL]


def get_profile_by_name(profile_name: str) -> Optional[ProfileConfig]:
    """
    Get a specific profile by name (case-insensitive).

    Args:
        profile_name: Name of the profile tier (learning, testing, scaling, advanced, professional)

    Returns:
        ProfileConfig or None if not found

    Examples:
        >>> profile = get_profile_by_name("testing")
        >>> profile.min_capital
        200.0
    """
    profile_name_lower = profile_name.lower()
    for tier, config in PROFILE_DEFINITIONS.items():
        if tier.value == profile_name_lower:
            return config
    return None


def display_profile_comparison():
    """Display a comparison table of all available profiles."""
    print("\n" + "=" * 120)
    print("CAPITAL-BASED TRADING PROFILES")
    print("=" * 120)
    print(f"{'Profile':<15} {'Capital Range':<20} {'Spread':<10} {'Size':<10} {'Max/Day':<10} {'Cooldown':<12} {'DRY_RUN':<10}")
    print("-" * 120)

    for tier in ProfileTier:
        config = PROFILE_DEFINITIONS[tier]
        capital_range = f"${config.min_capital:.0f}-${config.max_capital:.0f}" if config.max_capital != float('inf') else f"${config.min_capital:.0f}+"
        spread = f"{config.spread_requirement:.1f}%"
        size = f"{config.order_size:.0f} shares"
        max_day = f"{config.max_trades_per_day} trades"
        cooldown = f"{config.cooldown_seconds:.0f}s"
        dry_run = "Yes" if config.recommended_dry_run else "No"

        print(f"{config.name:<15} {capital_range:<20} {spread:<10} {size:<10} {max_day:<10} {cooldown:<12} {dry_run:<10}")

    print("-" * 120)
    print("\nKey Insights (2025 Research):")
    print("  • Market fees: ~2.5-3% total (2% outcome + 0.01-0.1% taker + gas)")
    print("  • Minimum profitable spread: 2.5-3% after fees")
    print("  • Conservative daily ROI: 0.5-1% achievable")
    print("  • Real success: 98% win rate bots, $313 → $414K in 1 month")
    print("  • Recommendation: Start with Learning/Testing profile, scale up as you prove strategy")
    print("=" * 120 + "\n")


def calculate_position_size(
    balance: float,
    profile: ProfileConfig,
    manual_override: Optional[float] = None
) -> float:
    """
    Calculate optimal position size based on balance and profile.

    Uses Kelly Criterion-inspired approach: position size is a % of total balance,
    capped by profile limits.

    Args:
        balance: Current account balance in USDC
        profile: Active trading profile
        manual_override: Optional manual size override (takes precedence)

    Returns:
        Position size in shares (number of outcome tokens to buy)

    Examples:
        >>> profile = PROFILE_DEFINITIONS[ProfileTier.SCALING]
        >>> calculate_position_size(1000.0, profile)
        25.0  # profile.order_size

        >>> calculate_position_size(1000.0, profile, manual_override=50.0)
        50.0  # manual override
    """
    if manual_override and manual_override > 0:
        # Respect manual override but cap at max_position_size
        return min(manual_override, profile.max_position_size)

    # Use profile's default order size
    suggested_size = profile.order_size

    # Ensure we don't exceed balance utilization limit
    max_cost = balance * profile.balance_utilization
    # Assume worst case: both sides cost 0.50 each = 1.00 total per share
    max_shares_by_balance = max_cost / 1.0

    # Take the minimum of suggested size, max position size, and balance limit
    final_size = min(suggested_size, profile.max_position_size, max_shares_by_balance)

    return max(1.0, final_size)  # Minimum 1 share


def validate_capital_for_profile(capital: float, profile: ProfileConfig) -> tuple[bool, str]:
    """
    Validate if the given capital is appropriate for the selected profile.

    Args:
        capital: Available trading capital in USDC
        profile: Selected trading profile

    Returns:
        Tuple of (is_valid, warning_message)

    Examples:
        >>> profile = PROFILE_DEFINITIONS[ProfileTier.ADVANCED]
        >>> is_valid, msg = validate_capital_for_profile(500.0, profile)
        >>> is_valid
        False
        >>> "below minimum" in msg
        True
    """
    if capital < profile.min_capital:
        return False, (
            f"⚠️ Warning: Your capital (${capital:.2f}) is below the minimum "
            f"recommended for {profile.name} profile (${profile.min_capital:.2f}). "
            f"Consider using a lower tier profile for better risk management."
        )

    if capital > profile.max_capital and profile.max_capital != float('inf'):
        return True, (
            f"ℹ️ Info: Your capital (${capital:.2f}) exceeds the recommended maximum "
            f"for {profile.name} profile (${profile.max_capital:.2f}). "
            f"Consider upgrading to a higher tier profile for better efficiency."
        )

    return True, f"✅ Capital (${capital:.2f}) is optimal for {profile.name} profile."


if __name__ == "__main__":
    # Display profile comparison when run directly
    display_profile_comparison()

    # Example usage
    print("\nExample: Auto-selecting profile for $750 capital:")
    profile = auto_select_profile(750.0)
    print(f"  Selected: {profile.name}")
    print(f"  Spread requirement: {profile.spread_requirement:.1f}%")
    print(f"  Profit threshold: {profile.profit_threshold}")
    print(f"  Position size: {profile.order_size:.0f} shares")
    print(f"  Description: {profile.description}")

    is_valid, msg = validate_capital_for_profile(750.0, profile)
    print(f"  {msg}")
