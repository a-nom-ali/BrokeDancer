/**
 * Mock Data for Playwright Tests
 *
 * Provides realistic mock data for API and WebSocket responses
 */

export const mockBots = [
  {
    id: 'bot_polymarket_arb',
    name: 'Polymarket Arbitrage Bot',
    strategy: 'binary_arbitrage',
    provider: 'polymarket',
    status: 'running',
    balance: 15000.50,
    created_at: '2026-01-20T10:00:00Z',
    config: {
      position_size: 100,
      max_positions: 5,
      min_edge: 0.015,
    },
    metrics: {
      total_trades: 245,
      winning_trades: 156,
      losing_trades: 89,
      total_pnl: 2450.75,
      win_rate: 0.637,
    },
    strategies: [
      {
        id: 'bot_polymarket_arb_strategy_1',
        bot_id: 'bot_polymarket_arb',
        name: 'binary_arbitrage',
        type: 'binary_arbitrage',
        status: 'running',
        config: {},
        created_at: '2026-01-20T10:00:00Z',
        metrics: {
          total_executions: 245,
          successful_executions: 156,
          failed_executions: 89,
          total_pnl: 2450.75,
        },
      },
    ],
  },
  {
    id: 'bot_binance_stat',
    name: 'Binance Statistical Bot',
    strategy: 'statistical_arbitrage',
    provider: 'binance',
    status: 'paused',
    balance: 8500.00,
    created_at: '2026-01-15T08:30:00Z',
    config: {
      position_size: 50,
      max_positions: 10,
      min_edge: 0.01,
    },
    metrics: {
      total_trades: 512,
      winning_trades: 298,
      losing_trades: 214,
      total_pnl: 1250.00,
      win_rate: 0.582,
    },
    strategies: [
      {
        id: 'bot_binance_stat_strategy_1',
        bot_id: 'bot_binance_stat',
        name: 'statistical_arbitrage',
        type: 'statistical_arbitrage',
        status: 'paused',
        config: {},
        created_at: '2026-01-15T08:30:00Z',
        metrics: {
          total_executions: 512,
          successful_executions: 298,
          failed_executions: 214,
          total_pnl: 1250.00,
        },
      },
    ],
  },
  {
    id: 'bot_cross_ex',
    name: 'Cross Exchange Bot',
    strategy: 'cross_exchange_arbitrage',
    provider: 'coinbase',
    status: 'stopped',
    balance: 5000.00,
    created_at: '2026-01-10T14:00:00Z',
    config: {
      position_size: 25,
      max_positions: 3,
      min_edge: 0.02,
    },
    metrics: {
      total_trades: 78,
      winning_trades: 45,
      losing_trades: 33,
      total_pnl: -150.25,
      win_rate: 0.577,
    },
    strategies: [],
  },
];

export const mockPortfolio = {
  total_balance: 28500.50,
  total_pnl: 3550.50,
  total_trades: 835,
  winning_trades: 499,
  losing_trades: 336,
  win_rate: 0.598,
  active_bots: 1,
  total_bots: 3,
  active_strategies: 1,
  pnl_history: generatePnlHistory(30),
  updated_at: new Date().toISOString(),
};

export const mockActivity = [
  {
    id: 'act_001',
    type: 'trade',
    bot_id: 'bot_polymarket_arb',
    strategy_id: 'bot_polymarket_arb_strategy_1',
    description: 'Trade executed: buy 100',
    profit: 25.50,
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    status: 'completed',
  },
  {
    id: 'act_002',
    type: 'trade',
    bot_id: 'bot_polymarket_arb',
    strategy_id: 'bot_polymarket_arb_strategy_1',
    description: 'Trade executed: sell 50',
    profit: -10.25,
    timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
    status: 'completed',
  },
  {
    id: 'act_003',
    type: 'trade',
    bot_id: 'bot_binance_stat',
    strategy_id: 'bot_binance_stat_strategy_1',
    description: 'Trade executed: buy 75',
    profit: 15.00,
    timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    status: 'completed',
  },
];

export const mockExecutions = [
  {
    id: 'exec_001',
    strategy_id: 'bot_polymarket_arb_strategy_1',
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    type: 'trade',
    side: 'buy',
    amount: 100,
    price: 0.65,
    profit: 25.50,
    status: 'completed',
    duration_ms: 245,
  },
  {
    id: 'exec_002',
    strategy_id: 'bot_polymarket_arb_strategy_1',
    timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
    type: 'trade',
    side: 'sell',
    amount: 50,
    price: 0.72,
    profit: -10.25,
    status: 'completed',
    duration_ms: 180,
  },
];

export const mockWorkflow = {
  blocks: [
    {
      id: 'block_1',
      type: 'provider',
      category: 'providers',
      name: 'Polymarket Provider',
      position: { x: 100, y: 100 },
    },
    {
      id: 'block_2',
      type: 'fetch_orderbook',
      category: 'data',
      name: 'Fetch Orderbook',
      position: { x: 300, y: 100 },
    },
    {
      id: 'block_3',
      type: 'calculate_edge',
      category: 'logic',
      name: 'Calculate Edge',
      position: { x: 500, y: 100 },
    },
  ],
  connections: [
    { from: 'block_1', to: 'block_2' },
    { from: 'block_2', to: 'block_3' },
  ],
  strategy_id: 'bot_polymarket_arb_strategy_1',
};

export const mockProviderHealth = {
  polymarket: {
    status: 'online',
    auth_configured: true,
    latency_ms: 45,
    favicon: 'https://polymarket.com/favicon.ico',
    last_check: new Date().toISOString(),
  },
  binance: {
    status: 'online',
    auth_configured: true,
    latency_ms: 23,
    favicon: 'https://bin.bnbstatic.com/static/images/common/favicon.ico',
    last_check: new Date().toISOString(),
  },
  coinbase: {
    status: 'auth_required',
    auth_configured: false,
    missing_vars: ['COINBASE_API_KEY', 'COINBASE_API_SECRET'],
    message: 'Missing: COINBASE_API_KEY, COINBASE_API_SECRET',
    favicon: 'https://www.coinbase.com/favicon.ico',
    last_check: new Date().toISOString(),
  },
  kalshi: {
    status: 'offline',
    auth_configured: false,
    error: 'Connection timeout',
    favicon: 'https://kalshi.com/favicon.ico',
    last_check: new Date().toISOString(),
  },
};

export const mockEmergencyState = {
  state: 'NORMAL',
  can_trade: true,
  can_operate: true,
  risk_limits: {
    max_daily_loss: 1000,
    max_position_size: 500,
    max_open_positions: 10,
    current_daily_loss: 150,
    current_positions: 3,
  },
  history: [
    {
      timestamp: new Date(Date.now() - 24 * 60 * 60000).toISOString(),
      from_state: 'ALERT',
      to_state: 'NORMAL',
      reason: 'Manual resume',
    },
    {
      timestamp: new Date(Date.now() - 48 * 60 * 60000).toISOString(),
      from_state: 'NORMAL',
      to_state: 'ALERT',
      reason: 'Daily loss limit approaching',
    },
  ],
};

// Helper to generate PnL history
function generatePnlHistory(days: number) {
  const history = [];
  let cumulative = 0;

  for (let i = days; i > 0; i--) {
    const date = new Date(Date.now() - i * 24 * 60 * 60000);
    const daily = Math.random() * 200 - 50; // Random between -50 and 150
    cumulative += daily;
    history.push({
      date: date.toISOString().split('T')[0],
      daily_pnl: Math.round(daily * 100) / 100,
      cumulative_pnl: Math.round(cumulative * 100) / 100,
    });
  }

  return history;
}

// WebSocket mock events
export const mockWebSocketEvents = {
  nodeExecution: {
    type: 'node_execution',
    bot_id: 'bot_polymarket_arb',
    strategy_id: 'bot_polymarket_arb_strategy_1',
    workflow_id: 'workflow_bot_polymarket_arb',
    node_id: 'node_1',
    node_type: 'fetch_orderbook',
    status: 'completed',
    timestamp: new Date().toISOString(),
    duration_ms: 45,
    output: { value: 0.65 },
  },
  botMetrics: {
    type: 'bot_metrics',
    bot_id: 'bot_polymarket_arb',
    timestamp: new Date().toISOString(),
    balance: 15025.00,
    total_pnl: 2475.25,
    total_trades: 246,
    win_rate: 0.638,
    active_positions: 2,
    pending_orders: 1,
  },
  tradeExecuted: {
    id: 'trade_new_001',
    bot_id: 'bot_polymarket_arb',
    timestamp: new Date().toISOString(),
    side: 'buy',
    amount: 100,
    price: 0.65,
    profit: 24.50,
    status: 'completed',
  },
  botStarted: {
    bot_id: 'bot_binance_stat',
    timestamp: new Date().toISOString(),
  },
  botStopped: {
    bot_id: 'bot_polymarket_arb',
    timestamp: new Date().toISOString(),
  },
};
