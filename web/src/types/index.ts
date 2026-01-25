/**
 * Core type definitions for the Multi-Domain Automation Platform Dashboard
 */

// ==================== Enums (as const for erasableSyntaxOnly) ====================

export const BotStatus = {
  RUNNING: 'running',
  PAUSED: 'paused',
  ERROR: 'error',
  STOPPED: 'stopped',
} as const;
export type BotStatus = typeof BotStatus[keyof typeof BotStatus];

export const StrategyStatus = {
  RUNNING: 'running',
  PAUSED: 'paused',
  ERROR: 'error',
} as const;
export type StrategyStatus = typeof StrategyStatus[keyof typeof StrategyStatus];

export const NodeStatus = {
  IDLE: 'idle',
  ACTIVE: 'active',
  EXECUTING: 'executing',
  SUCCESS: 'success',
  FAILED: 'failed',
} as const;
export type NodeStatus = typeof NodeStatus[keyof typeof NodeStatus];

export const Domain = {
  TRADING: 'trading',
  GPU: 'gpu',
  ADVERTISING: 'advertising',
  ECOMMERCE: 'ecommerce',
  CREDIT_YIELD: 'credit_yield',
} as const;
export type Domain = typeof Domain[keyof typeof Domain];

// ==================== Bot Types ====================

export interface Bot {
  botId: string;
  name: string;
  domain: Domain;
  status: BotStatus;
  totalPnl: number;
  totalPnlPercent: number;
  capital: number;
  activeStrategies: number;
  totalStrategies: number;
  uptime: string;
  createdAt: string;
  metrics: BotMetrics;
  strategies: StrategyInstance[];
}

export interface BotMetrics {
  pnl: number;
  pnlPercent: number;
  activeTrades?: number;
  winRate?: number;
  revenue?: number;
  occupancy?: number;
  roas?: number;
  spend?: number;
  dailyVolume?: number;
}

// ==================== Strategy Types ====================

export interface StrategyInstance {
  strategyId: string;
  botId: string;
  name: string;
  description?: string;
  status: StrategyStatus;
  weight: number; // Capital allocation weight (0-1)
  pnl: number;
  pnlPercent: number;
  tradesExecuted: number;
  tradesTotal: number;
  winRate: number;
  avgProfit: number;
  lastExecution: string;
  config: StrategyConfig;
  workflow: WorkflowDefinition;
}

export interface StrategyConfig {
  scanIntervalMs: number;
  minExpectedProfit: number;
  minRoi: number;
  enableAutoExecution: boolean;
  dryRunMode: boolean;
  customParams: Record<string, any>;
}

// ==================== Workflow Types ====================

export interface WorkflowDefinition {
  name: string;
  description: string;
  version: string;
  domain: Domain;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  config: WorkflowConfig;
}

export interface WorkflowNode {
  id: string;
  type: string;
  category: NodeCategory;
  properties: Record<string, any>;
  position: { x: number; y: number };
  status?: NodeStatus;
  currentValue?: any;
  lastExecutionTime?: number;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  label?: string;
  condition?: string;
}

export interface WorkflowConfig {
  executionMode: 'polling' | 'event-driven';
  pollIntervalSeconds?: number;
  enableAutoExecution: boolean;
  dryRun: boolean;
  riskLimits: Record<string, any>;
}

export const NodeCategory = {
  SOURCE: 'source',
  TRANSFORM: 'transform',
  SCORER: 'scorer',
  CONDITION: 'condition',
  EXECUTOR: 'executor',
  MONITOR: 'monitor',
} as const;
export type NodeCategory = typeof NodeCategory[keyof typeof NodeCategory];

// ==================== WebSocket Event Types ====================

export interface WebSocketEvent {
  type: string;
  timestamp: number;
  [key: string]: any;
}

export interface NodeExecutionEvent extends WebSocketEvent {
  type: 'node_execution';
  botId: string;
  strategyId: string;
  nodeId: string;
  data: {
    inputs: Record<string, any>;
    outputs: Record<string, any>;
    status: 'success' | 'failed' | 'running';
    executionTimeMs: number;
    error?: string;
  };
}

export interface BotMetricsEvent extends WebSocketEvent {
  type: 'bot_metrics';
  botId: string;
  metrics: BotMetrics;
}

export interface StrategyMetricsEvent extends WebSocketEvent {
  type: 'strategy_metrics';
  botId: string;
  strategyId: string;
  metrics: {
    opportunitiesFound: number;
    executed: number;
    pnl: number;
  };
}

export interface RiskLimitUpdateEvent extends WebSocketEvent {
  type: 'risk_limit_update';
  botId: string;
  limits: {
    dailyLoss: { used: number; limit: number };
    positionLimit: { used: number; limit: number };
    frequencyLimit: { used: number; limit: number };
  };
}

// ==================== Portfolio Types ====================

export interface GlobalPortfolio {
  totalPnl: number;
  totalPnlPercent: number;
  activeBots: number;
  totalBots: number;
  totalCapital: number;
  dailyVolume: number;
  pnlHistory: PnlDataPoint[];
}

export interface PnlDataPoint {
  timestamp: number;
  value: number;
}

// ==================== Activity Types ====================

export interface ActivityItem {
  id: string;
  timestamp: string;
  botId: string;
  botName: string;
  message: string;
  type: 'execution' | 'alert' | 'config_change';
}

// ==================== Risk Management Types ====================

export interface RiskConstraint {
  name: string;
  type: string;
  limit: number;
  used: number;
  enforce: boolean;
  timeWindow?: string;
}

// ==================== Execution History Types ====================

export interface ExecutionRecord {
  id: string;
  timestamp: string;
  strategyId: string;
  spread?: number;
  buyPrice?: number;
  sellPrice?: number;
  profit?: number;
  status: 'filled' | 'skipped' | 'failed';
  details?: Record<string, any>;
}

// ==================== Runtime Value Editing Types ====================

export interface NodeValueChange {
  nodeId: string;
  field: string;
  oldValue: any;
  newValue: any;
  timestamp: string;
  savedDuringRuntime: boolean;
}

export interface EditableNodeField {
  name: string;
  defaultValue: any;
  currentValue: any;
  runtimeValue?: any;
  type: 'number' | 'string' | 'boolean' | 'select';
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
}

// ==================== UI State Types ====================

export interface DashboardState {
  globalPortfolio: GlobalPortfolio;
  bots: Bot[];
  recentActivity: ActivityItem[];
  isLoading: boolean;
  error: string | null;
}

export interface BotDashboardState {
  bot: Bot | null;
  isLoading: boolean;
  error: string | null;
}

export interface StrategyViewState {
  strategy: StrategyInstance | null;
  executionHistory: ExecutionRecord[];
  selectedNode: WorkflowNode | null;
  valueChanges: NodeValueChange[];
  isLoading: boolean;
  error: string | null;
}
