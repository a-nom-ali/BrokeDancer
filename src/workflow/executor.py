"""
Workflow Executor

Executes workflow-based bots in real-time without code generation.
Uses topological sort to determine execution order and executes nodes sequentially.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Executes workflow-based bots in real-time."""

    def __init__(self, workflow: Dict[str, Any]):
        """
        Initialize workflow executor.

        Args:
            workflow: Workflow definition with blocks and connections
                {
                    'blocks': [...],
                    'connections': [...]
                }
        """
        self.workflow = workflow
        self.providers = {}  # provider_id → provider instance
        self.node_outputs = {}  # node_id → output values
        self.execution_order = []  # Topologically sorted node IDs
        self.start_time = 0
        self.is_running = False

    async def initialize(self):
        """Initialize all provider nodes and compute execution order."""
        logger.info("Initializing workflow executor")

        # 1. Initialize provider nodes
        for block in self.workflow['blocks']:
            if block['category'] == 'providers':
                await self._initialize_provider(block)

        # 2. Compute topological execution order
        self.execution_order = self._topological_sort()
        logger.info(f"Execution order: {self.execution_order}")

    async def _initialize_provider(self, block: Dict[str, Any]):
        """
        Initialize a provider node.

        Supports all 8 providers:
        - polymarket: Prediction market (BTC UP/DOWN)
        - luno: Cryptocurrency exchange (BTC/ZAR)
        - kalshi: US-regulated prediction market
        - binance: World's largest crypto exchange
        - coinbase: Largest US-based exchange
        - bybit: Leading derivatives exchange
        - kraken: Trusted exchange with deep liquidity
        - dydx: Decentralized perpetuals exchange

        Args:
            block: Provider block definition
        """
        provider_type = block['type']
        profile_id = block['properties'].get('profile_id')

        if not profile_id:
            logger.warning(f"Provider {block['id']} has no profile_id, skipping initialization")
            return

        logger.info(f"Initializing {provider_type} provider with profile {profile_id}")

        # TODO: Load actual provider from profile manager
        # For now, store mock provider reference
        # Future implementation:
        # from ..providers.factory import create_provider
        # profile = await self.profile_manager.get_profile(profile_id)
        # credentials = profile['credentials']
        # provider_instance = create_provider(provider_type, credentials)
        # await provider_instance.initialize()

        # Store provider reference
        self.providers[block['id']] = {
            'type': provider_type,
            'profile_id': profile_id,
            'enabled_endpoints': block['properties'].get('enabled_endpoints', [])
        }

        logger.debug(f"Provider {provider_type} initialized with endpoints: {self.providers[block['id']]['enabled_endpoints']}")

    def _topological_sort(self) -> List[str]:
        """
        Compute execution order based on node dependencies using Kahn's algorithm.

        Returns:
            List of node IDs in execution order
        """
        # Build dependency graph
        graph = defaultdict(list)  # node -> [dependent_nodes]
        in_degree = defaultdict(int)  # node -> number of dependencies

        # Get all node IDs
        all_nodes = {block['id'] for block in self.workflow['blocks']}

        # Initialize in_degree for all nodes
        for node_id in all_nodes:
            in_degree[node_id] = 0

        # Build graph from connections
        for conn in self.workflow.get('connections', []):
            from_node = conn['from']['blockId']
            to_node = conn['to']['blockId']

            graph[from_node].append(to_node)
            in_degree[to_node] += 1

        # Kahn's algorithm
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(all_nodes):
            raise ValueError("Workflow contains cycles - cannot execute")

        return result

    async def execute(self) -> Dict[str, Any]:
        """
        Execute workflow once.

        Returns:
            Execution result with status, duration, and node outputs
        """
        self.start_time = time.time()
        self.is_running = True
        errors = []
        results = []

        try:
            logger.info("Starting workflow execution")

            # Execute nodes in topological order
            for node_id in self.execution_order:
                node = self._get_node(node_id)
                if not node:
                    logger.error(f"Node {node_id} not found in workflow")
                    continue

                try:
                    # Get inputs from connected nodes
                    inputs = await self._get_node_inputs(node_id)

                    # Execute node based on category
                    node_start = time.time()
                    outputs = await self._execute_node(node, inputs)
                    node_duration = (time.time() - node_start) * 1000  # ms

                    # Store outputs for downstream nodes
                    self.node_outputs[node_id] = outputs

                    # Log execution
                    logger.debug(f"Executed {node['name']} ({node_id}): {outputs}")

                    results.append({
                        'nodeId': node_id,
                        'nodeName': node['name'],
                        'nodeType': node['category'],
                        'output': outputs,
                        'duration': node_duration
                    })

                except Exception as e:
                    logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
                    errors.append({
                        'nodeId': node_id,
                        'error': str(e)
                    })

            duration = (time.time() - self.start_time) * 1000  # ms
            status = 'completed' if not errors else 'completed_with_errors'

            return {
                'status': status,
                'duration': duration,
                'results': results,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            duration = (time.time() - self.start_time) * 1000

            return {
                'status': 'failed',
                'duration': duration,
                'error': str(e),
                'results': results,
                'errors': errors
            }

        finally:
            self.is_running = False

    async def _execute_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single node based on its category.

        Args:
            node: Node definition
            inputs: Input values from connected nodes

        Returns:
            Output values from node execution
        """
        category = node['category']

        if category == 'providers':
            return await self._execute_provider_node(node, inputs)
        elif category == 'triggers':
            return await self._execute_trigger_node(node, inputs)
        elif category == 'conditions':
            return await self._execute_condition_node(node, inputs)
        elif category == 'actions':
            return await self._execute_action_node(node, inputs)
        elif category == 'risk':
            return await self._execute_risk_node(node, inputs)
        else:
            raise ValueError(f"Unknown node category: {category}")

    async def _execute_provider_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute provider node (fetch live data).

        Supports all 8 providers with consistent output interface:
        - polymarket 🎯: Prediction market prices
        - luno 🚀: BTC/ZAR spot prices
        - kalshi 🎲: US prediction market prices
        - binance 🌐: Global crypto prices
        - coinbase 🇺🇸: US-based crypto prices
        - bybit 📊: Derivatives prices
        - kraken 🐙: Multi-asset prices
        - dydx ⚡: DeFi perpetuals prices

        Args:
            node: Provider node definition
            inputs: Input values (providers have no inputs)

        Returns:
            Provider outputs (price_feed, balance, positions, orderbook)
        """
        provider_id = node['id']
        provider = self.providers.get(provider_id)

        if not provider:
            logger.warning(f"Provider {provider_id} not initialized")
            return {}

        provider_type = provider['type']
        enabled_endpoints = provider['enabled_endpoints']
        outputs = {}

        # Mock data for now - will be replaced with actual provider calls
        # Future implementation will call provider-specific methods:
        # provider_instance = self.providers[provider_id]['instance']
        # outputs['price_feed'] = await provider_instance.get_current_price()

        if 'price_feed' in enabled_endpoints:
            outputs['price_feed'] = 0.52  # Mock price
            logger.debug(f"{provider_type} price_feed: 0.52")

        if 'balance' in enabled_endpoints:
            outputs['balance'] = 1000.0  # Mock balance
            logger.debug(f"{provider_type} balance: 1000.0")

        if 'positions' in enabled_endpoints:
            outputs['positions'] = []  # Mock positions
            logger.debug(f"{provider_type} positions: []")

        if 'orderbook' in enabled_endpoints:
            outputs['orderbook'] = {
                'bids': [[0.51, 100]],
                'asks': [[0.53, 100]]
            }
            logger.debug(f"{provider_type} orderbook: 2 levels")

        logger.info(f"Provider {provider_type} executed with {len(outputs)} outputs")
        return outputs

    async def _execute_trigger_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trigger node."""
        # Mock implementation
        return {'signal': True}

    async def _execute_condition_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute condition node (boolean evaluation).

        Args:
            node: Condition node definition
            inputs: Input values from connected nodes

        Returns:
            Condition outputs (true/false branches, or boolean result)
        """
        node_type = node['type']

        if node_type == 'threshold':
            value = inputs.get('value', 0)
            min_val = inputs.get('min', float('-inf'))
            max_val = inputs.get('max', float('inf'))

            passed = min_val <= value <= max_val
            return {'pass': passed}

        elif node_type == 'compare':
            value1 = inputs.get('value1', 0)
            value2 = inputs.get('value2', 0)
            operator = inputs.get('operator', '==')

            if operator == '==':
                result = value1 == value2
            elif operator == '>':
                result = value1 > value2
            elif operator == '<':
                result = value1 < value2
            elif operator == '>=':
                result = value1 >= value2
            elif operator == '<=':
                result = value1 <= value2
            elif operator == '!=':
                result = value1 != value2
            else:
                result = False

            return {'result': result}

        elif node_type == 'and':
            input1 = inputs.get('input1', False)
            input2 = inputs.get('input2', False)
            return {'output': bool(input1 and input2)}

        elif node_type == 'or':
            input1 = inputs.get('input1', False)
            input2 = inputs.get('input2', False)
            return {'output': bool(input1 or input2)}

        elif node_type == 'if':
            condition = inputs.get('condition', False)
            return {
                'true': bool(condition),
                'false': not bool(condition)
            }

        return {}

    async def _execute_action_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action node (buy, sell, cancel, notify).

        Args:
            node: Action node definition
            inputs: Input values from connected nodes

        Returns:
            Action outputs (order, done, sent)
        """
        node_type = node['type']

        if node_type == 'buy' or node_type == 'sell':
            signal = inputs.get('signal', False)
            amount = inputs.get('amount', 0)

            if not signal:
                return {'order': None}

            # Mock order execution
            order = {
                'side': node_type,
                'amount': amount,
                'price': 0.52,
                'status': 'filled'
            }
            logger.info(f"Executed {node_type} order: {order}")
            return {'order': order}

        elif node_type == 'cancel':
            signal = inputs.get('signal', False)
            if signal:
                logger.info("Cancelled orders")
                return {'done': True}
            return {'done': False}

        elif node_type == 'notify':
            signal = inputs.get('signal', False)
            message = inputs.get('message', '')
            if signal:
                logger.info(f"Notification: {message}")
                return {'sent': True}
            return {'sent': False}

        return {}

    async def _execute_risk_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk management node."""
        # Mock implementation
        return {'trigger': False}

    async def _get_node_inputs(self, node_id: str) -> Dict[str, Any]:
        """
        Get input values for a node from connected nodes.

        Args:
            node_id: ID of node to get inputs for

        Returns:
            Dictionary mapping input names to values
        """
        inputs = {}

        for conn in self.workflow.get('connections', []):
            to_node_id = conn['to']['blockId']

            if to_node_id == node_id:
                from_node_id = conn['from']['blockId']
                from_output_index = conn['from']['index']

                # Get the output name from the from_node
                from_node = self._get_node(from_node_id)
                if not from_node:
                    continue

                from_output_name = from_node['outputs'][from_output_index]['name']

                # Get value from stored outputs
                if from_node_id in self.node_outputs:
                    value = self.node_outputs[from_node_id].get(from_output_name)

                    # Get the input name from to_node
                    to_node = self._get_node(to_node_id)
                    if to_node and to_node.get('inputs'):
                        to_input_index = conn['to']['index']
                        to_input_name = to_node['inputs'][to_input_index]['name']
                        inputs[to_input_name] = value

        return inputs

    def _get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node definition by ID.

        Args:
            node_id: Node ID to find

        Returns:
            Node definition or None if not found
        """
        for block in self.workflow['blocks']:
            if block['id'] == node_id:
                return block
        return None

    def stop(self):
        """Stop workflow execution."""
        logger.info("Stopping workflow execution")
        self.is_running = False
