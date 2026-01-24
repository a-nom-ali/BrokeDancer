"""
WebSocket Server for Real-Time Workflow Events

Broadcasts workflow execution events to connected UI clients using Socket.IO.
"""

import socketio
from aiohttp import web
from typing import Optional, Dict, Set
from src.infrastructure.factory import Infrastructure
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class WorkflowWebSocketServer:
    """
    WebSocket server that broadcasts workflow events to UI clients.

    Features:
    - Real-time event broadcasting
    - Client subscription by workflow/bot/strategy ID
    - Automatic reconnection support
    - Event replay for new clients

    Usage:
        # Create server
        infra = await Infrastructure.create("development")
        server = WorkflowWebSocketServer(infra)

        # Start server
        await server.run(host='0.0.0.0', port=8001)

        # Clients connect via Socket.IO:
        # const socket = io('http://localhost:8001')
        # socket.on('workflow_event', (event) => { ... })
    """

    def __init__(self, infra: Infrastructure):
        """
        Initialize WebSocket server.

        Args:
            infra: Infrastructure instance
        """
        self.infra = infra

        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',  # Allow all origins for development
            logger=False,
            engineio_logger=False
        )

        # Create aiohttp web app
        self.app = web.Application()
        self.sio.attach(self.app)

        # Track client subscriptions
        # sid -> {'workflow_ids': set(), 'bot_ids': set(), 'strategy_ids': set()}
        self.client_subscriptions: Dict[str, Dict[str, Set[str]]] = {}

        # Recent events buffer (for replay to new clients)
        self.recent_events: list = []
        self.max_recent_events = 100

        # Register event handlers
        self._register_handlers()

        logger.info("websocket_server_initialized", cors_allowed=True)

    def _register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection."""
            logger.info("client_connected", sid=sid)

            # Initialize subscription tracking
            self.client_subscriptions[sid] = {
                'workflow_ids': set(),
                'bot_ids': set(),
                'strategy_ids': set()
            }

            # Send connection confirmation
            await self.sio.emit('connected', {
                'sid': sid,
                'message': 'Connected to workflow events'
            }, to=sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            logger.info("client_disconnected", sid=sid)

            # Clean up subscriptions
            if sid in self.client_subscriptions:
                del self.client_subscriptions[sid]

        @self.sio.event
        async def subscribe_workflow(sid, data):
            """
            Subscribe to workflow-specific events.

            Client sends: { workflow_id: 'arb_btc_001' }
            """
            workflow_id = data.get('workflow_id')

            if not workflow_id:
                await self.sio.emit('error', {
                    'message': 'workflow_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['workflow_ids'].add(workflow_id)

            logger.info(
                "client_subscribed_workflow",
                sid=sid,
                workflow_id=workflow_id
            )

            # Send recent events for this workflow
            await self._send_recent_events(sid, workflow_id=workflow_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'workflow',
                'workflow_id': workflow_id
            }, to=sid)

        @self.sio.event
        async def subscribe_bot(sid, data):
            """
            Subscribe to bot-specific events.

            Client sends: { bot_id: 'bot_001' }
            """
            bot_id = data.get('bot_id')

            if not bot_id:
                await self.sio.emit('error', {
                    'message': 'bot_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['bot_ids'].add(bot_id)

            logger.info("client_subscribed_bot", sid=sid, bot_id=bot_id)

            # Send recent events for this bot
            await self._send_recent_events(sid, bot_id=bot_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'bot',
                'bot_id': bot_id
            }, to=sid)

        @self.sio.event
        async def subscribe_strategy(sid, data):
            """
            Subscribe to strategy-specific events.

            Client sends: { strategy_id: 'arb_btc' }
            """
            strategy_id = data.get('strategy_id')

            if not strategy_id:
                await self.sio.emit('error', {
                    'message': 'strategy_id required'
                }, to=sid)
                return

            # Add to subscriptions
            self.client_subscriptions[sid]['strategy_ids'].add(strategy_id)

            logger.info(
                "client_subscribed_strategy",
                sid=sid,
                strategy_id=strategy_id
            )

            # Send recent events for this strategy
            await self._send_recent_events(sid, strategy_id=strategy_id)

            # Confirm subscription
            await self.sio.emit('subscribed', {
                'type': 'strategy',
                'strategy_id': strategy_id
            }, to=sid)

        @self.sio.event
        async def unsubscribe(sid, data):
            """
            Unsubscribe from events.

            Client sends: { type: 'workflow', workflow_id: 'arb_btc_001' }
            """
            sub_type = data.get('type')
            sub_id = data.get(f'{sub_type}_id')

            if not sub_type or not sub_id:
                return

            # Remove from subscriptions
            subs = self.client_subscriptions.get(sid, {})
            sub_set = subs.get(f'{sub_type}_ids', set())
            sub_set.discard(sub_id)

            logger.info(
                "client_unsubscribed",
                sid=sid,
                type=sub_type,
                id=sub_id
            )

            # Confirm unsubscription
            await self.sio.emit('unsubscribed', {
                'type': sub_type,
                f'{sub_type}_id': sub_id
            }, to=sid)

    async def setup(self):
        """Set up event bus subscription."""
        # Subscribe to workflow events from infrastructure
        await self.infra.events.subscribe(
            "workflow_events",
            self.handle_workflow_event
        )

        logger.info("websocket_server_subscribed_to_events")

    async def handle_workflow_event(self, event: dict):
        """
        Handle workflow event from event bus.

        Forwards event to subscribed clients.

        Args:
            event: Workflow event
        """
        # Store in recent events buffer
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

        # Log event
        logger.debug(
            "workflow_event_received",
            event_type=event.get('type'),
            workflow_id=event.get('workflow_id'),
            node_id=event.get('node_id')
        )

        # Broadcast to subscribed clients
        await self._broadcast_event(event)

    async def _broadcast_event(self, event: dict):
        """
        Broadcast event to subscribed clients.

        Args:
            event: Event to broadcast
        """
        workflow_id = event.get('workflow_id')
        bot_id = event.get('bot_id')
        strategy_id = event.get('strategy_id')

        # Find matching clients
        for sid, subs in self.client_subscriptions.items():
            should_send = False

            # Check if client is subscribed to this workflow
            if workflow_id and workflow_id in subs['workflow_ids']:
                should_send = True

            # Check if client is subscribed to this bot
            if bot_id and bot_id in subs['bot_ids']:
                should_send = True

            # Check if client is subscribed to this strategy
            if strategy_id and strategy_id in subs['strategy_ids']:
                should_send = True

            # Send event to client
            if should_send:
                await self.sio.emit('workflow_event', event, to=sid)

    async def _send_recent_events(
        self,
        sid: str,
        workflow_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        strategy_id: Optional[str] = None
    ):
        """
        Send recent events to newly subscribed client.

        Args:
            sid: Client session ID
            workflow_id: Optional workflow filter
            bot_id: Optional bot filter
            strategy_id: Optional strategy filter
        """
        filtered_events = []

        for event in self.recent_events:
            match = False

            if workflow_id and event.get('workflow_id') == workflow_id:
                match = True
            if bot_id and event.get('bot_id') == bot_id:
                match = True
            if strategy_id and event.get('strategy_id') == strategy_id:
                match = True

            if match:
                filtered_events.append(event)

        # Send events
        if filtered_events:
            await self.sio.emit('recent_events', {
                'events': filtered_events,
                'count': len(filtered_events)
            }, to=sid)

            logger.info(
                "recent_events_sent",
                sid=sid,
                event_count=len(filtered_events)
            )

    async def run(self, host: str = '0.0.0.0', port: int = 8001):
        """
        Start WebSocket server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        logger.info("websocket_server_starting", host=host, port=port)

        # Set up event subscription
        await self.setup()

        # Run server
        web.run_app(
            self.app,
            host=host,
            port=port,
            print=lambda x: logger.info("aiohttp_message", message=x)
        )

    def get_stats(self) -> dict:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats
        """
        total_subscriptions = sum(
            len(subs['workflow_ids']) +
            len(subs['bot_ids']) +
            len(subs['strategy_ids'])
            for subs in self.client_subscriptions.values()
        )

        return {
            'connected_clients': len(self.client_subscriptions),
            'total_subscriptions': total_subscriptions,
            'recent_events_count': len(self.recent_events),
            'clients': [
                {
                    'sid': sid,
                    'workflow_count': len(subs['workflow_ids']),
                    'bot_count': len(subs['bot_ids']),
                    'strategy_count': len(subs['strategy_ids'])
                }
                for sid, subs in self.client_subscriptions.items()
            ]
        }
