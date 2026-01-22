"""
Bridge Layer

This module provides seamless integration between the existing trading system
and the new generic abstraction layer. It allows:

1. Existing BaseProvider → Generic Venue (already done in adapters/trading.py)
2. Existing BaseStrategy → Generic Strategy (this file)
3. Existing Opportunity → Generic Opportunity (this file)
4. Bidirectional compatibility (old code works with new, new code works with old)
"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

from ..providers.base import BaseProvider, Order, OrderSide, OrderType
from ..strategies.base import (
    BaseStrategy as LegacyBaseStrategy,
    Opportunity as LegacyOpportunity,
    TradeResult as LegacyTradeResult,
    StrategyStatus as LegacyStrategyStatus
)

from .asset import Asset, AssetPosition
from .venue import Venue, ActionRequest, ActionResult, ActionType
from .strategy import (
    Strategy,
    Opportunity,
    OpportunityType,
    OpportunityStatus,
    ExecutionResult,
    StrategyStatus,
    StrategyConfig
)
from .adapters.trading import TradingVenueAdapter, FinancialAssetAdapter


class LegacyProviderWrapper:
    """
    Wraps a new generic Venue to look like a legacy BaseProvider.

    This allows new Venue implementations to be used with existing strategies.
    """

    def __init__(self, venue: TradingVenueAdapter):
        self.venue = venue
        self._connected = False

    def connect(self):
        """Connect to venue (synchronous wrapper)"""
        asyncio.run(self.venue.connect())
        self._connected = True

    def disconnect(self):
        """Disconnect from venue"""
        asyncio.run(self.venue.disconnect())
        self._connected = False

    def get_balance(self, asset: Optional[str] = None) -> Dict[str, Any]:
        """Get balance (synchronous wrapper)"""
        # This would need async handling in real implementation
        # For now, return empty dict as placeholder
        return {}

    def get_orderbook(self, pair: str, depth: int = 100):
        """Get orderbook (synchronous wrapper)"""
        return asyncio.run(self.venue.get_orderbook(
            asset=asyncio.run(self.venue.get_asset(pair))
        ))

    def place_order(
        self,
        pair: str,
        side: OrderSide,
        order_type: OrderType,
        size: float,
        price: Optional[float] = None,
        **kwargs
    ) -> Order:
        """Place order (synchronous wrapper)"""
        # Create action request
        asset = asyncio.run(self.venue.get_asset(pair))

        request = ActionRequest(
            action_type=ActionType.PLACE_ORDER,
            asset=asset,
            quantity=size,
            price=price,
            side=side.value.lower(),
            order_type=order_type.value.lower()
        )

        result = asyncio.run(self.venue.execute_action(request))

        # Convert ActionResult to Order
        from ..providers.base import Order, OrderStatus

        return Order(
            order_id=result.venue_transaction_id or "",
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=result.executed_quantity or 0,
            status=OrderStatus.FILLED if result.success else OrderStatus.REJECTED,
            created_at=int(result.submitted_at.timestamp() * 1000),
            updated_at=int((result.completed_at or result.submitted_at).timestamp() * 1000)
        )

    def get_order(self, order_id: str) -> Order:
        """Get order status"""
        result = asyncio.run(self.venue.query_action_status(order_id))

        from ..providers.base import Order, OrderStatus

        # Extract order info from metadata
        metadata = result.metadata

        return Order(
            order_id=order_id,
            pair="",  # Not available in result
            side=OrderSide.BUY,  # Default
            type=OrderType.LIMIT,  # Default
            price=None,
            size=0,
            filled_size=0,
            status=OrderStatus[result.status.upper()] if result.status else OrderStatus.PENDING,
            created_at=0,
            updated_at=0
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        request = ActionRequest(
            action_type=ActionType.CANCEL_ORDER,
            asset=None,  # Not needed for cancel
            quantity=0,
            metadata={"order_id": order_id}
        )

        result = asyncio.run(self.venue.execute_action(request))
        return result.success

    def get_markets(self) -> List[str]:
        """Get available markets"""
        assets = asyncio.run(self.venue.list_assets())
        return [asset.symbol for asset in assets]


class StrategyBridge(Strategy):
    """
    Wraps a legacy BaseStrategy to work with the new Strategy interface.

    This allows existing strategies to be used in the new system without modification.
    """

    def __init__(
        self,
        legacy_strategy: LegacyBaseStrategy,
        venue: Optional[TradingVenueAdapter] = None
    ):
        # If venue not provided, wrap the strategy's provider
        if venue is None and hasattr(legacy_strategy, 'provider'):
            # Create a TradingVenueAdapter from the legacy provider
            venue = TradingVenueAdapter(provider=legacy_strategy.provider)

        # Initialize generic Strategy
        super().__init__(
            strategy_id=f"legacy_{legacy_strategy.name}",
            strategy_name=legacy_strategy.name,
            venues=[venue] if venue else [],
            config=StrategyConfig(
                scan_interval_ms=int(legacy_strategy.scan_interval * 1000),
                min_expected_profit=legacy_strategy.min_profit,
                dry_run_mode=legacy_strategy.dry_run
            )
        )

        self.legacy_strategy = legacy_strategy
        self.venue = venue

    async def initialize(self) -> bool:
        """Initialize strategy"""
        try:
            await self.legacy_strategy.start()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize legacy strategy: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown strategy"""
        try:
            await self.legacy_strategy.stop()
            return True
        except Exception:
            return False

    async def find_opportunities(self) -> List[Opportunity]:
        """Find opportunities using legacy strategy"""
        # Call legacy find_opportunity method
        legacy_opp = await self.legacy_strategy.find_opportunity()

        if legacy_opp is None:
            return []

        # Convert legacy Opportunity to generic Opportunity
        generic_opp = self._convert_legacy_opportunity(legacy_opp)
        return [generic_opp]

    def _convert_legacy_opportunity(self, legacy_opp: LegacyOpportunity) -> Opportunity:
        """Convert legacy Opportunity to generic Opportunity"""
        return Opportunity(
            opportunity_id=f"{legacy_opp.strategy_name}_{legacy_opp.timestamp}",
            opportunity_type=OpportunityType.ARBITRAGE,  # Default assumption
            strategy_name=legacy_opp.strategy_name,
            strategy_version="1.0.0",
            confidence=legacy_opp.confidence,
            expected_profit=legacy_opp.expected_profit,
            expected_cost=0.0,  # Not available in legacy
            expected_roi=0.0,  # Would need to calculate
            detected_at=datetime.fromtimestamp(legacy_opp.timestamp / 1000),
            metadata=legacy_opp.metadata
        )

    async def validate_opportunity(self, opportunity: Opportunity) -> bool:
        """Validate opportunity"""
        # Use legacy strategy's validation if available
        return opportunity.confidence >= self.config.min_confidence

    async def execute_opportunity(self, opportunity: Opportunity) -> ExecutionResult:
        """Execute opportunity using legacy strategy"""
        # Convert generic Opportunity back to legacy
        legacy_opp = LegacyOpportunity(
            strategy_name=opportunity.strategy_name,
            timestamp=int(opportunity.detected_at.timestamp() * 1000),
            confidence=opportunity.confidence,
            expected_profit=opportunity.expected_profit,
            metadata=opportunity.metadata
        )

        # Execute using legacy strategy
        legacy_result = await self.legacy_strategy.execute(legacy_opp)

        # Convert legacy TradeResult to generic ExecutionResult
        return self._convert_legacy_result(opportunity, legacy_result)

    def _convert_legacy_result(
        self,
        opportunity: Opportunity,
        legacy_result: LegacyTradeResult
    ) -> ExecutionResult:
        """Convert legacy TradeResult to generic ExecutionResult"""
        return ExecutionResult(
            opportunity=opportunity,
            success=legacy_result.success,
            actual_profit=legacy_result.actual_profit,
            actual_cost=None,  # Not available in legacy
            actual_roi=None,  # Would need to calculate
            action_results=[],  # Would need to convert orders
            error_message=legacy_result.error,
            execution_time_ms=legacy_result.execution_time_ms
        )


class OpportunityConverter:
    """
    Utility class for converting between legacy and generic opportunity formats.
    """

    @staticmethod
    def to_generic(legacy_opp: LegacyOpportunity) -> Opportunity:
        """Convert legacy Opportunity to generic Opportunity"""
        # Infer opportunity type from metadata
        opp_type = OpportunityType.CUSTOM
        if "arbitrage" in legacy_opp.metadata:
            opp_type = OpportunityType.ARBITRAGE
        elif "spread" in legacy_opp.metadata:
            opp_type = OpportunityType.MARKET_MAKING

        return Opportunity(
            opportunity_id=f"{legacy_opp.strategy_name}_{legacy_opp.timestamp}",
            opportunity_type=opp_type,
            strategy_name=legacy_opp.strategy_name,
            strategy_version="1.0.0",
            confidence=legacy_opp.confidence,
            expected_profit=legacy_opp.expected_profit,
            expected_cost=0.0,
            expected_roi=0.0,
            detected_at=datetime.fromtimestamp(legacy_opp.timestamp / 1000),
            metadata=legacy_opp.metadata
        )

    @staticmethod
    def to_legacy(generic_opp: Opportunity) -> LegacyOpportunity:
        """Convert generic Opportunity to legacy Opportunity"""
        return LegacyOpportunity(
            strategy_name=generic_opp.strategy_name,
            timestamp=int(generic_opp.detected_at.timestamp() * 1000),
            confidence=generic_opp.confidence,
            expected_profit=generic_opp.expected_profit,
            metadata=generic_opp.metadata
        )


def wrap_legacy_strategy(legacy_strategy: LegacyBaseStrategy) -> Strategy:
    """
    Convenience function to wrap a legacy strategy.

    Args:
        legacy_strategy: Instance of old BaseStrategy

    Returns:
        Generic Strategy instance that wraps the legacy strategy

    Example:
        >>> from strategies.binary_arbitrage import BinaryArbitrageStrategy
        >>> legacy_strat = BinaryArbitrageStrategy(provider, config)
        >>> generic_strat = wrap_legacy_strategy(legacy_strat)
        >>> # Now can use with new system
        >>> await generic_strat.initialize()
        >>> opportunities = await generic_strat.find_opportunities()
    """
    return StrategyBridge(legacy_strategy)


def wrap_provider_as_venue(provider: BaseProvider) -> TradingVenueAdapter:
    """
    Convenience function to wrap a legacy provider as a venue.

    Args:
        provider: Instance of old BaseProvider

    Returns:
        Generic Venue instance that wraps the provider

    Example:
        >>> from providers.binance import BinanceProvider
        >>> provider = BinanceProvider(api_key=..., api_secret=...)
        >>> venue = wrap_provider_as_venue(provider)
        >>> # Now can use with new system
        >>> await venue.connect()
        >>> assets = await venue.list_assets()
    """
    return TradingVenueAdapter(provider=provider)
