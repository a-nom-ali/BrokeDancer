"""
WebSocket Server Startup Script

Starts the WebSocket server for real-time workflow events.

Run with:
    # Development (in-memory infrastructure)
    python src/web/run_websocket_server.py

    # Production (Redis infrastructure)
    ENV=production python src/web/run_websocket_server.py
"""

import asyncio
import argparse
from src.infrastructure.factory import create_infrastructure
from src.web.websocket_server import WorkflowWebSocketServer
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Start WebSocket server."""
    parser = argparse.ArgumentParser(description="WebSocket Server for Workflow Events")
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="Environment (default: development)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to bind to (default: 8001)"
    )
    args = parser.parse_args()

    # Create infrastructure
    logger.info(
        "creating_infrastructure",
        env=args.env,
        host=args.host,
        port=args.port
    )

    infra = await create_infrastructure(args.env)

    try:
        # Create WebSocket server
        server = WorkflowWebSocketServer(infra)

        logger.info(
            "websocket_server_created",
            env=args.env,
            state_backend=infra.config.state.backend,
            events_backend=infra.config.events.backend
        )

        # Run server (blocks until shutdown)
        await server.run(host=args.host, port=args.port)

    except KeyboardInterrupt:
        logger.info("websocket_server_shutdown", reason="keyboard_interrupt")

    finally:
        # Clean up infrastructure
        await infra.close()
        logger.info("infrastructure_closed")


if __name__ == "__main__":
    asyncio.run(main())
