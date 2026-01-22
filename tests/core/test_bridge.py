"""
Tests for the bridge layer that integrates legacy and new systems.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from src.core.bridge import (
    StrategyBridge,
    OpportunityConverter,
    wrap_legacy_strategy,
    wrap_provider_as_venue
)
from src.core.strategy import OpportunityType
from src.providers.base import BaseProvider, Orderbook, OrderbookEntry, Balance, OrderSide, OrderType
from src.strategies.base import BaseStrategy as LegacyBaseStrategy, Opportunity as LegacyOpportunity


class MockProvider(BaseProvider):
    """Mock provider for testing"""

    def __init__(self, config=None):
        super().__init__(config or {})
        self._connected = False

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def get_balance(self, asset=None):
        return {
            "BTC": Balance(asset="BTC", available=1.0, reserved=0.0, total=1.0),
            "USDT": Balance(asset="USDT", available=10000.0, reserved=0.0, total=10000.0)
        }

    def get_orderbook(self, pair, depth=100):
        return Orderbook(
            pair=pair,
            bids=[OrderbookEntry(price=50000, volume=1.0)],
            asks=[OrderbookEntry(price=50100, volume=1.0)],
            timestamp=int(datetime.utcnow().timestamp() * 1000)
        )

    def place_order(self, pair, side, order_type, size, price=None, **kwargs):
        from src.providers.base import Order, OrderStatus
        return Order(
            order_id="test_order_123",
            pair=pair,
            side=side,
            type=order_type,
            price=price,
            size=size,
            filled_size=size,
            status=OrderStatus.FILLED,
            created_at=int(datetime.utcnow().timestamp() * 1000),
            updated_at=int(datetime.utcnow().timestamp() * 1000)
        )

    def get_order(self, order_id):
        from src.providers.base import Order, OrderStatus
        return Order(
            order_id=order_id,
            pair="BTC-USDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            price=50000,
            size=0.1,
            filled_size=0.1,
            status=OrderStatus.FILLED,
            created_at=int(datetime.utcnow().timestamp() * 1000),
            updated_at=int(datetime.utcnow().timestamp() * 1000)
        )

    def cancel_order(self, order_id):
        return True

    def get_markets(self):
        return ["BTC-USDT", "ETH-USDT", "BTC-USD"]


class MockLegacyStrategy(LegacyBaseStrategy):
    """Mock legacy strategy for testing"""

    async def run(self):
        """Main loop"""
        while self.running:
            opp = await self.find_opportunity()
            if opp and opp.expected_profit >= self.min_profit:
                await self.execute(opp)
            await asyncio.sleep(self.scan_interval)

    async def find_opportunity(self):
        """Return mock opportunity"""
        return LegacyOpportunity(
            strategy_name=self.name,
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            confidence=0.8,
            expected_profit=100.0,
            metadata={"test": "data"}
        )

    async def execute(self, opportunity):
        """Mock execution"""
        from src.strategies.base import TradeResult
        return TradeResult(
            opportunity=opportunity,
            success=True,
            actual_profit=95.0,
            orders=[],
            execution_time_ms=50.0
        )


class TestOpportunityConverter:
    """Test OpportunityConverter utility"""

    def test_to_generic(self):
        """Test converting legacy to generic opportunity"""
        legacy_opp = LegacyOpportunity(
            strategy_name="test_strategy",
            timestamp=1700000000000,
            confidence=0.85,
            expected_profit=50.0,
            metadata={"arbitrage": True, "spread": 0.5}
        )

        generic_opp = OpportunityConverter.to_generic(legacy_opp)

        assert generic_opp.strategy_name == "test_strategy"
        assert generic_opp.confidence == 0.85
        assert generic_opp.expected_profit == 50.0
        assert generic_opp.opportunity_type == OpportunityType.ARBITRAGE
        assert generic_opp.metadata["arbitrage"] is True

    def test_to_legacy(self):
        """Test converting generic to legacy opportunity"""
        from src.core.strategy import Opportunity

        generic_opp = Opportunity(
            opportunity_id="test_123",
            opportunity_type=OpportunityType.MARKET_MAKING,
            strategy_name="test_strategy",
            confidence=0.9,
            expected_profit=75.0,
            expected_cost=10.0,
            expected_roi=650.0,
            metadata={"spread": 1.0}
        )

        legacy_opp = OpportunityConverter.to_legacy(generic_opp)

        assert legacy_opp.strategy_name == "test_strategy"
        assert legacy_opp.confidence == 0.9
        assert legacy_opp.expected_profit == 75.0
        assert legacy_opp.metadata["spread"] == 1.0


class TestStrategyBridge:
    """Test StrategyBridge for wrapping legacy strategies"""

    @pytest.mark.asyncio
    async def test_wrap_legacy_strategy(self):
        """Test wrapping a legacy strategy"""
        provider = MockProvider()
        legacy_strategy = MockLegacyStrategy(
            provider=provider,
            config={"scan_interval": 1.0, "min_profit": 10.0}
        )

        # Wrap it
        bridge = StrategyBridge(legacy_strategy)

        assert bridge.strategy_name == legacy_strategy.name
        assert bridge.config.min_expected_profit == 10.0

    @pytest.mark.asyncio
    async def test_find_opportunities(self):
        """Test finding opportunities through bridge"""
        provider = MockProvider()
        legacy_strategy = MockLegacyStrategy(
            provider=provider,
            config={"scan_interval": 1.0, "min_profit": 10.0}
        )

        bridge = StrategyBridge(legacy_strategy)
        await bridge.initialize()

        opportunities = await bridge.find_opportunities()

        assert len(opportunities) == 1
        assert opportunities[0].expected_profit == 100.0
        assert opportunities[0].confidence == 0.8

    @pytest.mark.asyncio
    async def test_execute_opportunity(self):
        """Test executing opportunity through bridge"""
        provider = MockProvider()
        legacy_strategy = MockLegacyStrategy(
            provider=provider,
            config={"scan_interval": 1.0, "min_profit": 10.0}
        )

        bridge = StrategyBridge(legacy_strategy)
        await bridge.initialize()

        # Find opportunity
        opportunities = await bridge.find_opportunities()
        opp = opportunities[0]

        # Execute it
        result = await bridge.execute_opportunity(opp)

        assert result.success is True
        assert result.actual_profit == 95.0


class TestProviderWrapper:
    """Test wrapping providers as venues"""

    @pytest.mark.asyncio
    async def test_wrap_provider_as_venue(self):
        """Test wrapping a provider as a venue"""
        provider = MockProvider()
        venue = wrap_provider_as_venue(provider)

        assert venue.name == "MockProvider"
        assert venue.is_connected is False

        # Connect
        await venue.connect()
        assert venue.is_connected is True

        # List assets
        assets = await venue.list_assets()
        assert len(assets) > 0

        # Disconnect
        await venue.disconnect()
        assert venue.is_connected is False


def test_wrap_legacy_strategy_convenience():
    """Test convenience function for wrapping"""
    provider = MockProvider()
    legacy_strategy = MockLegacyStrategy(
        provider=provider,
        config={"scan_interval": 1.0}
    )

    bridge = wrap_legacy_strategy(legacy_strategy)

    assert isinstance(bridge, StrategyBridge)
    assert bridge.strategy_name == legacy_strategy.name
