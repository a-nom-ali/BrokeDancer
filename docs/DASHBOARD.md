# React Dashboard Documentation

The Elion Dashboard is a modern React-based web interface for monitoring and controlling the trading bot system.

## Overview

- **Framework**: React 19 with TypeScript 5.9
- **Styling**: TailwindCSS v4
- **Charts**: Recharts for data visualization
- **Workflow Visualization**: ReactFlow v12
- **Real-time**: Socket.io for WebSocket communication
- **Build Tool**: Vite 7

## Directory Structure

```
web/
├── src/
│   ├── components/
│   │   ├── Bots/           # Bot management components
│   │   ├── Charts/         # Recharts-based visualizations
│   │   ├── Dashboard/      # Dashboard widgets
│   │   ├── Emergency/      # Emergency control panel
│   │   ├── Events/         # Event display components
│   │   ├── Layout/         # App layout (sidebar, header)
│   │   ├── Shared/         # Reusable components
│   │   └── Workflow/       # ReactFlow visualizer
│   ├── hooks/              # Custom React hooks
│   ├── pages/              # Route pages
│   ├── services/           # API and WebSocket services
│   └── types/              # TypeScript type definitions
├── e2e/                    # Playwright E2E tests
├── scripts/                # Utility scripts
└── public/                 # Static assets
```

## Quick Start

### Development

```bash
cd web

# Install dependencies
npm install

# Start development server (http://localhost:5173)
npm run dev
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

### Environment Variables

Create `.env.development` or `.env.production`:

```env
# Flask HTTP API server (default port: 8080)
VITE_API_URL=http://localhost:8080/api

# WebSocket server for real-time events (default port: 8001)
VITE_WEBSOCKET_URL=http://localhost:8001

# Enable debug logging
VITE_ENABLE_DEBUG=true

# Use mock data (for development without backend)
VITE_MOCK_DATA=false
```

## Pages

### Dashboard (`/`)
Main overview with portfolio metrics, bot status, and recent activity.

### Bots (`/bots`)
Bot management interface with:
- Summary statistics (total bots, running, success rate)
- Filter tabs (All, Running, Paused, Stopped, Error)
- Bot cards with Start/Pause/Stop controls

### Metrics (`/metrics`)
Real-time analytics with:
- Summary cards (executions, success, failures, avg duration)
- Performance line chart (PnL over time)
- Execution bar chart (by bot)
- Timeline area chart (per minute)

### Events (`/events`)
Live event stream showing workflow execution events.

### Workflows (`/workflows`)
ReactFlow-based workflow visualization with real-time node status.

### History (`/history`)
Execution history with filtering and pagination.

### Emergency (`/emergency`)
Emergency control panel with:
- State indicators (NORMAL, ALERT, HALT, SHUTDOWN)
- Manual control buttons
- Risk limit monitor
- Event history

## Components

### Shared Components

| Component | Description |
|-----------|-------------|
| `ErrorBoundary` | Graceful error handling with recovery |
| `LoadingSpinner` | Loading indicator with size variants |
| `Skeleton` | Loading placeholders for cards/tables |
| `ConnectionStatus` | WebSocket connection indicator |
| `EmptyState` | Empty data state with icon and message |
| `MetricCard` | Colorful metric display card |

### Chart Components

| Component | Description |
|-----------|-------------|
| `PerformanceLineChart` | PnL and cumulative performance |
| `ExecutionBarChart` | Success/failure by bot |
| `ExecutionTimelineChart` | Executions over time |

### Bot Components

| Component | Description |
|-----------|-------------|
| `BotCard` | Individual bot with status and controls |
| `BotList` | Grid of bots with filtering |

## Testing

### Integration Tests

```bash
# Test backend connectivity
npm run test:integration
```

### E2E Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui
```

## Code Splitting

The dashboard uses code splitting for optimal performance:

| Chunk | Size (gzip) | Contents |
|-------|-------------|----------|
| `index` | ~75KB | Core app code |
| `react-vendor` | ~17KB | React, React DOM, React Router |
| `recharts` | ~107KB | Charting library |
| `reactflow` | ~58KB | Workflow visualization |

## WebSocket Events

### From Backend

| Event | Description |
|-------|-------------|
| `workflow_event` | Workflow execution events |
| `stats_update` | Real-time statistics |
| `trade_executed` | Trade notifications |
| `bot_started` | Bot started notification |
| `bot_stopped` | Bot stopped notification |
| `bot_list_update` | Bot list refresh |
| `recent_events` | Event replay on connect |

### To Backend

| Event | Description |
|-------|-------------|
| `subscribe_workflow` | Subscribe to workflow events |
| `subscribe_bot` | Subscribe to bot events |
| `request_stats` | Request current stats |

## Type Safety

All types are defined in `src/types/index.ts`:

- `BotStatus` - Bot state (running, paused, error, stopped)
- `WorkflowEvent` - WebSocket event structure
- `BotMetrics` - Bot performance metrics
- `ExecutionRecord` - Execution history entry

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### WebSocket Connection Failed

1. Check backend servers are running:
   ```bash
   python -m src.web.server --port 8080
   python src/web/run_websocket_server.py --port 8001
   ```

2. Verify environment variables match server ports

3. Check browser console for CORS errors

### Charts Not Rendering

1. Verify WebSocket connection (green indicator)
2. Check browser console for errors
3. Wait for events to populate data

### Build Errors

1. Clear build cache: `rm -rf node_modules/.tmp`
2. Reinstall dependencies: `npm install`
3. Run `npm run lint` to check for issues
