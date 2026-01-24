# Multi-Domain Automation Platform - Dashboard

React-based dashboard for managing automation bots across multiple domains (trading, GPU, ads, ecommerce).

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Utility-first styling
- **ReactFlow** - Node diagrams
- **Recharts** - Charts and graphs
- **Socket.io** - Real-time WebSocket communication
- **React Router** - Navigation

## Project Structure

```
src/
├── components/          # React components
│   ├── layout/         # Layout components (Header, Sidebar, etc.)
│   ├── dashboard/      # Main dashboard components
│   ├── bot/            # Bot dashboard components
│   ├── strategy/       # Strategy view components
│   └── shared/         # Shared/reusable components
├── pages/              # Page components
├── services/           # API and WebSocket services
├── hooks/              # Custom React hooks
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── context/            # React Context providers
└── index.css           # Global styles with Tailwind
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.development

# Start development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Environment Variables

Create a `.env.development` file:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WEBSOCKET_URL=http://localhost:8000
VITE_ENABLE_DEBUG=true
VITE_MOCK_DATA=false
```

## Available Scripts

```bash
# Development server
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Dashboard Hierarchy

### 1. Main Dashboard
- Overview of all bots
- Global portfolio metrics
- Bot status cards
- Recent activity feed

### 2. Bot Dashboard
- Single bot details
- Orchestration diagram
- Strategy list
- Risk management metrics

### 3. Strategy View
- Live workflow execution
- Node-based diagram with real-time values
- Runtime value editing (Unity-style)
- Execution history

## Real-time Updates

The dashboard uses WebSocket (Socket.io) for real-time updates:

- Node execution events (< 100ms latency)
- Bot metrics updates (every 1-5 seconds)
- Strategy metrics updates (every 1-5 seconds)
- Risk limit updates (real-time)

## Runtime Value Editing

Users can edit node values while workflows are running (Unity-style):
- Click node to open editing panel
- Change values immediately (affects live execution)
- Save button appears when value differs from default
- Click "Save as Default" to persist changes
- All changes logged with timestamp

## Development Guidelines

### Component Structure

```typescript
// Use functional components with TypeScript
interface Props {
  botId: string;
  onUpdate?: (bot: Bot) => void;
}

export function BotCard({ botId, onUpdate }: Props) {
  // Implementation
}
```

### State Management

Use React Context + useReducer for global state:

```typescript
// context/DashboardContext.tsx
const [state, dispatch] = useReducer(dashboardReducer, initialState);
```

### WebSocket Usage

```typescript
import { websocketService } from '../services/websocket';

// Connect on mount
useEffect(() => {
  websocketService.connect();
  return () => websocketService.disconnect();
}, []);

// Subscribe to events
useEffect(() => {
  const handler = (data: BotMetricsEvent) => {
    // Update state
  };

  websocketService.on('bot_metrics', handler);
  return () => websocketService.off('bot_metrics', handler);
}, []);
```

### Styling

Use TailwindCSS utility classes:

```tsx
<div className="dashboard-card">
  <div className="flex items-center justify-between">
    <h2 className="text-xl font-semibold">Bot Name</h2>
    <span className="status-dot status-running" />
  </div>
</div>
```

Custom animations are available:
- `animate-pulse-green` - Node executing
- `animate-shake` - Node error
- `value-updated` - Value change highlight

## Design Tokens

### Colors

**Status:**
- Running: `#10B981` (green)
- Paused: `#F59E0B` (amber)
- Error: `#EF4444` (red)

**Node States:**
- Active: `#3B82F6` (blue)
- Executing: `#10B981` (green)
- Failed: `#EF4444` (red)
- Idle: `#6B7280` (gray)

### Typography

- H1: 24px Bold
- H2: 20px Semibold
- H3: 16px Semibold
- Body: 14px Normal
- Small: 12px Normal

### Spacing

Use Tailwind spacing scale (4, 8, 16, 24, 32px)

## Testing

```bash
# Run tests (when configured)
npm run test

# Run tests in watch mode
npm run test:watch

# Generate coverage
npm run test:coverage
```

## Build and Deploy

```bash
# Build for production
npm run build

# Preview production build
npm run preview

# Build output is in dist/ directory
```

## Backend Integration

The dashboard connects to a Python FastAPI backend:

- REST API: `http://localhost:8000/api`
- WebSocket: `http://localhost:8000`

See backend documentation for API endpoints.

## Contributing

1. Follow TypeScript strict mode
2. Use functional components
3. Add proper types for all props
4. Use TailwindCSS for styling
5. Write meaningful commit messages (gitmoji format)

## License

Same as parent project
