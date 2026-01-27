"""
Demo Mode Event Emitter

Generates mock events for demonstrating the dashboard without real trading.
This allows the frontend to be tested and demonstrated with realistic data.

Usage:
    python -m src.web.demo_mode --port 8080

Features:
- Generates mock bots with realistic statistics
- Emits periodic trade and metric events
- Simulates bot lifecycle events
- Provides realistic portfolio data
"""

import asyncio
import random
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class DemoDataGenerator:
    """Generates realistic mock data for demo mode."""

    STRATEGIES = [
        'binary_arbitrage',
        'cross_exchange_arbitrage',
        'triangular_arbitrage',
        'statistical_arbitrage',
        'momentum_trading',
        'market_making'
    ]

    PROVIDERS = [
        'polymarket',
        'binance',
        'kalshi',
        'coinbase',
        'kraken'
    ]

    MARKET_NAMES = [
        'BTC Price > $100k by Dec 2026',
        'ETH flips BTC by 2027',
        'Fed rate cut in Q1 2026',
        'Trump wins 2028 election',
        'SpaceX reaches Mars by 2030',
        'AI passes Turing test 2026'
    ]

    def __init__(self):
        self.bots: Dict[str, Dict] = {}
        self.trades: List[Dict] = []
        self.start_time = time.time()
        self._generate_initial_bots()

    def _generate_initial_bots(self):
        """Generate initial set of demo bots."""
        bot_configs = [
            ('bot_polymarket_arb', 'binary_arbitrage', 'polymarket', 'running'),
            ('bot_binance_stat', 'statistical_arbitrage', 'binance', 'running'),
            ('bot_cross_ex', 'cross_exchange_arbitrage', 'coinbase', 'paused'),
            ('bot_momentum', 'momentum_trading', 'kraken', 'stopped'),
        ]

        for bot_id, strategy, provider, status in bot_configs:
            self.bots[bot_id] = {
                'id': bot_id,
                'name': f"{strategy.replace('_', ' ').title()} Bot",
                'strategy': strategy,
                'provider': provider,
                'status': status,
                'balance': random.uniform(1000, 50000),
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'config': {
                    'position_size': random.choice([10, 25, 50, 100]),
                    'max_positions': random.randint(3, 10),
                    'min_edge': random.uniform(0.005, 0.02)
                },
                'metrics': {
                    'total_trades': random.randint(50, 500),
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': random.uniform(-500, 5000),
                    'win_rate': random.uniform(0.45, 0.75)
                },
                'strategies': [{
                    'id': f"{bot_id}_strategy_1",
                    'bot_id': bot_id,
                    'name': strategy,
                    'type': strategy,
                    'status': status,
                    'config': {},
                    'created_at': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                    'metrics': {
                        'total_executions': random.randint(50, 500),
                        'successful_executions': 0,
                        'failed_executions': 0,
                        'total_pnl': random.uniform(-500, 5000)
                    }
                }]
            }

            # Calculate win/loss breakdown
            total = self.bots[bot_id]['metrics']['total_trades']
            win_rate = self.bots[bot_id]['metrics']['win_rate']
            self.bots[bot_id]['metrics']['winning_trades'] = int(total * win_rate)
            self.bots[bot_id]['metrics']['losing_trades'] = total - int(total * win_rate)

    def generate_trade(self, bot_id: Optional[str] = None) -> Dict:
        """Generate a mock trade event."""
        if not bot_id:
            running_bots = [b for b in self.bots.values() if b['status'] == 'running']
            if not running_bots:
                return {}
            bot = random.choice(running_bots)
            bot_id = bot['id']
        else:
            bot = self.bots.get(bot_id, {})

        is_winning = random.random() < bot.get('metrics', {}).get('win_rate', 0.5)
        profit = random.uniform(5, 100) if is_winning else -random.uniform(5, 50)
        amount = random.uniform(10, 500)

        trade = {
            'id': str(uuid.uuid4())[:8],
            'bot_id': bot_id,
            'strategy_id': f"{bot_id}_strategy_1",
            'timestamp': datetime.now().isoformat(),
            'type': 'trade',
            'side': random.choice(['buy', 'sell']),
            'market': random.choice(self.MARKET_NAMES),
            'amount': round(amount, 2),
            'price': round(random.uniform(0.3, 0.7), 4),
            'profit': round(profit, 2),
            'status': 'completed',
            'duration_ms': random.randint(50, 2000)
        }

        self.trades.append(trade)
        if len(self.trades) > 1000:
            self.trades = self.trades[-1000:]

        # Update bot metrics
        if bot_id in self.bots:
            self.bots[bot_id]['metrics']['total_trades'] += 1
            self.bots[bot_id]['metrics']['total_pnl'] += profit
            if is_winning:
                self.bots[bot_id]['metrics']['winning_trades'] += 1
            else:
                self.bots[bot_id]['metrics']['losing_trades'] += 1

        return trade

    def generate_node_execution(self, bot_id: Optional[str] = None) -> Dict:
        """Generate a mock node execution event."""
        if not bot_id:
            running_bots = [b for b in self.bots.values() if b['status'] == 'running']
            if not running_bots:
                return {}
            bot = random.choice(running_bots)
            bot_id = bot['id']

        node_types = ['fetch_orderbook', 'calculate_edge', 'check_balance', 'place_order', 'monitor_fill']

        return {
            'type': 'node_execution',
            'bot_id': bot_id,
            'strategy_id': f"{bot_id}_strategy_1",
            'workflow_id': f"workflow_{bot_id}",
            'node_id': f"node_{random.randint(1, 10)}",
            'node_type': random.choice(node_types),
            'status': random.choice(['completed', 'completed', 'completed', 'running']),
            'timestamp': datetime.now().isoformat(),
            'duration_ms': random.randint(10, 500),
            'output': {
                'value': random.uniform(0, 100)
            }
        }

    def generate_bot_metrics(self, bot_id: str) -> Dict:
        """Generate bot metrics event."""
        bot = self.bots.get(bot_id, {})
        metrics = bot.get('metrics', {})

        return {
            'type': 'bot_metrics',
            'bot_id': bot_id,
            'timestamp': datetime.now().isoformat(),
            'balance': bot.get('balance', 0),
            'total_pnl': metrics.get('total_pnl', 0),
            'total_trades': metrics.get('total_trades', 0),
            'win_rate': metrics.get('win_rate', 0),
            'active_positions': random.randint(0, 5),
            'pending_orders': random.randint(0, 3)
        }

    def generate_strategy_metrics(self, strategy_id: str) -> Dict:
        """Generate strategy metrics event."""
        # Find bot for this strategy
        bot_id = strategy_id.replace('_strategy_1', '')
        bot = self.bots.get(bot_id, {})

        return {
            'type': 'strategy_metrics',
            'strategy_id': strategy_id,
            'bot_id': bot_id,
            'timestamp': datetime.now().isoformat(),
            'executions_per_hour': random.randint(5, 50),
            'avg_execution_time_ms': random.randint(100, 2000),
            'success_rate': random.uniform(0.8, 0.99),
            'total_pnl': bot.get('metrics', {}).get('total_pnl', 0)
        }

    def get_all_bots(self) -> List[Dict]:
        """Get all bots."""
        return list(self.bots.values())

    def get_bot(self, bot_id: str) -> Optional[Dict]:
        """Get a specific bot."""
        return self.bots.get(bot_id)

    def get_portfolio(self) -> Dict:
        """Get portfolio metrics."""
        total_balance = sum(b.get('balance', 0) for b in self.bots.values())
        total_pnl = sum(b.get('metrics', {}).get('total_pnl', 0) for b in self.bots.values())
        total_trades = sum(b.get('metrics', {}).get('total_trades', 0) for b in self.bots.values())
        active_bots = len([b for b in self.bots.values() if b['status'] == 'running'])

        return {
            'total_balance': round(total_balance, 2),
            'total_pnl': round(total_pnl, 2),
            'total_trades': total_trades,
            'winning_trades': sum(b.get('metrics', {}).get('winning_trades', 0) for b in self.bots.values()),
            'losing_trades': sum(b.get('metrics', {}).get('losing_trades', 0) for b in self.bots.values()),
            'win_rate': round(sum(b.get('metrics', {}).get('win_rate', 0) for b in self.bots.values()) / max(len(self.bots), 1), 4),
            'active_bots': active_bots,
            'total_bots': len(self.bots),
            'active_strategies': active_bots,
            'pnl_history': self._generate_pnl_history(),
            'updated_at': datetime.now().isoformat()
        }

    def _generate_pnl_history(self, days: int = 30) -> List[Dict]:
        """Generate PnL history for charts."""
        history = []
        cumulative = 0

        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i)).strftime('%Y-%m-%d')
            daily = random.uniform(-200, 500)
            cumulative += daily
            history.append({
                'date': date,
                'daily_pnl': round(daily, 2),
                'cumulative_pnl': round(cumulative, 2)
            })

        return history

    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Get recent trades."""
        return self.trades[-limit:]

    def start_bot(self, bot_id: str) -> bool:
        """Start a bot."""
        if bot_id in self.bots:
            self.bots[bot_id]['status'] = 'running'
            return True
        return False

    def stop_bot(self, bot_id: str) -> bool:
        """Stop a bot."""
        if bot_id in self.bots:
            self.bots[bot_id]['status'] = 'stopped'
            return True
        return False

    def pause_bot(self, bot_id: str) -> bool:
        """Pause a bot."""
        if bot_id in self.bots:
            current = self.bots[bot_id]['status']
            self.bots[bot_id]['status'] = 'paused' if current == 'running' else 'running'
            return True
        return False


class DemoModeServer:
    """
    Demo mode server that integrates with TradingBotWebServer.

    Replaces real bot manager with demo data generator.
    """

    def __init__(self, port: int = 8080, websocket_port: int = 8001):
        self.port = port
        self.websocket_port = websocket_port
        self.demo_data = DemoDataGenerator()
        self.running = False
        self.event_loop = None

    def patch_web_server(self, server):
        """
        Patch the web server to use demo data.

        Args:
            server: TradingBotWebServer instance
        """
        # Replace bot_manager methods with demo data methods
        server.bot_manager.get_all_bots = self.demo_data.get_all_bots
        server.bot_manager.get_bot = self.demo_data.get_bot
        server.bot_manager.start_bot = self.demo_data.start_bot
        server.bot_manager.stop_bot = self.demo_data.stop_bot
        server.bot_manager.pause_bot = self.demo_data.pause_bot
        server.bot_manager.get_aggregated_stats = lambda: {
            'total_profit': sum(b.get('metrics', {}).get('total_pnl', 0) for b in self.demo_data.bots.values() if b.get('metrics', {}).get('total_pnl', 0) > 0),
            'total_loss': abs(sum(b.get('metrics', {}).get('total_pnl', 0) for b in self.demo_data.bots.values() if b.get('metrics', {}).get('total_pnl', 0) < 0)),
            'total_trades': sum(b.get('metrics', {}).get('total_trades', 0) for b in self.demo_data.bots.values()),
            'winning_trades': sum(b.get('metrics', {}).get('winning_trades', 0) for b in self.demo_data.bots.values()),
            'losing_trades': sum(b.get('metrics', {}).get('losing_trades', 0) for b in self.demo_data.bots.values()),
            'win_rate': sum(b.get('metrics', {}).get('win_rate', 0) for b in self.demo_data.bots.values()) / max(len(self.demo_data.bots), 1)
        }

        # Add demo trades as recent_trades
        server.recent_trades = self.demo_data.trades

        logger.info("Demo mode patched into web server")

    def start_event_emitter(self, socketio):
        """
        Start background event emitter.

        Args:
            socketio: Socket.IO instance for emitting events
        """
        def emit_events():
            while self.running:
                try:
                    # Generate random events for running bots
                    running_bots = [b for b in self.demo_data.bots.values() if b['status'] == 'running']

                    if running_bots:
                        # Emit trade events (roughly every 5 seconds per bot)
                        if random.random() < 0.2:
                            bot = random.choice(running_bots)
                            trade = self.demo_data.generate_trade(bot['id'])
                            if trade:
                                socketio.emit('trade_executed', trade)
                                socketio.emit('workflow_event', {
                                    **trade,
                                    'type': 'execution_completed'
                                })

                        # Emit node execution events (more frequently)
                        if random.random() < 0.5:
                            bot = random.choice(running_bots)
                            node_event = self.demo_data.generate_node_execution(bot['id'])
                            if node_event:
                                socketio.emit('node_execution', node_event)
                                socketio.emit('workflow_event', node_event)

                        # Emit bot metrics (every few seconds)
                        if random.random() < 0.3:
                            for bot in running_bots:
                                metrics = self.demo_data.generate_bot_metrics(bot['id'])
                                socketio.emit('bot_metrics', metrics)

                    # Update bot list periodically
                    if random.random() < 0.1:
                        bots = self.demo_data.get_all_bots()
                        socketio.emit('bot_list_update', bots)

                    time.sleep(1)

                except Exception as e:
                    logger.error(f"Error in event emitter: {e}")
                    time.sleep(5)

        self.running = True
        thread = threading.Thread(target=emit_events, daemon=True)
        thread.start()
        logger.info("Demo event emitter started")

    def stop(self):
        """Stop the demo mode server."""
        self.running = False


def run_demo_server(port: int = 8080, websocket_port: int = 8001):
    """
    Run the web server in demo mode.

    Args:
        port: HTTP server port
        websocket_port: WebSocket server port (not used in this simple demo)
    """
    from .server import create_web_server

    # Create web server
    server = create_web_server({
        'port': port,
        'host': '0.0.0.0'
    })

    # Create demo mode
    demo = DemoModeServer(port, websocket_port)
    demo.patch_web_server(server)
    demo.start_event_emitter(server.socketio)

    logger.info(f"Starting demo mode server on port {port}")
    logger.info("Demo mode active - using simulated data")

    # Run server
    server.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BrokeDancer Demo Mode")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--ws-port", type=int, default=8001, help="WebSocket server port")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    run_demo_server(args.port, args.ws_port)
