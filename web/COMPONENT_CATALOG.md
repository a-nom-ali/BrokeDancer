# Component Catalog

**Version**: 1.0.0
**Last Updated**: 2026-01-24

This document catalogs all reusable components in the dashboard.

---

## Layout Components

### Header
**Location**: `src/components/layout/Header.tsx`
**Purpose**: Top navigation bar with branding and user actions

**Props**:
```typescript
interface HeaderProps {
  title?: string;
  onSettingsClick?: () => void;
  onProfileClick?: () => void;
}
```

**Usage**:
```tsx
<Header
  title="Multi-Domain Automation Platform"
  onSettingsClick={() => navigate('/settings')}
  onProfileClick={() => navigate('/profile')}
/>
```

---

### Breadcrumb
**Location**: `src/components/layout/Breadcrumb.tsx`
**Purpose**: Navigation breadcrumb trail

**Props**:
```typescript
interface BreadcrumbProps {
  items: Array<{
    label: string;
    href?: string;
  }>;
}
```

**Usage**:
```tsx
<Breadcrumb
  items={[
    { label: 'Dashboard', href: '/' },
    { label: 'Bots', href: '/bots' },
    { label: 'BTC Arbitrage' }
  ]}
/>
```

---

## Dashboard Components

### BotCard
**Location**: `src/components/dashboard/BotCard.tsx`
**Purpose**: Display bot summary on main dashboard

**Props**:
```typescript
interface BotCardProps {
  bot: Bot;
  onClick?: (botId: string) => void;
  onPause?: (botId: string) => void;
  onStart?: (botId: string) => void;
}
```

**Features**:
- Status indicator
- PnL display with color coding
- Mini metrics preview
- Action buttons (View, Pause/Start, Edit)

**Usage**:
```tsx
<BotCard
  bot={botData}
  onClick={(id) => navigate(`/bots/${id}`)}
  onPause={handlePauseBot}
/>
```

---

### GlobalPortfolio
**Location**: `src/components/dashboard/GlobalPortfolio.tsx`
**Purpose**: Display global portfolio metrics and PnL chart

**Props**:
```typescript
interface GlobalPortfolioProps {
  portfolio: GlobalPortfolio;
  timeRange?: '1D' | '7D' | '30D';
  onTimeRangeChange?: (range: string) => void;
}
```

**Usage**:
```tsx
<GlobalPortfolio
  portfolio={portfolioData}
  timeRange="30D"
  onTimeRangeChange={setTimeRange}
/>
```

---

### ActivityFeed
**Location**: `src/components/dashboard/ActivityFeed.tsx`
**Purpose**: Display recent activity stream

**Props**:
```typescript
interface ActivityFeedProps {
  activities: ActivityItem[];
  limit?: number;
  onViewAll?: () => void;
}
```

**Usage**:
```tsx
<ActivityFeed
  activities={recentActivity}
  limit={5}
  onViewAll={() => navigate('/activity')}
/>
```

---

## Bot Dashboard Components

### OrchestrationDiagram
**Location**: `src/components/bot/OrchestrationDiagram.tsx`
**Purpose**: Display bot orchestration workflow using ReactFlow

**Props**:
```typescript
interface OrchestrationDiagramProps {
  botId: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  editable?: boolean;
  onNodesChange?: (nodes: WorkflowNode[]) => void;
  onEdgesChange?: (edges: WorkflowEdge[]) => void;
}
```

**Usage**:
```tsx
<OrchestrationDiagram
  botId={bot.botId}
  nodes={orchestrationNodes}
  edges={orchestrationEdges}
  editable={true}
  onNodesChange={handleNodeUpdate}
/>
```

---

### StrategyCard
**Location**: `src/components/bot/StrategyCard.tsx`
**Purpose**: Display strategy summary in bot dashboard

**Props**:
```typescript
interface StrategyCardProps {
  strategy: StrategyInstance;
  onViewWorkflow?: (strategyId: string) => void;
  onPause?: (strategyId: string) => void;
  onEditConfig?: (strategyId: string) => void;
}
```

**Usage**:
```tsx
<StrategyCard
  strategy={strategyData}
  onViewWorkflow={(id) => navigate(`/strategies/${id}`)}
  onPause={handlePauseStrategy}
/>
```

---

### RiskManagementPanel
**Location**: `src/components/bot/RiskManagementPanel.tsx`
**Purpose**: Display risk constraint usage bars

**Props**:
```typescript
interface RiskManagementPanelProps {
  constraints: RiskConstraint[];
}
```

**Usage**:
```tsx
<RiskManagementPanel
  constraints={bot.riskConstraints}
/>
```

---

## Strategy View Components

### WorkflowCanvas
**Location**: `src/components/strategy/WorkflowCanvas.tsx`
**Purpose**: Display live workflow execution with ReactFlow

**Props**:
```typescript
interface WorkflowCanvasProps {
  workflow: WorkflowDefinition;
  onNodeSelect?: (node: WorkflowNode) => void;
  onNodeValueChange?: (nodeId: string, field: string, value: any) => void;
}
```

**Features**:
- Live node status updates
- Click to select node
- Real-time value display
- Execution animations

**Usage**:
```tsx
<WorkflowCanvas
  workflow={strategyWorkflow}
  onNodeSelect={setSelectedNode}
  onNodeValueChange={handleValueChange}
/>
```

---

### LiveNode
**Location**: `src/components/strategy/LiveNode.tsx`
**Purpose**: ReactFlow custom node with live data display

**Props**:
```typescript
interface LiveNodeProps extends NodeProps {
  data: {
    label: string;
    status: NodeStatus;
    currentValue?: any;
    lastExecutionTime?: number;
  };
}
```

**Features**:
- Status-based styling
- Pulse animation when executing
- Shake animation on error
- Value highlight on update

**Usage**:
```tsx
// Registered as custom node type in ReactFlow
const nodeTypes = {
  live: LiveNode,
};
```

---

### NodeEditPanel
**Location**: `src/components/strategy/NodeEditPanel.tsx`
**Purpose**: Unity-style value editing panel for selected node

**Props**:
```typescript
interface NodeEditPanelProps {
  node: WorkflowNode | null;
  editableFields: EditableNodeField[];
  valueChanges: NodeValueChange[];
  onValueChange: (field: string, value: any) => void;
  onSave: (field: string, value: any) => void;
  onRevert: (field: string) => void;
}
```

**Features**:
- Real-time value editing
- Save button when value differs
- Revert to default button
- Change log display

**Usage**:
```tsx
<NodeEditPanel
  node={selectedNode}
  editableFields={getEditableFields(selectedNode)}
  valueChanges={nodeChangeLog}
  onValueChange={handleRuntimeChange}
  onSave={handleSaveValue}
  onRevert={handleRevert}
/>
```

---

### ExecutionHistoryTable
**Location**: `src/components/strategy/ExecutionHistoryTable.tsx`
**Purpose**: Display strategy execution history

**Props**:
```typescript
interface ExecutionHistoryTableProps {
  records: ExecutionRecord[];
  onExport?: () => void;
}
```

**Usage**:
```tsx
<ExecutionHistoryTable
  records={executionHistory}
  onExport={exportToCSV}
/>
```

---

## Shared Components

### MetricCard
**Location**: `src/components/shared/MetricCard.tsx`
**Purpose**: Display single metric with label and value

**Props**:
```typescript
interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
  loading?: boolean;
}
```

**Usage**:
```tsx
<MetricCard
  label="Total PnL"
  value="+$2,456.78"
  change={1.64}
  changeType="positive"
  icon={<DollarSign />}
/>
```

---

### StatusBadge
**Location**: `src/components/shared/StatusBadge.tsx`
**Purpose**: Display status indicator with dot and label

**Props**:
```typescript
interface StatusBadgeProps {
  status: BotStatus | StrategyStatus | NodeStatus;
  label?: string;
  showDot?: boolean;
}
```

**Usage**:
```tsx
<StatusBadge
  status={BotStatus.RUNNING}
  label="Running"
  showDot={true}
/>
```

---

### PnLChart
**Location**: `src/components/shared/PnLChart.tsx`
**Purpose**: Line chart for PnL visualization using Recharts

**Props**:
```typescript
interface PnLChartProps {
  data: PnlDataPoint[];
  height?: number;
  showGrid?: boolean;
  showTooltip?: boolean;
}
```

**Usage**:
```tsx
<PnLChart
  data={pnlHistory}
  height={200}
  showGrid={true}
  showTooltip={true}
/>
```

---

### Button
**Location**: `src/components/shared/Button.tsx`
**Purpose**: Reusable button with variants

**Props**:
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}
```

**Usage**:
```tsx
<Button
  variant="primary"
  size="md"
  onClick={handleSubmit}
  loading={isSubmitting}
>
  Save Changes
</Button>
```

---

### LoadingSpinner
**Location**: `src/components/shared/LoadingSpinner.tsx`
**Purpose**: Loading indicator

**Props**:
```typescript
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}
```

**Usage**:
```tsx
<LoadingSpinner
  size="lg"
  message="Loading bot data..."
/>
```

---

### ErrorMessage
**Location**: `src/components/shared/ErrorMessage.tsx`
**Purpose**: Display error messages

**Props**:
```typescript
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}
```

**Usage**:
```tsx
<ErrorMessage
  message="Failed to load bot data"
  onRetry={refetch}
  onDismiss={clearError}
/>
```

---

## Custom Hooks

### useWebSocket
**Location**: `src/hooks/useWebSocket.ts`
**Purpose**: Hook for WebSocket event subscriptions

**Usage**:
```typescript
const { connected, subscribe, unsubscribe } = useWebSocket();

useEffect(() => {
  const handler = (data: BotMetricsEvent) => {
    // Handle event
  };

  subscribe('bot_metrics', handler);
  return () => unsubscribe('bot_metrics', handler);
}, []);
```

---

### useBot
**Location**: `src/hooks/useBot.ts`
**Purpose**: Fetch and manage bot data

**Usage**:
```typescript
const { bot, loading, error, refetch, updateBot } = useBot(botId);
```

---

### useStrategy
**Location**: `src/hooks/useStrategy.ts`
**Purpose**: Fetch and manage strategy data

**Usage**:
```typescript
const { strategy, loading, error, executionHistory, refetch } = useStrategy(strategyId);
```

---

## Utility Functions

### formatCurrency
**Location**: `src/utils/format.ts`
**Purpose**: Format numbers as currency

**Usage**:
```typescript
formatCurrency(2456.78) // "$2,456.78"
formatCurrency(-123.45) // "-$123.45"
```

---

### formatPercent
**Location**: `src/utils/format.ts`
**Purpose**: Format numbers as percentages

**Usage**:
```typescript
formatPercent(0.0164) // "+1.64%"
formatPercent(-0.0023) // "-0.23%"
```

---

### formatTimeAgo
**Location**: `src/utils/format.ts`
**Purpose**: Format timestamp as relative time

**Usage**:
```typescript
formatTimeAgo(Date.now() - 120000) // "2 minutes ago"
formatTimeAgo(Date.now() - 3600000) // "1 hour ago"
```

---

## Notes

- All components use TypeScript for type safety
- All components use TailwindCSS for styling
- All interactive components support keyboard navigation
- All components have proper ARIA labels for accessibility

**To add a new component**:
1. Create component file in appropriate directory
2. Add TypeScript interface for props
3. Implement component with TailwindCSS
4. Add to this catalog with usage example
5. Export from index file

---

**End of Component Catalog**
