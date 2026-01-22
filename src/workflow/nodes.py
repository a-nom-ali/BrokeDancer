"""
Multi-Domain Workflow Nodes

This module extends the workflow system with nodes that work across all domains:
trading, GPU allocation, ad optimization, ecommerce arbitrage, etc.

Each node type implements the Node interface from core.graph_runtime.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from ..core.graph_runtime import (
    Node,
    NodeCategory,
    NodeInput,
    NodeOutput,
    NodeExecutionContext,
    NodeExecutionResult,
    NodeStatus,
    register_node_type
)
from ..core.asset import Asset, AssetValuation
from ..core.venue import Venue, ActionRequest, ActionType
from ..core.strategy import Opportunity, OpportunityType


# ==================== SOURCE NODES ====================

@register_node_type("venue_price")
class VenuePriceNode(Node):
    """
    Fetch current price/valuation from any venue.

    Works across all domains:
    - Trading: Market price
    - GPU: Rental rate
    - Ads: CPC/CPM
    - Ecommerce: Market price
    """

    def __init__(self, node_id: str, venue: Venue, asset_symbol: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="venue_price",
            category=NodeCategory.SOURCE,
            inputs=[],
            outputs=[
                NodeOutput(name="price", data_type="number"),
                NodeOutput(name="valuation", data_type="object"),
                NodeOutput(name="asset", data_type="asset")
            ],
            config={"venue_id": venue.venue_id, "asset_symbol": asset_symbol}
        )
        self.venue = venue
        self.asset_symbol = asset_symbol

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Fetch current price"""
        start_time = datetime.utcnow()

        try:
            # Get asset from venue
            asset = await self.venue.get_asset(self.asset_symbol)

            if not asset:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.FAILED,
                    error_message=f"Asset {self.asset_symbol} not found on {self.venue.name}"
                )

            # Fetch current valuation
            valuation = await asset.fetch_current_valuation()

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "price": valuation.current_value,
                    "valuation": valuation,
                    "asset": asset
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


@register_node_type("venue_position")
class VenuePositionNode(Node):
    """
    Fetch current position/holdings from any venue.

    Works across all domains:
    - Trading: Asset balance
    - GPU: GPU availability
    - Ads: Campaign status
    - Ecommerce: Inventory level
    """

    def __init__(self, node_id: str, venue: Venue, asset_symbol: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="venue_position",
            category=NodeCategory.SOURCE,
            inputs=[],
            outputs=[
                NodeOutput(name="position", data_type="object"),
                NodeOutput(name="quantity", data_type="number"),
                NodeOutput(name="available", data_type="number")
            ],
            config={"venue_id": venue.venue_id, "asset_symbol": asset_symbol}
        )
        self.venue = venue
        self.asset_symbol = asset_symbol

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Fetch current position"""
        start_time = datetime.utcnow()

        try:
            asset = await self.venue.get_asset(self.asset_symbol)
            if not asset:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.FAILED,
                    error_message=f"Asset {self.asset_symbol} not found"
                )

            position = await self.venue.get_position(asset)

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            if position:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.COMPLETED,
                    outputs={
                        "position": position,
                        "quantity": position.quantity,
                        "available": position.available
                    },
                    execution_time_ms=elapsed
                )
            else:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.COMPLETED,
                    outputs={
                        "position": None,
                        "quantity": 0.0,
                        "available": 0.0
                    },
                    execution_time_ms=elapsed
                )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# ==================== TRANSFORM NODES ====================

@register_node_type("calculate_spread")
class CalculateSpreadNode(Node):
    """
    Calculate price spread between two sources.

    Universal across domains:
    - Trading: Arbitrage spread between exchanges
    - GPU: Rental rate difference between marketplaces
    - Ads: ROAS difference between campaigns
    - Ecommerce: Profit margin (sell price - buy price)
    """

    def __init__(self, node_id: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="calculate_spread",
            category=NodeCategory.TRANSFORM,
            inputs=[
                NodeInput(name="price_a", data_type="number", required=True),
                NodeInput(name="price_b", data_type="number", required=True)
            ],
            outputs=[
                NodeOutput(name="spread", data_type="number"),
                NodeOutput(name="spread_pct", data_type="number"),
                NodeOutput(name="profitable", data_type="boolean")
            ],
            config=kwargs.get("config", {})
        )

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Calculate spread"""
        start_time = datetime.utcnow()

        try:
            price_a = context.inputs.get("price_a", 0)
            price_b = context.inputs.get("price_b", 0)

            spread = price_b - price_a
            spread_pct = (spread / price_a * 100) if price_a > 0 else 0
            profitable = spread > 0

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "profitable": profitable
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


@register_node_type("calculate_profit")
class CalculateProfitNode(Node):
    """
    Calculate expected profit from an action.

    Universal across domains:
    - Trading: Trade profit after fees
    - GPU: Rental revenue - power cost
    - Ads: Revenue - ad spend
    - Ecommerce: Selling price - (buying cost + fees)
    """

    def __init__(self, node_id: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="calculate_profit",
            category=NodeCategory.TRANSFORM,
            inputs=[
                NodeInput(name="revenue", data_type="number", required=True),
                NodeInput(name="cost", data_type="number", required=True),
                NodeInput(name="fees", data_type="number", required=False, default_value=0)
            ],
            outputs=[
                NodeOutput(name="profit", data_type="number"),
                NodeOutput(name="profit_pct", data_type="number"),
                NodeOutput(name="roi", data_type="number")
            ],
            config=kwargs.get("config", {})
        )

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Calculate profit"""
        start_time = datetime.utcnow()

        try:
            revenue = context.inputs.get("revenue", 0)
            cost = context.inputs.get("cost", 0)
            fees = context.inputs.get("fees", 0)

            profit = revenue - cost - fees
            profit_pct = (profit / cost * 100) if cost > 0 else 0
            roi = (profit / (cost + fees) * 100) if (cost + fees) > 0 else 0

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "roi": roi
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# ==================== CONDITION NODES ====================

@register_node_type("threshold_check")
class ThresholdCheckNode(Node):
    """
    Check if a value meets a threshold.

    Universal conditions:
    - Trading: Spread > min_spread
    - GPU: Rate > min_rate
    - Ads: ROAS > min_roas
    - Ecommerce: ROI > min_roi
    """

    def __init__(self, node_id: str, threshold: float, operator: str = ">=", **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="threshold_check",
            category=NodeCategory.CONDITION,
            inputs=[
                NodeInput(name="value", data_type="number", required=True)
            ],
            outputs=[
                NodeOutput(name="passed", data_type="boolean"),
                NodeOutput(name="value", data_type="number")
            ],
            config={"threshold": threshold, "operator": operator}
        )
        self.threshold = threshold
        self.operator = operator

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Check threshold"""
        start_time = datetime.utcnow()

        try:
            value = context.inputs.get("value", 0)

            # Evaluate condition
            if self.operator == ">=":
                passed = value >= self.threshold
            elif self.operator == ">":
                passed = value > self.threshold
            elif self.operator == "<=":
                passed = value <= self.threshold
            elif self.operator == "<":
                passed = value < self.threshold
            elif self.operator == "==":
                passed = value == self.threshold
            else:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.FAILED,
                    error_message=f"Unknown operator: {self.operator}"
                )

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "passed": passed,
                    "value": value
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# ==================== EXECUTOR NODES ====================

@register_node_type("execute_action")
class ExecuteActionNode(Node):
    """
    Execute an action on a venue.

    Universal actions:
    - Trading: PLACE_ORDER, CANCEL_ORDER
    - GPU: ALLOCATE, DEALLOCATE, SET_PRICE
    - Ads: SET_BUDGET, ADJUST_BID
    - Ecommerce: CREATE_LISTING, UPDATE_LISTING
    """

    def __init__(
        self,
        node_id: str,
        venue: Venue,
        action_type: ActionType,
        **kwargs
    ):
        super().__init__(
            node_id=node_id,
            node_type="execute_action",
            category=NodeCategory.EXECUTOR,
            inputs=[
                NodeInput(name="asset", data_type="asset", required=True),
                NodeInput(name="quantity", data_type="number", required=True),
                NodeInput(name="price", data_type="number", required=False)
            ],
            outputs=[
                NodeOutput(name="result", data_type="object"),
                NodeOutput(name="success", data_type="boolean"),
                NodeOutput(name="transaction_id", data_type="string")
            ],
            config={"venue_id": venue.venue_id, "action_type": action_type.value}
        )
        self.venue = venue
        self.action_type = action_type

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute action"""
        start_time = datetime.utcnow()

        try:
            asset = context.inputs.get("asset")
            quantity = context.inputs.get("quantity", 0)
            price = context.inputs.get("price")

            if not asset:
                return NodeExecutionResult(
                    node_id=self.node_id,
                    status=NodeStatus.FAILED,
                    error_message="Missing asset input"
                )

            # Create action request
            request = ActionRequest(
                action_type=self.action_type,
                asset=asset,
                quantity=quantity,
                price=price
            )

            # Execute on venue
            result = await self.venue.execute_action(request)

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED if result.success else NodeStatus.FAILED,
                outputs={
                    "result": result,
                    "success": result.success,
                    "transaction_id": result.venue_transaction_id or ""
                },
                execution_time_ms=elapsed,
                error_message=result.error_message if not result.success else None
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# ==================== OPPORTUNITY NODES ====================

@register_node_type("create_opportunity")
class CreateOpportunityNode(Node):
    """
    Create an Opportunity object from inputs.

    Universal opportunity creation across all domains.
    """

    def __init__(self, node_id: str, strategy_name: str, **kwargs):
        super().__init__(
            node_id=node_id,
            node_type="create_opportunity",
            category=NodeCategory.CUSTOM,
            inputs=[
                NodeInput(name="confidence", data_type="number", required=True),
                NodeInput(name="expected_profit", data_type="number", required=True),
                NodeInput(name="expected_cost", data_type="number", required=False, default_value=0),
                NodeInput(name="asset", data_type="asset", required=False)
            ],
            outputs=[
                NodeOutput(name="opportunity", data_type="object")
            ],
            config={"strategy_name": strategy_name}
        )
        self.strategy_name = strategy_name

    async def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Create opportunity"""
        start_time = datetime.utcnow()

        try:
            confidence = context.inputs.get("confidence", 0)
            expected_profit = context.inputs.get("expected_profit", 0)
            expected_cost = context.inputs.get("expected_cost", 0)
            asset = context.inputs.get("asset")

            # Create opportunity
            opportunity = Opportunity(
                opportunity_id=f"{self.strategy_name}_{int(datetime.utcnow().timestamp())}",
                opportunity_type=OpportunityType.CUSTOM,
                strategy_name=self.strategy_name,
                confidence=confidence,
                expected_profit=expected_profit,
                expected_cost=expected_cost,
                expected_roi=(expected_profit / expected_cost * 100) if expected_cost > 0 else 0,
                primary_asset=asset
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "opportunity": opportunity
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            return NodeExecutionResult(
                node_id=self.node_id,
                status=NodeStatus.FAILED,
                error_message=str(e),
                execution_time_ms=elapsed
            )


# Export all node types
__all__ = [
    'VenuePriceNode',
    'VenuePositionNode',
    'CalculateSpreadNode',
    'CalculateProfitNode',
    'ThresholdCheckNode',
    'ExecuteActionNode',
    'CreateOpportunityNode',
]
