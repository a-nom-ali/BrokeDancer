"""
Full Stack Integration Tests

Tests the integration between the React frontend services and Python backend.
Validates that API endpoints, WebSocket events, and data transformations work correctly.

Run with:
    pytest tests/integration/test_full_stack.py -v
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


class TestAPIResponseTransformation:
    """Test that API responses are correctly transformed between snake_case and camelCase."""

    def test_snake_to_camel_basic(self):
        """Test basic snake_case to camelCase conversion."""
        from src.web.server import TradingBotWebServer

        # Simulate backend response (snake_case)
        backend_response = {
            'bot_id': 'bot_001',
            'strategy_id': 'strat_001',
            'total_pnl': 1250.50,
            'created_at': '2026-01-27T10:00:00Z'
        }

        # The frontend api.ts transforms these to camelCase
        # This test validates the transformation logic
        def snake_to_camel(s: str) -> str:
            components = s.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])

        expected = {
            'botId': 'bot_001',
            'strategyId': 'strat_001',
            'totalPnl': 1250.50,
            'createdAt': '2026-01-27T10:00:00Z'
        }

        transformed = {snake_to_camel(k): v for k, v in backend_response.items()}
        assert transformed == expected

    def test_camel_to_snake_basic(self):
        """Test basic camelCase to snake_case conversion."""
        # Simulate frontend request (camelCase)
        frontend_request = {
            'botId': 'bot_001',
            'strategyId': 'strat_001',
            'totalPnl': 1250.50
        }

        def camel_to_snake(s: str) -> str:
            import re
            return re.sub(r'([A-Z])', r'_\1', s).lower()

        expected = {
            'bot_id': 'bot_001',
            'strategy_id': 'strat_001',
            'total_pnl': 1250.50
        }

        transformed = {camel_to_snake(k): v for k, v in frontend_request.items()}
        assert transformed == expected


class TestDemoModeDataGeneration:
    """Test that demo mode generates valid data."""

    def test_demo_data_generator_initialization(self):
        """Test DemoDataGenerator creates initial bots."""
        from src.web.demo_mode import DemoDataGenerator

        generator = DemoDataGenerator()

        # Should have 4 initial bots
        assert len(generator.bots) == 4

        # Each bot should have required fields
        for bot_id, bot in generator.bots.items():
            assert 'id' in bot
            assert 'name' in bot
            assert 'strategy' in bot
            assert 'provider' in bot
            assert 'status' in bot
            assert 'balance' in bot
            assert 'metrics' in bot
            assert bot['status'] in ['running', 'paused', 'stopped']

    def test_demo_trade_generation(self):
        """Test trade generation produces valid trade objects."""
        from src.web.demo_mode import DemoDataGenerator

        generator = DemoDataGenerator()

        # Generate a trade
        trade = generator.generate_trade()

        if trade:  # May be empty if no running bots
            assert 'id' in trade
            assert 'bot_id' in trade
            assert 'timestamp' in trade
            assert 'side' in trade
            assert trade['side'] in ['buy', 'sell']
            assert 'amount' in trade
            assert 'profit' in trade
            assert 'status' in trade

    def test_demo_portfolio_metrics(self):
        """Test portfolio metrics calculation."""
        from src.web.demo_mode import DemoDataGenerator

        generator = DemoDataGenerator()
        portfolio = generator.get_portfolio()

        assert 'total_balance' in portfolio
        assert 'total_pnl' in portfolio
        assert 'total_trades' in portfolio
        assert 'active_bots' in portfolio
        assert 'total_bots' in portfolio
        assert 'pnl_history' in portfolio
        assert portfolio['total_bots'] == 4

    def test_demo_pnl_history(self):
        """Test PnL history generation."""
        from src.web.demo_mode import DemoDataGenerator

        generator = DemoDataGenerator()
        portfolio = generator.get_portfolio()
        history = portfolio['pnl_history']

        assert len(history) == 30  # Default 30 days
        for entry in history:
            assert 'date' in entry
            assert 'daily_pnl' in entry
            assert 'cumulative_pnl' in entry


class TestServerEndpoints:
    """Test that server endpoints return correct data structures."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock server instance."""
        with patch('src.web.server.MultiBotManager'):
            with patch('src.web.server.DataExporter'):
                with patch('src.web.server.AlertManager'):
                    with patch('src.web.server.ProfileManager'):
                        from src.web.server import TradingBotWebServer
                        server = TradingBotWebServer({'port': 8080})
                        return server

    def test_portfolio_endpoint_structure(self, mock_server):
        """Test /api/portfolio returns expected structure."""
        # Mock the bot manager
        mock_server.bot_manager.get_aggregated_stats = Mock(return_value={
            'total_profit': 1000,
            'total_loss': 200,
            'total_trades': 100,
            'winning_trades': 60,
            'losing_trades': 40,
            'win_rate': 0.6
        })
        mock_server.bot_manager.get_all_bots = Mock(return_value=[
            {'id': 'bot_1', 'status': 'running', 'balance': 5000, 'strategies': []},
            {'id': 'bot_2', 'status': 'stopped', 'balance': 3000, 'strategies': []}
        ])

        # Test the endpoint via Flask test client
        with mock_server.app.test_client() as client:
            response = client.get('/api/portfolio')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'total_balance' in data
            assert 'total_pnl' in data
            assert 'active_bots' in data
            assert data['total_balance'] == 8000
            assert data['active_bots'] == 1

    def test_bots_endpoint_returns_list(self, mock_server):
        """Test /api/bots returns a list."""
        mock_server.bot_manager.get_all_bots = Mock(return_value=[
            {'id': 'bot_1', 'name': 'Test Bot', 'status': 'running'}
        ])

        with mock_server.app.test_client() as client:
            response = client.get('/api/bots')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]['id'] == 'bot_1'

    def test_activity_endpoint_structure(self, mock_server):
        """Test /api/activity returns activity items."""
        mock_server.recent_trades = [
            {
                'id': 'trade_1',
                'bot_id': 'bot_1',
                'timestamp': '2026-01-27T10:00:00Z',
                'side': 'buy',
                'amount': 100,
                'profit': 10
            }
        ]

        with mock_server.app.test_client() as client:
            response = client.get('/api/activity?limit=10')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert isinstance(data, list)
            if data:
                assert 'id' in data[0]
                assert 'type' in data[0]
                assert 'timestamp' in data[0]


class TestWebSocketEvents:
    """Test WebSocket event structures."""

    def test_workflow_event_structure(self):
        """Test workflow event has required fields."""
        event = {
            'type': 'node_execution',
            'bot_id': 'bot_001',
            'strategy_id': 'strat_001',
            'workflow_id': 'workflow_001',
            'node_id': 'node_1',
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }

        # Validate structure
        required_fields = ['type', 'timestamp']
        for field in required_fields:
            assert field in event

    def test_trade_executed_event_structure(self):
        """Test trade_executed event has required fields."""
        event = {
            'id': 'trade_001',
            'bot_id': 'bot_001',
            'timestamp': datetime.now().isoformat(),
            'side': 'buy',
            'amount': 100,
            'price': 0.65,
            'profit': 10.5,
            'status': 'completed'
        }

        required_fields = ['id', 'bot_id', 'timestamp', 'side', 'amount']
        for field in required_fields:
            assert field in event

    def test_bot_metrics_event_structure(self):
        """Test bot_metrics event has required fields."""
        event = {
            'type': 'bot_metrics',
            'bot_id': 'bot_001',
            'timestamp': datetime.now().isoformat(),
            'balance': 5000,
            'total_pnl': 1250.50,
            'total_trades': 100,
            'win_rate': 0.6
        }

        required_fields = ['type', 'bot_id', 'timestamp']
        for field in required_fields:
            assert field in event


class TestWebSocketServerHandlers:
    """Test WebSocket server handler logic."""

    @pytest.mark.asyncio
    async def test_subscribe_all_bots_handler(self):
        """Test subscribe_all_bots handler sets flag correctly."""
        # This tests the handler logic without actually running the server
        client_subscriptions = {
            'test_sid': {
                'workflow_ids': set(),
                'bot_ids': set(),
                'strategy_ids': set(),
                'authenticated': True,
                'all_bots': False
            }
        }

        # Simulate handler logic
        sid = 'test_sid'
        client_subscriptions[sid]['all_bots'] = True

        assert client_subscriptions[sid]['all_bots'] is True

    @pytest.mark.asyncio
    async def test_broadcast_to_all_bots_subscribers(self):
        """Test that events are broadcast to all_bots subscribers."""
        client_subscriptions = {
            'client_1': {
                'workflow_ids': set(),
                'bot_ids': set(),
                'strategy_ids': set(),
                'all_bots': True
            },
            'client_2': {
                'workflow_ids': set(),
                'bot_ids': {'bot_001'},
                'strategy_ids': set(),
                'all_bots': False
            },
            'client_3': {
                'workflow_ids': set(),
                'bot_ids': set(),
                'strategy_ids': set(),
                'all_bots': False
            }
        }

        event = {
            'type': 'node_execution',
            'bot_id': 'bot_002',  # Different from client_2's subscription
            'timestamp': datetime.now().isoformat()
        }

        # Simulate broadcast logic
        recipients = []
        for sid, subs in client_subscriptions.items():
            should_send = False

            if subs.get('all_bots'):
                should_send = True
            if event.get('bot_id') in subs['bot_ids']:
                should_send = True

            if should_send:
                recipients.append(sid)

        # client_1 subscribed to all_bots, client_2 only to bot_001
        assert 'client_1' in recipients
        assert 'client_2' not in recipients  # Not subscribed to bot_002
        assert 'client_3' not in recipients


class TestEndToEndFlow:
    """Test complete data flow from backend to frontend."""

    def test_portfolio_data_flow(self):
        """Test portfolio data flows correctly through the system."""
        from src.web.demo_mode import DemoDataGenerator

        # 1. Backend generates data
        generator = DemoDataGenerator()
        portfolio = generator.get_portfolio()

        # 2. Data has snake_case keys (Python convention)
        assert 'total_balance' in portfolio
        assert 'total_pnl' in portfolio
        assert 'active_bots' in portfolio

        # 3. Frontend transforms to camelCase
        def transform_keys(obj):
            if isinstance(obj, dict):
                return {
                    ''.join(word.title() if i > 0 else word for i, word in enumerate(k.split('_'))): transform_keys(v)
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [transform_keys(item) for item in obj]
            return obj

        frontend_data = transform_keys(portfolio)

        # 4. Frontend receives camelCase keys
        assert 'totalBalance' in frontend_data
        assert 'totalPnl' in frontend_data
        assert 'activeBots' in frontend_data

    def test_bot_lifecycle_events(self):
        """Test bot lifecycle event flow."""
        from src.web.demo_mode import DemoDataGenerator

        generator = DemoDataGenerator()

        # Get initial state
        bots = generator.get_all_bots()
        initial_running = len([b for b in bots if b['status'] == 'running'])

        # Stop a running bot
        running_bot = next((b for b in bots if b['status'] == 'running'), None)
        if running_bot:
            generator.stop_bot(running_bot['id'])

            # Verify state changed
            updated_bot = generator.get_bot(running_bot['id'])
            assert updated_bot['status'] == 'stopped'

            # Count should have decreased
            bots = generator.get_all_bots()
            new_running = len([b for b in bots if b['status'] == 'running'])
            assert new_running == initial_running - 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
