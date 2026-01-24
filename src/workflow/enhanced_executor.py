"""
Enhanced Workflow Executor with Infrastructure Integration

Extends the base WorkflowExecutor with Week 2 infrastructure:
- Event emission to event bus
- Correlation ID tracking
- Emergency controller checks
- State persistence
- Circuit breakers and resilience
- Structured logging
"""

import asyncio
import time
import uuid
from typing import Any, Dict, Optional
from datetime import datetime

from .executor import WorkflowExecutor as BaseWorkflowExecutor
from src.infrastructure.factory import Infrastructure
from src.infrastructure.logging import get_logger, set_correlation_id, get_correlation_id
from src.infrastructure.resilience import with_retry, with_timeout
from src.infrastructure.emergency import EmergencyHalted


logger = get_logger(__name__)


class EnhancedWorkflowExecutor(BaseWorkflowExecutor):
    """
    Enhanced workflow executor with full infrastructure integration.

    Adds to base executor:
    - Real-time event emission
    - Correlation ID tracking
    - Emergency halt checks
    - State persistence
    - Circuit breakers for external calls
    - Structured logging with context

    Usage:
        # Create infrastructure
        infra = await Infrastructure.create("development")

        # Create enhanced executor
        executor = EnhancedWorkflowExecutor(
            workflow=workflow_definition,
            infra=infra,
            workflow_id="arb_btc_001",
            bot_id="bot_001",
            strategy_id="arb_btc"
        )

        # Initialize and execute
        await executor.initialize()
        result = await executor.execute()

        # Events are automatically emitted to event bus
        # Correlation ID is set for log tracing
        # Emergency state is checked before execution
    """

    def __init__(
        self,
        workflow: Dict[str, Any],
        infra: Infrastructure,
        workflow_id: str,
        bot_id: Optional[str] = None,
        strategy_id: Optional[str] = None
    ):
        """
        Initialize enhanced workflow executor.

        Args:
            workflow: Workflow definition
            infra: Infrastructure instance
            workflow_id: Unique workflow identifier
            bot_id: Optional bot identifier
            strategy_id: Optional strategy identifier
        """
        super().__init__(workflow)

        self.infra = infra
        self.workflow_id = workflow_id
        self.bot_id = bot_id
        self.strategy_id = strategy_id
        self.execution_id: Optional[str] = None

        # Create circuit breaker for external API calls
        self.api_breaker = infra.create_circuit_breaker(
            f"workflow_{workflow_id}_api",
            failure_threshold=5
        )

        logger.info(
            "enhanced_workflow_executor_created",
            workflow_id=workflow_id,
            bot_id=bot_id,
            strategy_id=strategy_id,
            node_count=len(workflow.get('blocks', []))
        )

    async def initialize(self):
        """Initialize workflow executor with infrastructure checks."""
        # Check emergency state before initialization
        try:
            await self.infra.emergency.assert_can_operate()
        except EmergencyHalted as e:
            logger.error(
                "workflow_initialization_blocked",
                workflow_id=self.workflow_id,
                reason=str(e)
            )
            raise

        # Call base initialization
        await super().initialize()

        logger.info(
            "workflow_initialized",
            workflow_id=self.workflow_id,
            execution_order=self.execution_order
        )

    async def execute(self) -> Dict[str, Any]:
        """
        Execute workflow with full infrastructure integration.

        Returns:
            Execution result with status, duration, and outputs
        """
        # Generate execution ID for correlation tracking
        self.execution_id = f"exec_{self.workflow_id}_{uuid.uuid4().hex[:8]}"
        set_correlation_id(self.execution_id)

        # Bind logging context
        log = logger.bind(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            bot_id=self.bot_id,
            strategy_id=self.strategy_id
        )

        # Save initial execution state
        await self._persist_execution_state("running")

        # Emit execution_started event
        await self._emit_event({
            "type": "execution_started",
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "bot_id": self.bot_id,
            "strategy_id": self.strategy_id,
            "timestamp": datetime.utcnow().isoformat(),
            "node_count": len(self.execution_order)
        })

        log.info(
            "workflow_execution_started",
            node_count=len(self.execution_order)
        )

        try:
            # Check emergency state before execution
            await self.infra.emergency.assert_can_trade()

            # Execute workflow
            result = await self._execute_with_resilience()

            # Emit execution_completed event
            await self._emit_event({
                "type": "execution_completed",
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": result['status'],
                "duration_ms": result['duration']
            })

            log.info(
                "workflow_execution_completed",
                status=result['status'],
                duration_ms=result['duration'],
                node_count=len(result.get('results', []))
            )

            # Save final state
            await self._persist_execution_state(result['status'])
            await self._persist_execution_result(result)

            return result

        except EmergencyHalted as e:
            # Emergency halt triggered
            log.critical(
                "workflow_execution_halted",
                reason=str(e),
                emergency_state=e.state.value
            )

            await self._emit_event({
                "type": "execution_halted",
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": str(e)
            })

            await self._persist_execution_state("halted")

            raise

        except Exception as e:
            # Unexpected error
            log.error(
                "workflow_execution_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )

            await self._emit_event({
                "type": "execution_failed",
                "execution_id": self.execution_id,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__
            })

            await self._persist_execution_state("failed")

            raise

    async def _execute_with_resilience(self) -> Dict[str, Any]:
        """Execute workflow with resilience patterns."""
        self.start_time = time.time()
        self.is_running = True
        errors = []
        results = []

        try:
            # Execute nodes in topological order
            for node_id in self.execution_order:
                node = self._get_node(node_id)
                if not node:
                    logger.error("node_not_found", node_id=node_id)
                    continue

                # Check emergency state before each node
                await self.infra.emergency.assert_can_trade()

                try:
                    # Emit node_started event
                    await self._emit_node_event(node_id, "node_started")

                    # Get inputs
                    inputs = await self._get_node_inputs(node_id)

                    # Execute node with resilience
                    node_start = time.time()
                    outputs = await self._execute_node_with_resilience(node, inputs)
                    node_duration = (time.time() - node_start) * 1000

                    # Store outputs
                    self.node_outputs[node_id] = outputs

                    # Emit node_completed event
                    await self._emit_node_event(
                        node_id,
                        "node_completed",
                        duration_ms=node_duration,
                        outputs=outputs,
                        status="success"
                    )

                    logger.debug(
                        "node_executed",
                        node_id=node_id,
                        node_name=node['name'],
                        duration_ms=round(node_duration, 2)
                    )

                    results.append({
                        'nodeId': node_id,
                        'nodeName': node['name'],
                        'nodeType': node['category'],
                        'output': outputs,
                        'duration': node_duration
                    })

                except EmergencyHalted:
                    # Propagate emergency halt
                    raise

                except Exception as e:
                    # Node execution failed
                    logger.error(
                        "node_execution_failed",
                        node_id=node_id,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True
                    )

                    # Emit node_failed event
                    await self._emit_node_event(
                        node_id,
                        "node_failed",
                        error=str(e),
                        error_type=type(e).__name__
                    )

                    errors.append({
                        'nodeId': node_id,
                        'error': str(e)
                    })

            duration = (time.time() - self.start_time) * 1000
            status = 'completed' if not errors else 'completed_with_errors'

            return {
                'status': status,
                'duration': duration,
                'results': results,
                'errors': errors
            }

        finally:
            self.is_running = False

    async def _execute_node_with_resilience(
        self,
        node: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute node with resilience patterns.

        Adds:
        - Timeout handling
        - Retry logic for transient failures
        - Circuit breaker for external calls
        """
        category = node['category']
        node_timeout = node.get('timeout', 30.0)

        # For provider nodes, use circuit breaker and retry
        if category == 'providers':
            @with_retry(
                max_attempts=self.infra.config.resilience.retry_max_attempts,
                min_wait_seconds=self.infra.config.resilience.retry_min_wait_seconds,
                retry_on=(ConnectionError, TimeoutError)
            )
            @with_timeout(node_timeout)
            async def execute_provider():
                return await self.api_breaker.call(
                    super(EnhancedWorkflowExecutor, self)._execute_provider_node,
                    node,
                    inputs
                )

            return await execute_provider()

        # For other nodes, just add timeout
        @with_timeout(node_timeout)
        async def execute_regular():
            return await super(EnhancedWorkflowExecutor, self)._execute_node(node, inputs)

        return await execute_regular()

    async def _emit_event(self, event: Dict[str, Any]):
        """
        Emit event to event bus.

        Args:
            event: Event data
        """
        try:
            await self.infra.events.publish("workflow_events", event)
        except Exception as e:
            logger.error(
                "event_emission_failed",
                event_type=event.get('type'),
                error=str(e)
            )

    async def _emit_node_event(
        self,
        node_id: str,
        event_type: str,
        **extra_data
    ):
        """
        Emit node-specific event.

        Args:
            node_id: Node identifier
            event_type: Event type (node_started, node_completed, node_failed)
            **extra_data: Additional event data
        """
        node = self._get_node(node_id)
        event = {
            "type": event_type,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "bot_id": self.bot_id,
            "strategy_id": self.strategy_id,
            "node_id": node_id,
            "node_name": node['name'] if node else "unknown",
            "node_category": node['category'] if node else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            **extra_data
        }

        await self._emit_event(event)

    async def _persist_execution_state(self, status: str):
        """
        Persist current execution state.

        Args:
            status: Execution status (running, completed, failed, halted)
        """
        try:
            await self.infra.state.set(
                f"workflow:{self.workflow_id}:execution:{self.execution_id}:status",
                status
            )

            await self.infra.state.set(
                f"workflow:{self.workflow_id}:latest_execution",
                self.execution_id
            )

        except Exception as e:
            logger.error(
                "state_persistence_failed",
                execution_id=self.execution_id,
                error=str(e)
            )

    async def _persist_execution_result(self, result: Dict[str, Any]):
        """
        Persist execution result.

        Args:
            result: Execution result
        """
        try:
            await self.infra.state.set(
                f"workflow:{self.workflow_id}:execution:{self.execution_id}:result",
                result
            )
        except Exception as e:
            logger.error(
                "result_persistence_failed",
                execution_id=self.execution_id,
                error=str(e)
            )

    async def get_execution_history(self, limit: int = 10) -> list:
        """
        Get execution history for this workflow.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of execution IDs and statuses
        """
        # TODO: Implement pagination
        # For now, just return the latest execution
        latest_execution_id = await self.infra.state.get(
            f"workflow:{self.workflow_id}:latest_execution"
        )

        if not latest_execution_id:
            return []

        status = await self.infra.state.get(
            f"workflow:{self.workflow_id}:execution:{latest_execution_id}:status"
        )

        return [{
            "execution_id": latest_execution_id,
            "status": status
        }]
