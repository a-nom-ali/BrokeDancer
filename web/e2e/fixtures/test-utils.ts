/**
 * Test Utilities for Playwright
 *
 * Provides helpers for API mocking, WebSocket simulation, and common test patterns
 */

import { Page, Route } from '@playwright/test';
import {
  mockBots,
  mockPortfolio,
  mockActivity,
  mockExecutions,
  mockWorkflow,
} from './mock-data';

const API_BASE = 'http://localhost:8080/api';

/**
 * Setup all API mocks for a page
 */
export async function setupApiMocks(page: Page, options?: {
  bots?: typeof mockBots;
  portfolio?: typeof mockPortfolio;
  activity?: typeof mockActivity;
  delay?: number;
}) {
  const bots = options?.bots ?? mockBots;
  const portfolio = options?.portfolio ?? mockPortfolio;
  const activity = options?.activity ?? mockActivity;
  const delay = options?.delay ?? 0;

  // Mock /api/bots
  await page.route(`${API_BASE}/bots`, async (route) => {
    if (delay) await new Promise(r => setTimeout(r, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(bots),
    });
  });

  // Mock /api/bots/:id
  await page.route(`${API_BASE}/bots/*`, async (route) => {
    const url = route.request().url();

    // Handle specific bot endpoints
    if (url.includes('/start') || url.includes('/stop') || url.includes('/pause')) {
      await handleBotAction(route, url, bots);
      return;
    }

    if (url.includes('/activity')) {
      await handleBotActivity(route, url, activity);
      return;
    }

    if (url.includes('/strategies')) {
      await handleBotStrategies(route, url, bots);
      return;
    }

    // Get single bot
    const botId = url.split('/bots/')[1]?.split('/')[0]?.split('?')[0];
    const bot = bots.find(b => b.id === botId);

    if (delay) await new Promise(r => setTimeout(r, delay));

    if (bot) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(bot),
      });
    } else {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Bot not found' }),
      });
    }
  });

  // Mock /api/portfolio
  await page.route(`${API_BASE}/portfolio`, async (route) => {
    if (delay) await new Promise(r => setTimeout(r, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(portfolio),
    });
  });

  // Mock /api/portfolio/pnl
  await page.route(`${API_BASE}/portfolio/pnl*`, async (route) => {
    if (delay) await new Promise(r => setTimeout(r, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(portfolio.pnl_history),
    });
  });

  // Mock /api/activity
  await page.route(`${API_BASE}/activity*`, async (route) => {
    if (delay) await new Promise(r => setTimeout(r, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(activity),
    });
  });

  // Mock /api/strategies/*
  await page.route(`${API_BASE}/strategies/*`, async (route) => {
    await handleStrategyRoutes(route, bots);
  });

  // Mock /api/providers
  await page.route(`${API_BASE}/providers`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        polymarket: { name: 'Polymarket', type: 'prediction_market' },
        binance: { name: 'Binance', type: 'crypto_exchange' },
        coinbase: { name: 'Coinbase', type: 'crypto_exchange' },
        kalshi: { name: 'Kalshi', type: 'prediction_market' },
      }),
    });
  });

  // Mock /api/strategies (list)
  await page.route(`${API_BASE}/strategies`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        'binary_arbitrage',
        'statistical_arbitrage',
        'cross_exchange_arbitrage',
        'momentum_trading',
        'market_making',
      ]),
    });
  });
}

async function handleBotAction(route: Route, url: string, bots: typeof mockBots) {
  const botId = url.split('/bots/')[1]?.split('/')[0];
  const action = url.includes('/start') ? 'started' : url.includes('/stop') ? 'stopped' : 'paused';

  const bot = bots.find(b => b.id === botId);
  if (bot) {
    // Update bot status based on action
    const newStatus = action === 'started' ? 'running' : action === 'stopped' ? 'stopped' : 'paused';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...bot, status: newStatus }),
    });
  } else {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Bot not found' }),
    });
  }
}

async function handleBotActivity(route: Route, url: string, activity: typeof mockActivity) {
  const botId = url.split('/bots/')[1]?.split('/')[0];
  const botActivity = activity.filter(a => a.bot_id === botId);
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(botActivity),
  });
}

async function handleBotStrategies(route: Route, url: string, bots: typeof mockBots) {
  const botId = url.split('/bots/')[1]?.split('/')[0];
  const bot = bots.find(b => b.id === botId);

  if (bot) {
    const strategies = bot.strategies?.length ? bot.strategies : [{
      id: `${botId}_strategy_1`,
      bot_id: botId,
      name: bot.strategy,
      type: bot.strategy,
      status: bot.status,
      config: bot.config,
      created_at: bot.created_at,
      metrics: {
        total_executions: bot.metrics.total_trades,
        successful_executions: bot.metrics.winning_trades,
        failed_executions: bot.metrics.losing_trades,
        total_pnl: bot.metrics.total_pnl,
      },
    }];

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(strategies),
    });
  } else {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Bot not found' }),
    });
  }
}

async function handleStrategyRoutes(route: Route, bots: typeof mockBots) {
  const url = route.request().url();

  // Extract strategy ID
  const strategyId = url.split('/strategies/')[1]?.split('/')[0]?.split('?')[0];

  if (url.includes('/executions')) {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockExecutions.filter(e => e.strategy_id === strategyId || strategyId?.startsWith(e.strategy_id?.split('_')[0] || ''))),
    });
    return;
  }

  if (url.includes('/workflow')) {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...mockWorkflow, strategy_id: strategyId }),
    });
    return;
  }

  if (url.includes('/start') || url.includes('/pause')) {
    const action = url.includes('/start') ? 'started' : 'paused';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: action }),
    });
    return;
  }

  // Get single strategy
  for (const bot of bots) {
    if (strategyId === `${bot.id}_strategy_1`) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: strategyId,
          bot_id: bot.id,
          name: bot.strategy,
          type: bot.strategy,
          status: bot.status,
          config: bot.config,
          created_at: bot.created_at,
        }),
      });
      return;
    }

    for (const strategy of bot.strategies || []) {
      if (strategy.id === strategyId) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(strategy),
        });
        return;
      }
    }
  }

  await route.fulfill({
    status: 404,
    contentType: 'application/json',
    body: JSON.stringify({ error: 'Strategy not found' }),
  });
}

/**
 * Setup emergency control mocks
 */
export async function setupEmergencyMocks(page: Page, state = mockEmergencyState) {
  // The emergency page uses local state, but we can mock any API calls it might make
  await page.route(`${API_BASE}/emergency*`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state),
    });
  });
}

/**
 * Mock WebSocket connection
 * Note: This mocks the Socket.IO transport at the network level
 */
export async function mockWebSocket(page: Page) {
  // Intercept Socket.IO polling transport
  await page.route('**/socket.io/*', async (route) => {
    const url = route.request().url();

    // Handle Socket.IO handshake
    if (url.includes('transport=polling') && !url.includes('sid=')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: '0{"sid":"mock_sid_123","upgrades":["websocket"],"pingInterval":25000,"pingTimeout":20000}',
      });
      return;
    }

    // Handle subsequent polling requests
    await route.fulfill({
      status: 200,
      contentType: 'text/plain',
      body: '2', // Socket.IO ping
    });
  });
}

/**
 * Wait for network idle (no pending requests)
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Take a screenshot with a descriptive name
 */
export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `test-results/screenshots/${name}.png`,
    fullPage: true,
  });
}

/**
 * Assert no console errors
 */
export async function assertNoConsoleErrors(page: Page) {
  const errors: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  // Return a function to check errors at the end of the test
  return () => {
    const criticalErrors = errors.filter(e =>
      !e.includes('WebSocket') && // Ignore WebSocket connection errors in tests
      !e.includes('socket.io') &&
      !e.includes('Failed to load resource') // Ignore network errors in mocked tests
    );
    return criticalErrors;
  };
}

/**
 * Fill a form field by label
 */
export async function fillByLabel(page: Page, label: string, value: string) {
  const input = page.locator(`label:has-text("${label}") + input, label:has-text("${label}") input`);
  await input.fill(value);
}

/**
 * Select dropdown option by label
 */
export async function selectByLabel(page: Page, label: string, option: string) {
  const select = page.locator(`label:has-text("${label}") + select, label:has-text("${label}") select`);
  await select.selectOption({ label: option });
}
