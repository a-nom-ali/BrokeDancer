"""
Tests for multi-domain workflow nodes.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.workflow.nodes import (
    VenuePriceNode,
    VenuePositionNode,
    CalculateSpreadNode,
    CalculateProfitNode,
    ThresholdCheckNode,
    ExecuteActionNode,
    CreateOpportunityNode
)
from src.core.graph_runtime import NodeExecutionContext, NodeStatus
from src.core.asset import AssetValuation, AssetPosition
from src.core.venue import ActionType, ActionResult


class TestVenuePriceNode:
    """Test VenuePriceNode"""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful price fetch"""
        # Mock venue and asset
        mock_asset = Mock()
        mock_asset.symbol = "BTC-USDT"

        mock_valuation = AssetValuation(
            current_value=50000.0,
            currency="USD",
            bid=49950.0,
            ask=50050.0
        )

        mock_asset.fetch_current_valuation = AsyncMock(return_value=mock_valuation)

        mock_venue = Mock()
        mock_venue.name = "MockExchange"
        mock_venue.get_asset = AsyncMock(return_value=mock_asset)

        # Create node
        node = VenuePriceNode(
            node_id="price_1",
            venue=mock_venue,
            asset_symbol="BTC-USDT"
        )

        # Execute
        context = NodeExecutionContext(
            node_id="price_1",
            graph_id="test_graph",
            execution_id="test_exec"
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["price"] == 50000.0
        assert result.outputs["valuation"] == mock_valuation
        assert result.outputs["asset"] == mock_asset

    @pytest.mark.asyncio
    async def test_execute_asset_not_found(self):
        """Test when asset is not found"""
        mock_venue = Mock()
        mock_venue.name = "MockExchange"
        mock_venue.get_asset = AsyncMock(return_value=None)

        node = VenuePriceNode(
            node_id="price_1",
            venue=mock_venue,
            asset_symbol="INVALID"
        )

        context = NodeExecutionContext(
            node_id="price_1",
            graph_id="test_graph",
            execution_id="test_exec"
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.FAILED
        assert "not found" in result.error_message.lower()


class TestCalculateSpreadNode:
    """Test CalculateSpreadNode"""

    @pytest.mark.asyncio
    async def test_calculate_positive_spread(self):
        """Test calculating positive spread"""
        node = CalculateSpreadNode(node_id="spread_1")

        context = NodeExecutionContext(
            node_id="spread_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "price_a": 50000.0,
                "price_b": 50500.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["spread"] == 500.0
        assert result.outputs["spread_pct"] == 1.0
        assert result.outputs["profitable"] is True

    @pytest.mark.asyncio
    async def test_calculate_negative_spread(self):
        """Test calculating negative spread"""
        node = CalculateSpreadNode(node_id="spread_1")

        context = NodeExecutionContext(
            node_id="spread_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "price_a": 50500.0,
                "price_b": 50000.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["spread"] == -500.0
        assert result.outputs["profitable"] is False


class TestCalculateProfitNode:
    """Test CalculateProfitNode"""

    @pytest.mark.asyncio
    async def test_calculate_profit(self):
        """Test profit calculation"""
        node = CalculateProfitNode(node_id="profit_1")

        context = NodeExecutionContext(
            node_id="profit_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "revenue": 1000.0,
                "cost": 800.0,
                "fees": 50.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["profit"] == 150.0  # 1000 - 800 - 50
        assert result.outputs["profit_pct"] == 18.75  # 150 / 800 * 100
        assert result.outputs["roi"] == pytest.approx(17.647, rel=0.01)  # 150 / 850 * 100


class TestThresholdCheckNode:
    """Test ThresholdCheckNode"""

    @pytest.mark.asyncio
    async def test_threshold_pass(self):
        """Test passing threshold"""
        node = ThresholdCheckNode(
            node_id="threshold_1",
            threshold=100.0,
            operator=">="
        )

        context = NodeExecutionContext(
            node_id="threshold_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={"value": 150.0}
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["passed"] is True
        assert result.outputs["value"] == 150.0

    @pytest.mark.asyncio
    async def test_threshold_fail(self):
        """Test failing threshold"""
        node = ThresholdCheckNode(
            node_id="threshold_1",
            threshold=100.0,
            operator=">="
        )

        context = NodeExecutionContext(
            node_id="threshold_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={"value": 50.0}
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["passed"] is False


class TestExecuteActionNode:
    """Test ExecuteActionNode"""

    @pytest.mark.asyncio
    async def test_execute_action_success(self):
        """Test successful action execution"""
        # Mock venue
        mock_action_result = ActionResult(
            request=None,
            success=True,
            venue_transaction_id="txn_123",
            status="completed"
        )

        mock_venue = Mock()
        mock_venue.venue_id = "test_venue"
        mock_venue.execute_action = AsyncMock(return_value=mock_action_result)

        # Mock asset
        mock_asset = Mock()
        mock_asset.symbol = "BTC"

        # Create node
        node = ExecuteActionNode(
            node_id="exec_1",
            venue=mock_venue,
            action_type=ActionType.PLACE_ORDER
        )

        # Execute
        context = NodeExecutionContext(
            node_id="exec_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "asset": mock_asset,
                "quantity": 0.1,
                "price": 50000.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        assert result.outputs["success"] is True
        assert result.outputs["transaction_id"] == "txn_123"

    @pytest.mark.asyncio
    async def test_execute_action_missing_asset(self):
        """Test action execution without asset"""
        mock_venue = Mock()
        mock_venue.venue_id = "test_venue"

        node = ExecuteActionNode(
            node_id="exec_1",
            venue=mock_venue,
            action_type=ActionType.PLACE_ORDER
        )

        context = NodeExecutionContext(
            node_id="exec_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "quantity": 0.1,
                "price": 50000.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.FAILED
        assert "missing asset" in result.error_message.lower()


class TestCreateOpportunityNode:
    """Test CreateOpportunityNode"""

    @pytest.mark.asyncio
    async def test_create_opportunity(self):
        """Test opportunity creation"""
        node = CreateOpportunityNode(
            node_id="opp_1",
            strategy_name="TestStrategy"
        )

        context = NodeExecutionContext(
            node_id="opp_1",
            graph_id="test_graph",
            execution_id="test_exec",
            inputs={
                "confidence": 0.85,
                "expected_profit": 100.0,
                "expected_cost": 50.0
            }
        )

        result = await node.execute(context)

        assert result.status == NodeStatus.COMPLETED
        opp = result.outputs["opportunity"]
        assert opp.confidence == 0.85
        assert opp.expected_profit == 100.0
        assert opp.expected_cost == 50.0
        assert opp.expected_roi == 200.0  # 100 / 50 * 100
        assert opp.strategy_name == "TestStrategy"
