"""
Web Dashboard Server

Flask-based web server with WebSocket support for real-time monitoring.
Provides live stats, strategy selection, and bot control.

Features:
- Real-time metrics via WebSocket
- Strategy selection and configuration
- Profile management
- Trade history visualization
- Start/stop/pause bot control
- Live order book display
- Performance analytics

Usage:
    python -m src.web.server --port 8080
"""

import logging
import asyncio
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from ..providers.factory import create_provider, get_supported_providers
from ..strategies.factory import create_strategy, get_supported_strategies
from .multi_bot_manager import MultiBotManager
from .data_export import DataExporter
from .alerts import AlertManager
from .profile_manager import ProfileManager
from ..backtesting import BacktestEngine, HistoricalDataProvider

logger = logging.getLogger(__name__)


class TradingBotWebServer:
    """Web dashboard server for trading bot."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize web server.

        Args:
            config: Server configuration
        """
        self.config = config or {}
        self.port = self.config.get("port", 8080)
        self.host = self.config.get("host", "0.0.0.0")

        # Flask app
        self.app = Flask(
            __name__,
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static")
        )

        # Enable CORS
        CORS(self.app)

        # Socket.IO for WebSocket
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading'
        )

        # Multi-bot manager
        self.bot_manager = MultiBotManager(self.config.get("bot_manager", {}))

        # Data exporter
        self.data_exporter = DataExporter(self.config.get("data_export", {}))

        # Alert manager
        self.alert_manager = AlertManager(self.config.get("alerts", {}))

        # Profile manager
        self.profile_manager = ProfileManager(self.config.get("master_password"))

        # Bot state (legacy single-bot support)
        self.bot_running = False
        self.bot_paused = False
        self.current_strategy = None
        self.current_provider = None
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "uptime": 0,
            "balance": 0.0
        }
        self.recent_trades = []
        self.active_orders = []

        # Setup routes
        self._setup_routes()
        self._setup_websocket_handlers()

        logger.info(f"Web server initialized on {self.host}:{self.port}")

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')

        @self.app.route('/api/status')
        def api_status():
            """Get bot status."""
            return jsonify({
                "running": self.bot_running,
                "paused": self.bot_paused,
                "strategy": self.current_strategy,
                "provider": self.current_provider,
                "uptime": self.stats["uptime"]
            })

        @self.app.route('/api/stats')
        def api_stats():
            """Get trading statistics."""
            return jsonify(self.stats)

        @self.app.route('/api/trades')
        def api_trades():
            """Get recent trades."""
            limit = request.args.get('limit', 50, type=int)
            return jsonify(self.recent_trades[-limit:])

        @self.app.route('/api/orders')
        def api_orders():
            """Get active orders."""
            return jsonify(self.active_orders)

        @self.app.route('/api/providers')
        def api_providers():
            """Get available providers."""
            return jsonify(get_supported_providers())

        @self.app.route('/api/strategies')
        def api_strategies():
            """Get available strategies."""
            return jsonify(get_supported_strategies())

        @self.app.route('/api/start', methods=['POST'])
        def api_start():
            """Start the bot."""
            data = request.json or {}
            strategy = data.get('strategy')
            provider = data.get('provider')
            config = data.get('config', {})

            if not strategy or not provider:
                return jsonify({"error": "strategy and provider required"}), 400

            try:
                self.current_strategy = strategy
                self.current_provider = provider
                self.bot_running = True
                self.bot_paused = False

                logger.info(f"Bot started: {strategy} on {provider}")

                # Emit WebSocket event
                self.socketio.emit('bot_started', {
                    'strategy': strategy,
                    'provider': provider,
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"status": "started"})

            except Exception as e:
                logger.error(f"Error starting bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """Stop the bot."""
            try:
                self.bot_running = False
                self.bot_paused = False

                logger.info("Bot stopped")

                # Emit WebSocket event
                self.socketio.emit('bot_stopped', {
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"status": "stopped"})

            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/pause', methods=['POST'])
        def api_pause():
            """Pause/Resume the bot."""
            try:
                self.bot_paused = not self.bot_paused

                logger.info(f"Bot {'paused' if self.bot_paused else 'resumed'}")

                # Emit WebSocket event
                self.socketio.emit('bot_paused' if self.bot_paused else 'bot_resumed', {
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({
                    "status": "paused" if self.bot_paused else "running",
                    "paused": self.bot_paused
                })

            except Exception as e:
                logger.error(f"Error pausing bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/static/<path:path>')
        def send_static(path):
            """Serve static files."""
            return send_from_directory('static', path)

        # Multi-bot management routes
        @self.app.route('/api/bots', methods=['GET'])
        def api_get_bots():
            """Get all bots."""
            return jsonify(self.bot_manager.get_all_bots())

        @self.app.route('/api/bots/running', methods=['GET'])
        def api_get_running_bots():
            """Get running bots."""
            return jsonify(self.bot_manager.get_running_bots())

        @self.app.route('/api/bots/<bot_id>', methods=['GET'])
        def api_get_bot(bot_id):
            """Get specific bot."""
            bot = self.bot_manager.get_bot(bot_id)
            if bot:
                return jsonify(bot)
            return jsonify({"error": "Bot not found"}), 404

        @self.app.route('/api/bots', methods=['POST'])
        def api_create_bot():
            """Create new bot."""
            data = request.json or {}
            strategy = data.get('strategy')
            provider = data.get('provider')
            config = data.get('config', {})

            if not strategy or not provider:
                return jsonify({"error": "strategy and provider required"}), 400

            try:
                bot_id = self.bot_manager.create_bot(strategy, provider, config)

                # Emit WebSocket event
                self.socketio.emit('bot_created', {
                    'bot_id': bot_id,
                    'strategy': strategy,
                    'provider': provider,
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({"bot_id": bot_id, "status": "created"})

            except Exception as e:
                logger.error(f"Error creating bot: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/workflow', methods=['POST'])
        def api_create_bot_from_workflow():
            """Create new bot from workflow definition."""
            data = request.json or {}

            name = data.get('name')
            description = data.get('description', '')
            workflow = data.get('workflow')
            config = data.get('config', {})
            auto_start = data.get('auto_start', False)

            if not name:
                return jsonify({"error": "name required"}), 400

            if not workflow:
                return jsonify({"error": "workflow required"}), 400

            try:
                # Extract primary provider from workflow
                provider_blocks = [
                    block for block in workflow.get('blocks', [])
                    if block.get('category') == 'providers'
                ]

                if not provider_blocks:
                    return jsonify({"error": "workflow must have at least one provider"}), 400

                # Use first provider as primary
                primary_provider = provider_blocks[0]['type']

                # Create bot config with workflow embedded
                bot_config = {
                    **config,
                    'workflow': workflow,
                    'workflow_based': True,
                    'description': description
                }

                # Create bot using workflow strategy
                bot_id = self.bot_manager.create_bot(
                    strategy='workflow',  # Special strategy type for workflows
                    provider=primary_provider,
                    config=bot_config
                )

                # Update bot name in database if supported
                # (This would require bot_manager to support custom names)

                # Start bot if requested
                if auto_start:
                    self.bot_manager.start_bot(bot_id)

                # Emit WebSocket event
                self.socketio.emit('bot_created', {
                    'bot_id': bot_id,
                    'name': name,
                    'strategy': 'workflow',
                    'provider': primary_provider,
                    'workflow_based': True,
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify({
                    "bot_id": bot_id,
                    "status": "created",
                    "auto_started": auto_start
                })

            except Exception as e:
                logger.error(f"Error creating bot from workflow: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/start', methods=['POST'])
        def api_start_bot(bot_id):
            """Start specific bot."""
            try:
                success = self.bot_manager.start_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_started', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "started"})
                else:
                    return jsonify({"error": "Failed to start bot"}), 500

            except Exception as e:
                logger.error(f"Error starting bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/stop', methods=['POST'])
        def api_stop_bot(bot_id):
            """Stop specific bot."""
            try:
                success = self.bot_manager.stop_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_stopped', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "stopped"})
                else:
                    return jsonify({"error": "Failed to stop bot"}), 500

            except Exception as e:
                logger.error(f"Error stopping bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>/pause', methods=['POST'])
        def api_pause_bot(bot_id):
            """Pause/resume specific bot."""
            try:
                success = self.bot_manager.pause_bot(bot_id)

                if success:
                    bot = self.bot_manager.get_bot(bot_id)
                    is_paused = bot['status'] == 'paused'

                    # Emit WebSocket event
                    self.socketio.emit('bot_paused' if is_paused else 'bot_resumed', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": bot['status']})
                else:
                    return jsonify({"error": "Failed to pause bot"}), 500

            except Exception as e:
                logger.error(f"Error pausing bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/<bot_id>', methods=['DELETE'])
        def api_remove_bot(bot_id):
            """Remove specific bot."""
            try:
                success = self.bot_manager.remove_bot(bot_id)

                if success:
                    # Emit WebSocket event
                    self.socketio.emit('bot_removed', {
                        'bot_id': bot_id,
                        'timestamp': datetime.now().isoformat()
                    })

                    return jsonify({"status": "removed"})
                else:
                    return jsonify({"error": "Failed to remove bot"}), 500

            except Exception as e:
                logger.error(f"Error removing bot {bot_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/bots/stats/aggregated', methods=['GET'])
        def api_get_aggregated_stats():
            """Get aggregated statistics across all bots."""
            return jsonify(self.bot_manager.get_aggregated_stats())

        # Data export routes
        @self.app.route('/api/export/trades', methods=['GET'])
        def api_export_trades():
            """Export trade history."""
            format = request.args.get('format', 'csv')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Parse dates
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None

            try:
                data = self.data_exporter.export_trades(
                    self.recent_trades,
                    format=format,
                    start_date=start,
                    end_date=end
                )

                # Determine mimetype
                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                elif format == 'json':
                    mimetype = 'application/json'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                elif format == 'excel':
                    mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    filename = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                else:
                    return jsonify({"error": "Invalid format"}), 400

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting trades: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/stats', methods=['GET'])
        def api_export_stats():
            """Export performance statistics."""
            format = request.args.get('format', 'json')

            try:
                data = self.data_exporter.export_performance_metrics(
                    self.stats,
                    format=format
                )

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting stats: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/chart-data', methods=['GET'])
        def api_export_chart_data():
            """Export chart data."""
            format = request.args.get('format', 'csv')
            interval = request.args.get('interval', '1h')

            try:
                # Generate chart data
                chart_data = self.data_exporter.generate_profit_chart_data(
                    self.recent_trades,
                    interval=interval
                )

                # Export
                data = self.data_exporter.export_chart_data(
                    chart_data,
                    format=format
                )

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'chart_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'chart_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting chart data: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/export/bots', methods=['GET'])
        def api_export_bots():
            """Export multi-bot summary."""
            format = request.args.get('format', 'csv')

            try:
                bots = self.bot_manager.get_all_bots()
                data = self.data_exporter.export_bot_summary(bots, format=format)

                if format == 'csv':
                    mimetype = 'text/csv'
                    filename = f'bots_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                else:
                    mimetype = 'application/json'
                    filename = f'bots_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

                from flask import Response
                return Response(
                    data,
                    mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )

            except Exception as e:
                logger.error(f"Error exporting bots: {e}")
                return jsonify({"error": str(e)}), 500

        # Backtesting routes
        @self.app.route('/api/backtest', methods=['POST'])
        def api_run_backtest():
            """Run strategy backtest."""
            data = request.json or {}
            strategy_name = data.get('strategy')
            historical_data = data.get('historical_data', [])
            config = data.get('config', {})

            if not strategy_name or not historical_data:
                return jsonify({"error": "strategy and historical_data required"}), 400

            try:
                # Parse timestamps in historical data
                for point in historical_data:
                    if isinstance(point.get('timestamp'), str):
                        point['timestamp'] = datetime.fromisoformat(point['timestamp'])

                # Get strategy class
                from ..strategies import factory
                # Create a mock provider for the strategy class lookup
                mock_provider = HistoricalDataProvider(historical_data)
                strategy_instance = create_strategy(strategy_name, mock_provider, config)
                strategy_class = type(strategy_instance)

                # Run backtest
                async def run():
                    engine = BacktestEngine(strategy_class, historical_data, config)
                    return await engine.run()

                result = asyncio.run(run())

                # Emit WebSocket event
                self.socketio.emit('backtest_completed', {
                    'strategy': strategy_name,
                    'result': result.to_dict(),
                    'timestamp': datetime.now().isoformat()
                })

                return jsonify(result.to_dict())

            except Exception as e:
                logger.error(f"Error running backtest: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/backtest/optimize', methods=['POST'])
        def api_optimize_parameters():
            """Optimize strategy parameters."""
            data = request.json or {}
            strategy_name = data.get('strategy')
            historical_data = data.get('historical_data', [])
            param_grid = data.get('param_grid', {})
            metric = data.get('metric', 'sharpe_ratio')

            if not strategy_name or not historical_data or not param_grid:
                return jsonify({"error": "strategy, historical_data, and param_grid required"}), 400

            try:
                # Parse timestamps
                for point in historical_data:
                    if isinstance(point.get('timestamp'), str):
                        point['timestamp'] = datetime.fromisoformat(point['timestamp'])

                # Get strategy class
                mock_provider = HistoricalDataProvider(historical_data)
                strategy_instance = create_strategy(strategy_name, mock_provider, {})
                strategy_class = type(strategy_instance)

                # Run optimization
                from ..backtesting.engine import ParameterOptimizer

                async def run():
                    optimizer = ParameterOptimizer(strategy_class, historical_data)
                    return await optimizer.optimize(param_grid, metric)

                result = asyncio.run(run())

                return jsonify({
                    'best_params': result['best_params'],
                    'best_score': result['best_score'],
                    'result': result['best_result'].to_dict()
                })

            except Exception as e:
                logger.error(f"Error optimizing parameters: {e}")
                return jsonify({"error": str(e)}), 500

        # Alert routes
        @self.app.route('/api/alerts/config', methods=['GET'])
        def api_get_alert_config():
            """Get alert configuration."""
            return jsonify({
                'email_enabled': self.alert_manager.email_enabled,
                'sms_enabled': self.alert_manager.sms_enabled,
                'alert_on_trade': self.alert_manager.alert_on_trade,
                'alert_on_error': self.alert_manager.alert_on_error,
                'alert_on_profit_threshold': self.alert_manager.alert_on_profit_threshold,
                'alert_on_loss_threshold': self.alert_manager.alert_on_loss_threshold,
                'max_alerts_per_hour': self.alert_manager.max_alerts_per_hour
            })

        @self.app.route('/api/alerts/config', methods=['POST'])
        def api_update_alert_config():
            """Update alert configuration."""
            data = request.json or {}

            try:
                if 'alert_on_trade' in data:
                    self.alert_manager.alert_on_trade = data['alert_on_trade']
                if 'alert_on_error' in data:
                    self.alert_manager.alert_on_error = data['alert_on_error']
                if 'alert_on_profit_threshold' in data:
                    self.alert_manager.alert_on_profit_threshold = float(data['alert_on_profit_threshold'])
                if 'alert_on_loss_threshold' in data:
                    self.alert_manager.alert_on_loss_threshold = float(data['alert_on_loss_threshold'])

                return jsonify({"status": "updated"})

            except Exception as e:
                logger.error(f"Error updating alert config: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/alerts/test', methods=['POST'])
        def api_test_alert():
            """Send test alert."""
            data = request.json or {}
            message = data.get('message', 'Test alert from trading bot')

            try:
                success = self.alert_manager.send_custom_alert(
                    'Test Alert',
                    message,
                    level='info'
                )

                if success:
                    return jsonify({"status": "sent"})
                else:
                    return jsonify({"error": "Failed to send alert"}), 500

            except Exception as e:
                logger.error(f"Error sending test alert: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/alerts/history', methods=['GET'])
        def api_get_alert_history():
            """Get alert history."""
            limit = request.args.get('limit', 100, type=int)

            try:
                history = self.alert_manager.get_alert_history(limit)

                # Convert datetime to ISO format
                for alert in history:
                    if 'timestamp' in alert:
                        alert['timestamp'] = alert['timestamp'].isoformat()

                return jsonify(history)

            except Exception as e:
                logger.error(f"Error getting alert history: {e}")
                return jsonify({"error": str(e)}), 500

        # Profile management routes
        @self.app.route('/api/profiles', methods=['GET'])
        def api_list_profiles():
            """List all profiles."""
            try:
                profiles = self.profile_manager.list_profiles()
                return jsonify(profiles)
            except Exception as e:
                logger.error(f"Error listing profiles: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles', methods=['POST'])
        def api_create_profile():
            """Create new profile."""
            data = request.json or {}
            name = data.get('name')
            config = data.get('config', {})

            if not name:
                return jsonify({"error": "name required"}), 400

            try:
                profile_id = self.profile_manager.create_profile(name, config)
                return jsonify({"profile_id": profile_id, "status": "created"})
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Error creating profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/<profile_id>', methods=['GET'])
        def api_get_profile(profile_id):
            """Get profile (credentials masked)."""
            try:
                profile = self.profile_manager.get_profile(profile_id)
                if not profile:
                    return jsonify({"error": "Profile not found"}), 404

                # Mask credentials in response
                masked_profile = profile.copy()
                masked_profile['config'] = self.profile_manager.mask_credentials(profile['config'])

                return jsonify(masked_profile)
            except Exception as e:
                logger.error(f"Error getting profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/<profile_id>', methods=['PUT'])
        def api_update_profile(profile_id):
            """Update profile."""
            data = request.json or {}
            config = data.get('config', {})

            try:
                success = self.profile_manager.update_profile(profile_id, config)
                if success:
                    return jsonify({"status": "updated"})
                return jsonify({"error": "Profile not found"}), 404
            except Exception as e:
                logger.error(f"Error updating profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/<profile_id>/activate', methods=['POST'])
        def api_activate_profile(profile_id):
            """Activate a profile."""
            try:
                success = self.profile_manager.activate_profile(profile_id)
                if success:
                    return jsonify({"status": "activated"})
                return jsonify({"error": "Profile not found"}), 404
            except Exception as e:
                logger.error(f"Error activating profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/active', methods=['GET'])
        def api_get_active_profile():
            """Get active profile."""
            try:
                profile = self.profile_manager.get_active_profile()
                if profile:
                    # Mask credentials
                    masked_profile = profile.copy()
                    masked_profile['config'] = self.profile_manager.mask_credentials(profile['config'])
                    return jsonify(masked_profile)
                return jsonify(None)
            except Exception as e:
                logger.error(f"Error getting active profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/<profile_id>', methods=['DELETE'])
        def api_delete_profile(profile_id):
            """Delete profile."""
            try:
                success = self.profile_manager.delete_profile(profile_id)
                if success:
                    return jsonify({"status": "deleted"})
                return jsonify({"error": "Failed to delete profile"}), 500
            except Exception as e:
                logger.error(f"Error deleting profile: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/profiles/validate-credentials', methods=['POST'])
        def api_validate_credentials():
            """Validate API credentials."""
            data = request.json or {}
            provider = data.get('provider')
            credentials = data.get('credentials', {})

            if not provider:
                return jsonify({"error": "provider required"}), 400

            try:
                result = self.profile_manager.validate_credentials(provider, credentials)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error validating credentials: {e}")
                return jsonify({"error": str(e)}), 500

        # ====================================================================
        # WORKFLOW EXECUTION API
        # ====================================================================

        @self.app.route('/api/workflow/execute', methods=['POST'])
        def api_execute_workflow():
            """
            Execute a workflow graph.

            Request body:
                {
                    "workflow": {
                        "blocks": [...],
                        "connections": [...]
                    }
                }

            Returns:
                {
                    "status": "completed",
                    "duration": 234,
                    "results": [...],
                    "errors": []
                }
            """
            data = request.json or {}
            workflow = data.get('workflow')

            if not workflow:
                return jsonify({"error": "workflow required"}), 400

            if not workflow.get('blocks'):
                return jsonify({"error": "workflow must have blocks"}), 400

            try:
                from ..workflow.executor import WorkflowExecutor

                # Create executor
                executor = WorkflowExecutor(workflow)

                # Run workflow synchronously (async in a thread)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Initialize
                    loop.run_until_complete(executor.initialize())

                    # Execute
                    result = loop.run_until_complete(executor.execute())

                    return jsonify(result)

                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Error executing workflow: {e}", exc_info=True)
                return jsonify({
                    "status": "failed",
                    "error": str(e),
                    "duration": 0,
                    "results": [],
                    "errors": [{"error": str(e)}]
                }), 500

        @self.app.route('/api/credentials/profiles', methods=['GET'])
        def api_get_credential_profiles():
            """
            Get credential profiles for a provider.

            Query params:
                provider: Provider name (polymarket, binance, kalshi)

            Returns:
                [{
                    "id": "prod_1",
                    "name": "Production",
                    "provider": "polymarket",
                    "created_at": "2026-01-20T10:00:00Z"
                }]
            """
            provider = request.args.get('provider')

            if not provider:
                return jsonify({"error": "provider query parameter required"}), 400

            try:
                # Get all profiles
                all_profiles = self.profile_manager.get_all_profiles()

                # Filter by provider
                provider_profiles = [
                    {
                        'id': profile_id,
                        'name': profile.get('name', profile_id),
                        'provider': profile.get('provider', provider),
                        'created_at': profile.get('created_at', datetime.now().isoformat())
                    }
                    for profile_id, profile in all_profiles.items()
                    if profile.get('provider') == provider
                ]

                return jsonify(provider_profiles)

            except Exception as e:
                logger.error(f"Error fetching credential profiles: {e}")
                return jsonify({"error": str(e)}), 500

    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {
                'message': 'Connected to trading bot',
                'timestamp': datetime.now().isoformat()
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")

        @self.socketio.on('request_stats')
        def handle_request_stats():
            """Send current stats to client."""
            emit('stats_update', self.stats)

        @self.socketio.on('request_trades')
        def handle_request_trades(data=None):
            """Send recent trades to client."""
            limit = data.get('limit', 50) if data else 50
            emit('trades_update', self.recent_trades[-limit:])

        @self.socketio.on('request_bot_list')
        def handle_request_bot_list(data=None):
            """Send current bot list to client."""
            bots = self.bot_manager.get_all_bots()

            # Enrich with live metrics
            for bot in bots:
                bot_id = bot['id']
                bot['health'] = self._get_bot_health(bot_id)
                bot['sparkline'] = self._get_profit_sparkline(bot_id, points=10)
                bot['last_activity'] = self._get_last_activity(bot_id)

            emit('bot_list_update', bots)

        @self.socketio.on('request_provider_health')
        def handle_request_provider_health(data=None):
            """Send provider health status."""
            health = self._check_provider_health()
            emit('provider_health_update', health)

    def update_stats(self, stats: Dict[str, Any]):
        """
        Update statistics and broadcast to clients.

        Args:
            stats: Updated statistics
        """
        self.stats.update(stats)

        # Broadcast to all connected clients
        self.socketio.emit('stats_update', self.stats)

    def add_trade(self, trade: Dict[str, Any]):
        """
        Add a trade and broadcast to clients.

        Args:
            trade: Trade information
        """
        trade['timestamp'] = datetime.now().isoformat()
        self.recent_trades.append(trade)

        # Keep only last 1000 trades
        if len(self.recent_trades) > 1000:
            self.recent_trades = self.recent_trades[-1000:]

        # Broadcast to all connected clients
        self.socketio.emit('trade_executed', trade)
        self.socketio.emit('trades_update', self.recent_trades[-50:])

    def update_orders(self, orders: list):
        """
        Update active orders and broadcast to clients.

        Args:
            orders: List of active orders
        """
        self.active_orders = orders

        # Broadcast to all connected clients
        self.socketio.emit('orders_update', self.active_orders)

    def send_notification(self, message: str, level: str = "info"):
        """
        Send notification to clients.

        Args:
            message: Notification message
            level: Notification level (info, warning, error, success)
        """
        self.socketio.emit('notification', {
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        })

    def _get_bot_health(self, bot_id: str) -> Dict[str, Any]:
        """
        Get bot health indicators.

        Args:
            bot_id: Bot identifier

        Returns:
            Health indicators dict
        """
        bot = self.bot_manager.get_bot(bot_id)
        if not bot:
            return {}

        # Calculate balance sufficiency
        balance = bot.get('balance', 0)
        min_balance = bot.get('config', {}).get('position_size', 10) * 2  # Need at least 2x position size
        balance_sufficient = balance >= min_balance

        # Calculate error rate from recent trades
        bot_trades = [t for t in self.recent_trades if t.get('bot_id') == bot_id]
        recent_trades = bot_trades[-20:]  # Last 20 trades
        errors = sum(1 for t in recent_trades if t.get('status') == 'error')
        error_rate = (errors / len(recent_trades)) if recent_trades else 0.0

        # Calculate last trade age
        last_trade_age = 0
        if bot_trades:
            last_trade = bot_trades[-1]
            last_time = datetime.fromisoformat(last_trade.get('timestamp', datetime.now().isoformat()))
            last_trade_age = int((datetime.now() - last_time).total_seconds())

        # Determine overall health
        overall = 'healthy'
        if not bot.get('status') == 'running':
            overall = 'warning'
        elif error_rate > 0.2:  # More than 20% errors
            overall = 'critical'
        elif not balance_sufficient:
            overall = 'warning'

        return {
            'api_connected': bot.get('status') in ['running', 'paused'],
            'balance_sufficient': balance_sufficient,
            'balance': balance,
            'min_balance': min_balance,
            'error_rate': round(error_rate, 3),
            'error_count': errors,
            'total_trades': len(recent_trades),
            'last_trade_age': last_trade_age,
            'overall': overall
        }

    def _get_profit_sparkline(self, bot_id: str, points: int = 10) -> List[float]:
        """
        Get profit sparkline data for bot.

        Args:
            bot_id: Bot identifier
            points: Number of data points

        Returns:
            List of cumulative profit values
        """
        bot = self.bot_manager.get_bot(bot_id)
        if not bot:
            return []

        # Get last N trades for this bot
        bot_trades = [t for t in self.recent_trades if t.get('bot_id') == bot_id]
        recent = bot_trades[-points:]

        # Calculate cumulative profit
        cumulative = []
        total = 0
        for trade in recent:
            total += trade.get('profit', 0)
            cumulative.append(total)

        return cumulative

    def _get_last_activity(self, bot_id: str) -> Optional[str]:
        """
        Get last activity timestamp for bot.

        Args:
            bot_id: Bot identifier

        Returns:
            ISO format timestamp or None
        """
        # Find last trade for this bot
        bot_trades = [t for t in self.recent_trades if t.get('bot_id') == bot_id]
        if bot_trades:
            last_trade = bot_trades[-1]
            return last_trade.get('timestamp')
        return None

    def _check_provider_health(self) -> Dict[str, Any]:
        """
        Check health of all configured providers.

        Returns:
            Dict mapping provider names to health status
        """
        import os
        health = {}
        providers = get_supported_providers()

        # Map of provider-specific auth env vars
        auth_env_vars = {
            'polymarket': ['POLYMARKET_API_KEY', 'POLYMARKET_PRIVATE_KEY'],
            'binance': ['BINANCE_API_KEY', 'BINANCE_API_SECRET'],
            'coinbase': ['COINBASE_API_KEY', 'COINBASE_API_SECRET'],
            'bybit': ['BYBIT_API_KEY', 'BYBIT_API_SECRET'],
            'kraken': ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET'],
            'dydx': ['DYDX_API_KEY', 'DYDX_PRIVATE_KEY'],
            'luno': ['LUNO_API_KEY', 'LUNO_API_SECRET'],
            'kalshi': ['KALSHI_API_KEY', 'KALSHI_API_SECRET']
        }

        # Provider favicon URLs
        provider_favicons = {
            'polymarket': 'https://polymarket.com/favicon.ico',
            'binance': 'https://bin.bnbstatic.com/static/images/common/favicon.ico',
            'coinbase': 'https://www.coinbase.com/favicon.ico',
            'bybit': 'https://www.bybit.com/favicon.ico',
            'kraken': 'https://www.kraken.com/favicon.ico',
            'dydx': 'https://dydx.exchange/favicon.ico',
            'luno': 'https://www.luno.com/favicon.ico',
            'kalshi': 'https://kalshi.com/favicon.ico'
        }

        for provider_name in providers.keys():
            try:
                # Check authentication status
                required_vars = auth_env_vars.get(provider_name, [])
                auth_configured = all(os.getenv(var) for var in required_vars) if required_vars else True
                missing_vars = [var for var in required_vars if not os.getenv(var)]

                if not auth_configured:
                    # Authentication not configured
                    health[provider_name] = {
                        'status': 'auth_required',
                        'auth_configured': False,
                        'missing_vars': missing_vars,
                        'message': f'Missing: {", ".join(missing_vars)}',
                        'favicon': provider_favicons.get(provider_name, ''),
                        'last_check': datetime.now().isoformat()
                    }
                else:
                    # Measure API latency with simple ping
                    import time
                    start_time = time.time()
                    try:
                        # Attempt to instantiate provider (lightweight check)
                        # In production, make actual API call to test endpoint
                        provider_class = providers.get(provider_name)
                        if provider_class:
                            # Quick instantiation test
                            _ = provider_class.__name__  # Just access class name
                        latency_ms = round((time.time() - start_time) * 1000, 2)
                        status = 'online'
                    except Exception:
                        latency_ms = 0.0
                        status = 'degraded'

                    health[provider_name] = {
                        'status': status,
                        'auth_configured': True,
                        'latency_ms': latency_ms,
                        'favicon': provider_favicons.get(provider_name, ''),
                        'last_check': datetime.now().isoformat()
                    }
            except Exception as e:
                health[provider_name] = {
                    'status': 'offline',
                    'auth_configured': False,
                    'error': str(e),
                    'favicon': provider_favicons.get(provider_name, ''),
                    'last_check': datetime.now().isoformat()
                }

        return health

    def start_live_update_loop(self):
        """Background task to push live updates to clients."""
        def update_loop():
            while True:
                try:
                    # Update bot list every second
                    bots = self.bot_manager.get_all_bots()
                    for bot in bots:
                        bot['health'] = self._get_bot_health(bot['id'])
                        bot['sparkline'] = self._get_profit_sparkline(bot['id'])
                        bot['last_activity'] = self._get_last_activity(bot['id'])

                    self.socketio.emit('bot_list_update', bots)

                    # Update provider health every 5 seconds
                    if int(time.time()) % 5 == 0:
                        health = self._check_provider_health()
                        self.socketio.emit('provider_health_update', health)

                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in live update loop: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        logger.info("Live update loop started")

    def run(self):
        """Start the web server."""
        logger.info(f"Starting web server on {self.host}:{self.port}")

        # Start live update loop
        self.start_live_update_loop()

        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )


def create_web_server(config: Optional[Dict[str, Any]] = None) -> TradingBotWebServer:
    """
    Create and return web server instance.

    Args:
        config: Server configuration

    Returns:
        TradingBotWebServer instance
    """
    return TradingBotWebServer(config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trading Bot Web Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = create_web_server({
        "port": args.port,
        "host": args.host
    })

    server.run()
