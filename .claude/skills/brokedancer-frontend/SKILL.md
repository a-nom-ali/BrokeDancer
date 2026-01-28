---
name: brokedancer-frontend
description: |
  React dashboard for BrokeDancer trading bot. Use when:
  (1) Creating or modifying React components in web/src/
  (2) Working with WebSocket real-time updates
  (3) Adding new pages or navigation routes
  (4) Styling with TailwindCSS or shadcn/ui
  (5) Writing Playwright E2E tests in web/e2e/
  Tech stack: React 18, TypeScript, Vite, TailwindCSS, ReactFlow, Recharts, Socket.io.
---

# BrokeDancer Frontend

## Tech Stack

- **React 18** + **TypeScript** (strict mode)
- **Vite** (build tool)
- **TailwindCSS v4** + **shadcn/ui** (styling)
- **ReactFlow** (workflow visualization)
- **Recharts** (charts)
- **Socket.io client** (WebSocket)
- **Playwright** (E2E testing)

## Directory Structure

```
web/
├── src/
│   ├── components/
│   │   ├── Bots/           # Bot list, cards, controls
│   │   ├── Dashboard/      # Dashboard widgets
│   │   ├── Charts/         # Bar, Line, Timeline charts
│   │   ├── Workflow/       # ReactFlow visualization
│   │   ├── Events/         # Event stream, cards
│   │   ├── Emergency/      # Emergency controls panel
│   │   ├── History/        # Execution history viewer
│   │   ├── Layout/         # DashboardLayout, Navigation
│   │   └── Shared/         # MetricCard, LoadingSpinner, etc.
│   ├── pages/              # Route pages
│   ├── services/
│   │   ├── api.ts          # HTTP client (snake_case transform)
│   │   └── websocket.ts    # Socket.io client
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useWorkflowEvents.ts
│   └── types/
│       └── index.ts        # TypeScript definitions
├── e2e/                    # Playwright tests
│   ├── fixtures/           # Mock data and test utils
│   └── *.spec.ts           # Test files
└── playwright.config.ts
```

## API Client

**Location**: `web/src/services/api.ts`

```typescript
// Automatic snake_case ↔ camelCase transformation
import { api } from '@/services/api';

const bots = await api.getBots();           // GET /api/bots
const bot = await api.getBot('123');        // GET /api/bots/123
await api.startBot('123');                  // POST /api/bots/123/start
await api.stopBot('123');                   // POST /api/bots/123/stop
const portfolio = await api.getPortfolio(); // GET /api/portfolio
```

**Base URL**: `VITE_API_URL` env var (default: `http://localhost:8080/api`)

## WebSocket

**Location**: `web/src/services/websocket.ts`

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

const { connected, subscribe, unsubscribe } = useWebSocket();

// Subscribe to events
subscribe('bot_started', (data) => console.log(data));
subscribe('trade_executed', handleTrade);
subscribe('workflow_event', handleWorkflow);
```

**Events**:
- `bot_started`, `bot_stopped`, `bot_paused`
- `trade_executed`, `opportunity_found`
- `workflow_event`, `node_execution`
- `emergency_state_changed`

## Component Patterns

**Shared components** (`web/src/components/Shared/`):
```typescript
import { MetricCard, LoadingSpinner, StatusBadge } from '@/components/Shared';

<MetricCard
  title="Total Profit"
  value="$1,234.56"
  trend={5.2}
/>
<StatusBadge status="running" />
<LoadingSpinner />
```

**Page layout**:
```typescript
import { DashboardLayout } from '@/components/Layout';

export function MyPage() {
  return (
    <DashboardLayout>
      <h2 className="text-2xl font-bold mb-4">Page Title</h2>
      {/* Content */}
    </DashboardLayout>
  );
}
```

## Adding a New Page

1. Create page component in `web/src/pages/MyPage.tsx`
2. Add route in `web/src/App.tsx`:
   ```typescript
   <Route path="/my-page" element={<MyPage />} />
   ```
3. Add nav link in `web/src/components/Layout/Navigation.tsx`
4. Add E2E test in `web/e2e/my-page.spec.ts`

## TypeScript Types

**Location**: `web/src/types/index.ts`

```typescript
interface Bot {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'paused' | 'error';
  strategy: string;
  provider: string;
  profit: number;
  tradesExecuted: number;
}

interface Portfolio {
  totalValue: number;
  pnlToday: number;
  pnlPercent: number;
}
```

## Styling

Use TailwindCSS classes:
```tsx
<div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
  <h3 className="text-lg font-semibold text-white">Title</h3>
  <p className="text-gray-400 text-sm">Description</p>
</div>
```

## Testing

```bash
# Development
npm run dev           # Start dev server (port 5173)

# Build
npm run build         # Production build
npm run preview       # Preview build

# Linting
npm run lint          # ESLint check

# E2E Tests
npm run test:e2e      # Run Playwright tests
npm run test:e2e:ui   # Playwright UI mode
```

## E2E Test Patterns

**Location**: `web/e2e/`

```typescript
import { test, expect } from '@playwright/test';
import { setupApiMocks, mockWebSocket } from './fixtures/test-utils';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
  });

  test('should display data', async ({ page }) => {
    await page.goto('/my-page');
    await expect(page.locator('h2')).toContainText('My Page');
  });
});
```
