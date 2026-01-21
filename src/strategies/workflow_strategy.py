"""
Workflow Strategy

Executes visual workflow definitions created in the strategy builder.
This strategy wraps the WorkflowExecutor to allow workflows to run as bots.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from .base import PollingStrategy, Opportunity, TradeResult
from ..providers.base import BaseProvider
from ..workflow.executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class WorkflowStrategy(PollingStrategy):
    """
    Strategy that executes visual workflow definitions.

    Workflows are created in the strategy builder and contain:
    - Provider nodes (data sources)
    - Condition nodes (logic)
    - Action nodes (trades)
    - Trigger nodes (signals)
    - Risk management nodes

    This strategy executes the workflow graph on each polling interval.
    """

    def __init__(self, provider: BaseProvider, config: Dict[str, Any], name: Optional[str] = None):
        """
        Initialize workflow strategy.

        Args:
            provider: Primary provider (may not be used if workflow has its own)
            config: Strategy configuration with 'workflow' key containing workflow definition
            name: Optional custom name
        """
        super().__init__(provider, config, name or "Workflow")

        # Extract workflow definition
        self.workflow_def = config.get('workflow')
        if not self.workflow_def:
            raise ValueError("Workflow strategy requires 'workflow' in config")

        # Validate workflow structure
        if 'blocks' not in self.workflow_def or 'connections' not in self.workflow_def:
            raise ValueError("Workflow must have 'blocks' and 'connections'")

        # Create workflow executor
        self.executor = WorkflowExecutor(self.workflow_def)

        # Initialize executor (async operation will be done in start)
        self._executor_initialized = False

        logger.info(f"Workflow strategy created with {len(self.workflow_def['blocks'])} blocks")

    async def find_opportunity(self) -> Optional[Opportunity]:
        """
        Execute workflow to find trading opportunity.

        The workflow execution determines if there's an opportunity.
        If the workflow completes successfully and produces action signals,
        we return an opportunity.

        Returns:
            Opportunity if workflow signals a trade, None otherwise
        """
        try:
            # Initialize executor on first run
            if not self._executor_initialized:
                await self.executor.initialize()
                self._executor_initialized = True

            # Execute workflow
            result = await self.executor.execute()

            # Check if workflow executed successfully
            if result['status'] not in ['completed', 'completed_with_errors']:
                self.logger.debug("Workflow execution failed, no opportunity")
                return None

            # Check if any action nodes produced signals
            # Look for action node outputs that indicate a trade should be placed
            has_trade_signal = False
            trade_details = {}

            for node_result in result['results']:
                if node_result['nodeType'] == 'actions':
                    output = node_result.get('output', {})
                    # If action node has an order output, it's a trade signal
                    if 'order' in output and output['order'] is not None:
                        has_trade_signal = True
                        trade_details = output['order']
                        break

            if not has_trade_signal:
                return None

            # Create opportunity from workflow execution
            opportunity = Opportunity(
                strategy_name=self.name,
                timestamp=int(asyncio.get_event_loop().time() * 1000),
                confidence=0.9,  # Workflow-based, assume high confidence
                expected_profit=trade_details.get('amount', 0) * 0.01,  # Estimate 1% profit
                metadata={
                    'workflow_execution': result,
                    'trade_details': trade_details,
                    'execution_duration': result['duration']
                }
            )

            return opportunity

        except Exception as e:
            self.logger.error(f"Error executing workflow: {e}", exc_info=True)
            return None

    async def execute(self, opportunity: Opportunity) -> TradeResult:
        """
        Execute trade based on workflow opportunity.

        Since the workflow already determined the trade parameters,
        we just need to confirm execution.

        Args:
            opportunity: Opportunity detected by workflow

        Returns:
            TradeResult with execution details
        """
        self.logger.info("=" * 70)
        self.logger.info("🤖 EXECUTING WORKFLOW-BASED TRADE")
        self.logger.info("=" * 70)

        trade_details = opportunity.metadata.get('trade_details', {})
        self.logger.info(f"Trade type:      {trade_details.get('side', 'unknown')}")
        self.logger.info(f"Amount:          {trade_details.get('amount', 0)}")
        self.logger.info(f"Expected profit: ${opportunity.expected_profit:.2f}")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("🔸 DRY RUN MODE - No real orders placed")
            return TradeResult(
                opportunity=opportunity,
                success=True,
                actual_profit=opportunity.expected_profit,  # Assume perfect execution
                orders=[],
            )

        # In production mode, the workflow executor should have already
        # placed the orders through the action nodes
        # Here we just confirm and return success

        # NOTE: In a full implementation, you might want to:
        # 1. Extract actual order IDs from workflow execution
        # 2. Monitor order fills
        # 3. Calculate actual profit

        return TradeResult(
            opportunity=opportunity,
            success=True,
            actual_profit=opportunity.expected_profit,
            orders=[],
            metadata={
                'workflow_execution': opportunity.metadata.get('workflow_execution')
            }
        )
