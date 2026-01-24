# WebSocket Server Guide

**Version:** 1.0.0 (Week 3 Day 2)
**Last Updated:** 2026-01-24

Complete guide to the Workflow WebSocket Server for real-time event broadcasting.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Reference](#api-reference)
- [HTTP Endpoints](#http-endpoints)
- [Event Types](#event-types)
- [Client Integration](#client-integration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Workflow WebSocket Server provides real-time event broadcasting for workflow executions using Socket.IO. It:

- Subscribes to workflow events from the infrastructure event bus
- Broadcasts events to connected UI clients in real-time
- Supports selective subscriptions by workflow/bot/strategy ID
- Includes authentication for production use
- Provides health check and metrics endpoints
- Buffers recent events for replay on reconnection

**Architecture:**

```
Workflow Executor → Event Bus → WebSocket Server → UI Clients
                                      ↓
                                 Health/Metrics
```

---

## Features

### Core Features

✅ **Real-Time Event Broadcasting**
- Events published to event bus are instantly forwarded to clients
- No polling required
- Low latency (<50ms typical)

✅ **Selective Subscriptions**
- Subscribe to specific workflows, bots, or strategies
- Receive only relevant events
- Multiple simultaneous subscriptions supported

✅ **Event Replay**
- Recent events buffer (last 100 events)
- Automatically sent to new subscribers
- Useful for reconnection scenarios

✅ **Authentication** (Optional)
- Token-based authentication
- Per-connection authentication state
- Configurable requirement

✅ **Health & Metrics**
- HTTP health check endpoint
- Real-time metrics endpoint
- Infrastructure health status

✅ **Connection Management**
- Automatic reconnection support
- Client tracking with session IDs
- Subscription cleanup on disconnect

---

## Quick Start

### 1. Start the Server

**Development (no authentication):**

```bash
# From project root
python src/web/run_websocket_server.py
```

**Production (with authentication):**

```bash
# Using command-line argument
python src/web/run_websocket_server.py --env production --auth-token YOUR_SECRET_TOKEN

# Or using environment variable
export WS_AUTH_TOKEN=YOUR_SECRET_TOKEN
python src/web/run_websocket_server.py --env production --require-auth
```

**Custom host/port:**

```bash
python src/web/run_websocket_server.py --host 127.0.0.1 --port 8080
```

### 2. Test with HTML Client

Open the test client in your browser:

```bash
# Using Python's built-in HTTP server
cd examples
python -m http.server 8000

# Then open: http://localhost:8000/websocket_test_client.html
```

### 3. Connect from Your App

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8001');

socket.on('connected', (data) => {
  console.log('Connected:', data);

  // Subscribe to workflow
  socket.emit('subscribe_workflow', { workflow_id: 'my_workflow_001' });
});

socket.on('workflow_event', (event) => {
  console.log('Event:', event);
});
```

---

## Authentication

### Overview

Authentication is **optional** but recommended for production. When enabled:

1. Clients must authenticate before subscribing to events
2. Unauthenticated clients can connect but cannot subscribe
3. Authentication uses a simple token-based system

### Server Configuration

**Option 1: Command-line argument**

```bash
python src/web/run_websocket_server.py --auth-token SECRET_TOKEN --require-auth
```

**Option 2: Environment variable**

```bash
export WS_AUTH_TOKEN=SECRET_TOKEN
python src/web/run_websocket_server.py --require-auth
```

**Option 3: Programmatic**

```python
from src.infrastructure.factory import create_infrastructure
from src.web.websocket_server import WorkflowWebSocketServer

infra = await create_infrastructure("production")

server = WorkflowWebSocketServer(
    infra,
    auth_token="YOUR_SECRET_TOKEN",
    require_auth=True
)

await server.run(host='0.0.0.0', port=8001)
```

### Client Authentication

```javascript
const socket = io('http://localhost:8001');

socket.on('connected', (data) => {
  if (data.auth_required) {
    // Authenticate
    socket.emit('authenticate', { token: 'YOUR_TOKEN' });
  }
});

socket.on('auth_response', (data) => {
  if (data.success) {
    console.log('Authenticated!');
    // Now can subscribe to events
    socket.emit('subscribe_workflow', { workflow_id: 'my_workflow' });
  } else {
    console.error('Auth failed:', data.message);
  }
});
```

### Security Recommendations

For production:

1. **Use strong tokens**: Generate with `openssl rand -hex 32`
2. **Use HTTPS/WSS**: Encrypt all traffic with TLS
3. **Rotate tokens**: Change tokens periodically
4. **Environment variables**: Never commit tokens to git
5. **Firewall**: Restrict access to known IP ranges

---

## API Reference

### Socket.IO Events

#### Client → Server

**`authenticate`**

Authenticate connection (if auth required).

```javascript
socket.emit('authenticate', { token: 'YOUR_TOKEN' });
```

**Response:** `auth_response` event

---

**`subscribe_workflow`**

Subscribe to workflow-specific events.

```javascript
socket.emit('subscribe_workflow', { workflow_id: 'arb_btc_001' });
```

**Response:** `subscribed` event + `recent_events` (if any)

---

**`subscribe_bot`**

Subscribe to bot-specific events (all workflows for a bot).

```javascript
socket.emit('subscribe_bot', { bot_id: 'bot_001' });
```

**Response:** `subscribed` event + `recent_events` (if any)

---

**`subscribe_strategy`**

Subscribe to strategy-specific events.

```javascript
socket.emit('subscribe_strategy', { strategy_id: 'arbitrage_v1' });
```

**Response:** `subscribed` event + `recent_events` (if any)

---

**`unsubscribe`**

Unsubscribe from events.

```javascript
socket.emit('unsubscribe', {
  type: 'workflow',
  workflow_id: 'arb_btc_001'
});
```

**Response:** `unsubscribed` event

---

#### Server → Client

**`connected`**

Sent immediately after connection.

```json
{
  "sid": "abc123",
  "message": "Connected to workflow events",
  "auth_required": false,
  "server_time": "2026-01-24T10:00:00.000Z"
}
```

---

**`auth_response`**

Response to authentication attempt.

```json
{
  "success": true,
  "message": "Authentication successful"
}
```

---

**`subscribed`**

Confirmation of subscription.

```json
{
  "type": "workflow",
  "workflow_id": "arb_btc_001"
}
```

---

**`unsubscribed`**

Confirmation of unsubscription.

```json
{
  "type": "workflow",
  "workflow_id": "arb_btc_001"
}
```

---

**`workflow_event`**

Workflow execution event (see [Event Types](#event-types)).

```json
{
  "type": "node_completed",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "node_id": "price_binance",
  "timestamp": "2026-01-24T10:00:00.000Z",
  "duration_ms": 45,
  "status": "success",
  "outputs": { "price": 50234.56 }
}
```

---

**`recent_events`**

Recent events buffer (sent after subscription).

```json
{
  "events": [...],
  "count": 15
}
```

---

**`error`**

Error message.

```json
{
  "message": "Authentication required"
}
```

---

## HTTP Endpoints

### `GET /health`

Health check endpoint for load balancers and monitoring.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-24T10:00:00.000Z",
  "uptime_seconds": 3600,
  "websocket": {
    "connected_clients": 5,
    "total_connections": 127
  },
  "infrastructure": {
    "status": "healthy",
    "components": {
      "state": "healthy",
      "events": "healthy",
      "emergency": "normal"
    }
  }
}
```

**Status Codes:**
- `200` - Healthy
- `503` - Unhealthy (infrastructure issues)

---

### `GET /metrics`

Detailed metrics for monitoring.

**Response:**

```json
{
  "timestamp": "2026-01-24T10:00:00.000Z",
  "uptime_seconds": 3600,
  "connections": {
    "current": 5,
    "total": 127
  },
  "subscriptions": {
    "total": 12,
    "by_client": [
      {
        "sid": "abc123",
        "workflow_count": 2,
        "bot_count": 1,
        "strategy_count": 0
      }
    ]
  },
  "events": {
    "received": 1543,
    "sent": 7234,
    "recent_buffer": 100
  }
}
```

---

### `GET /status`

Simple status check.

**Response:**

```json
{
  "status": "ok",
  "server": "workflow-websocket-server",
  "timestamp": "2026-01-24T10:00:00.000Z"
}
```

---

## Event Types

All workflow events follow this schema:

### Common Fields

All events include:

```json
{
  "type": "event_type",
  "execution_id": "exec_workflow_001_a1b2c3d4",
  "workflow_id": "workflow_001",
  "bot_id": "bot_001",           // Optional
  "strategy_id": "arbitrage_v1", // Optional
  "timestamp": "2026-01-24T10:00:00.000Z"
}
```

### `execution_started`

Workflow execution begins.

```json
{
  "type": "execution_started",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "bot_id": "bot_001",
  "strategy_id": "arbitrage_v1",
  "timestamp": "2026-01-24T10:00:00.000Z",
  "node_count": 5
}
```

### `node_started`

Node execution begins.

```json
{
  "type": "node_started",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "node_id": "price_binance",
  "node_name": "Binance Price Feed",
  "node_category": "providers",
  "timestamp": "2026-01-24T10:00:00.100Z"
}
```

### `node_completed`

Node execution completes successfully.

```json
{
  "type": "node_completed",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "node_id": "price_binance",
  "timestamp": "2026-01-24T10:00:00.145Z",
  "duration_ms": 45,
  "status": "success",
  "outputs": {
    "price": 50234.56,
    "volume": 1234.56
  }
}
```

### `node_failed`

Node execution fails.

```json
{
  "type": "node_failed",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "node_id": "price_binance",
  "timestamp": "2026-01-24T10:00:00.145Z",
  "duration_ms": 45,
  "error": "Connection timeout",
  "error_type": "TimeoutError"
}
```

### `execution_completed`

Workflow execution completes.

```json
{
  "type": "execution_completed",
  "execution_id": "exec_arb_btc_001_a1b2c3d4",
  "workflow_id": "arb_btc_001",
  "timestamp": "2026-01-24T10:00:01.000Z",
  "duration_ms": 900,
  "status": "completed",
  "results": {
    "action_1": { "order_id": "order_123", "filled": true }
  }
}
```

---

## Client Integration

### React Hook Example

```typescript
import { useEffect, useState } from 'react';
import io, { Socket } from 'socket.io-client';

interface WorkflowEvent {
  type: string;
  execution_id: string;
  workflow_id: string;
  timestamp: string;
  [key: string]: any;
}

export function useWorkflowEvents(workflowId: string) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = io('http://localhost:8001');

    socket.on('connect', () => {
      setConnected(true);
      // Subscribe to workflow
      socket.emit('subscribe_workflow', { workflow_id: workflowId });
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socket.on('workflow_event', (event: WorkflowEvent) => {
      setEvents(prev => [...prev, event]);
    });

    setSocket(socket);

    return () => {
      socket.disconnect();
    };
  }, [workflowId]);

  return { events, connected, socket };
}
```

### Python Client Example

```python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print('Connected to WebSocket server')
    sio.emit('subscribe_workflow', {'workflow_id': 'my_workflow_001'})

@sio.event
def workflow_event(data):
    print(f"Event: {data['type']} - {data.get('node_id')}")

@sio.event
def disconnect():
    print('Disconnected from server')

# Connect
sio.connect('http://localhost:8001')
sio.wait()
```

---

## Testing

### Using the HTML Test Client

1. Start the WebSocket server:

```bash
python src/web/run_websocket_server.py
```

2. Start the test client HTTP server:

```bash
cd examples
python -m http.server 8000
```

3. Open browser: `http://localhost:8000/websocket_test_client.html`

4. Connect and test subscriptions

### Running the Enhanced Workflow Demo

The demo automatically broadcasts events to the WebSocket server:

Terminal 1 (WebSocket server):
```bash
python src/web/run_websocket_server.py
```

Terminal 2 (Test client):
```bash
# Open test client in browser
cd examples && python -m http.server 8000
```

Terminal 3 (Run demo):
```bash
PYTHONPATH=. python examples/enhanced_workflow_demo.py
```

Watch events appear in real-time in the test client!

### Automated Testing

```python
import pytest
from src.infrastructure.factory import create_infrastructure
from src.web.websocket_server import WorkflowWebSocketServer

@pytest.mark.asyncio
async def test_websocket_event_broadcasting():
    """Test that events are broadcast to clients."""
    infra = await create_infrastructure("memory")
    server = WorkflowWebSocketServer(infra)

    # Set up test...
    # Verify events are forwarded...
```

---

## Production Deployment

### Configuration

**Environment Variables:**

```bash
# Required
ENV=production

# Optional
WS_AUTH_TOKEN=your-secret-token-here
WS_HOST=0.0.0.0
WS_PORT=8001

# Infrastructure
REDIS_URL=redis://localhost:6379/0
```

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY examples/ ./examples/

# Expose WebSocket port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run server
CMD ["python", "src/web/run_websocket_server.py", "--env", "production"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  websocket-server:
    build: .
    ports:
      - "8001:8001"
    environment:
      - ENV=production
      - REDIS_URL=redis://redis:6379/0
      - WS_AUTH_TOKEN=${WS_AUTH_TOKEN}
    depends_on:
      - redis
    restart: unless-stopped
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name ws.example.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring

**Health Check:**

```bash
curl http://localhost:8001/health
```

**Metrics Collection:**

```bash
# Prometheus metrics endpoint (custom implementation)
curl http://localhost:8001/metrics
```

**Logging:**

All logs use structured logging (JSON format in production):

```json
{
  "timestamp": "2026-01-24T10:00:00.000Z",
  "level": "info",
  "event": "client_connected",
  "sid": "abc123",
  "total_connections": 127
}
```

---

## Troubleshooting

### Connection Issues

**Problem:** Client cannot connect to server

**Solutions:**

1. Check server is running:
   ```bash
   curl http://localhost:8001/status
   ```

2. Check firewall allows port 8001

3. Verify CORS settings (should be `*` for development)

4. Check client URL matches server address

---

**Problem:** `Authentication required` error

**Solutions:**

1. Authenticate before subscribing:
   ```javascript
   socket.emit('authenticate', { token: 'YOUR_TOKEN' });
   ```

2. Verify token matches server configuration

3. Check server logs for auth failures

---

### Event Issues

**Problem:** Not receiving events

**Solutions:**

1. Verify subscription was successful:
   ```javascript
   socket.on('subscribed', data => console.log('Subscribed:', data));
   ```

2. Check workflow is actually executing

3. Verify workflow_id/bot_id/strategy_id matches

4. Check browser console for errors

---

**Problem:** Receiving duplicate events

**Solutions:**

1. Ensure only one subscription per workflow
2. Check for multiple socket connections
3. Unsubscribe before resubscribing

---

### Performance Issues

**Problem:** High latency

**Solutions:**

1. Check network latency to server
2. Reduce event buffer size if memory constrained
3. Use Redis for production (faster than memory)
4. Consider running server closer to clients

---

**Problem:** Memory usage growing

**Solutions:**

1. Reduce `max_recent_events` (default: 100)
2. Implement event expiration
3. Monitor with `/metrics` endpoint
4. Restart server periodically (zero-downtime with load balancer)

---

## Summary

The Workflow WebSocket Server provides:

✅ Real-time event broadcasting with Socket.IO
✅ Selective subscriptions by workflow/bot/strategy
✅ Optional authentication for production
✅ Health check and metrics endpoints
✅ Event replay for new connections
✅ Full infrastructure integration

**Next Steps:**

1. Integrate with your React dashboard
2. Build real-time visualizations
3. Add custom event types as needed
4. Deploy to production with authentication

**Related Documentation:**

- `WEEK_3_DAY_1_COMPLETE.md` - Infrastructure integration
- `WEEK_3_INTEGRATION_PLAN.md` - Overall Week 3 plan
- `DASHBOARD_ARCHITECTURE.md` - UI architecture

---

**Questions?** Check the examples directory or run the test client!
