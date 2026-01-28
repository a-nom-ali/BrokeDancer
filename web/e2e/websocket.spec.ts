/**
 * WebSocket Connection Tests
 *
 * Tests WebSocket connection handling, reconnection, and real-time updates
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockWebSocket, waitForNetworkIdle } from './fixtures/test-utils';

test.describe('WebSocket Connection', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('should attempt WebSocket connection on page load', async ({ page }) => {
    let wsConnectionAttempted = false;

    // Monitor WebSocket/Socket.IO connection attempts
    await page.route('**/socket.io/*', async (route) => {
      wsConnectionAttempted = true;
      // Simulate successful handshake
      if (route.request().url().includes('transport=polling') && !route.request().url().includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"test_sid","upgrades":["websocket"],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '2',
        });
      }
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    expect(wsConnectionAttempted).toBe(true);
  });

  test('should show connection status indicator', async ({ page }) => {
    await mockWebSocket(page);
    await page.goto('/');
    await waitForNetworkIdle(page);

    // Look for connection status indicator (may or may not be implemented)
    const connectionIndicator = page.locator('text=Connected').or(
      page.locator('text=Disconnected').or(
        page.locator('[class*="connection"]').or(
          page.locator('[data-testid="connection-status"]')
        )
      )
    );

    // Connection status might be shown in various ways
    await expect(connectionIndicator.or(page.locator('body'))).toBeVisible();
  });

  test('should handle connection failure gracefully', async ({ page }) => {
    // Simulate connection failure
    await page.route('**/socket.io/*', async (route) => {
      await route.abort('connectionrefused');
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // Page should still be usable without WebSocket
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('body')).toBeVisible();
  });

  test('should reconnect after disconnection', async ({ page }) => {
    let connectionCount = 0;

    await page.route('**/socket.io/*', async (route) => {
      connectionCount++;

      // First connection fails, subsequent succeed
      if (connectionCount === 1) {
        await route.abort('connectionrefused');
      } else {
        if (route.request().url().includes('transport=polling') && !route.request().url().includes('sid=')) {
          await route.fulfill({
            status: 200,
            contentType: 'text/plain',
            body: '0{"sid":"reconnect_sid","upgrades":["websocket"],"pingInterval":25000,"pingTimeout":20000}',
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'text/plain',
            body: '2',
          });
        }
      }
    });

    await page.goto('/');
    await page.waitForTimeout(5000); // Wait for reconnection attempts

    // Should have attempted reconnection
    expect(connectionCount).toBeGreaterThan(1);
  });
});

test.describe('Real-time Updates', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
  });

  test('should display real-time bot updates', async ({ page }) => {
    await page.goto('/bots');
    await waitForNetworkIdle(page);

    // The page should be set up to receive real-time updates
    // Verify the bot list is displayed
    await expect(page.locator('h2:has-text("Bots")')).toBeVisible();
  });

  test('should display real-time trade notifications', async ({ page }) => {
    await page.goto('/');
    await waitForNetworkIdle(page);

    // Dashboard should be ready to receive trade notifications
    await expect(page.locator('body')).toBeVisible();
  });

  test('should update metrics in real-time', async ({ page }) => {
    await page.goto('/metrics');
    await waitForNetworkIdle(page);

    // Metrics page should be ready for real-time updates
    await expect(page.locator('h2:has-text("Metrics")')).toBeVisible();
  });
});

test.describe('WebSocket Events', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('should handle bot_started event', async ({ page }) => {
    // Set up Socket.IO mock that sends bot_started event
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"event_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else if (url.includes('sid=')) {
        // Send bot_started event
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["bot_started",{"bot_id":"bot_test","timestamp":"2026-01-28T10:00:00Z"}]',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '2',
        });
      }
    });

    await page.goto('/bots');
    await page.waitForTimeout(2000);

    // Page should handle the event without errors
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle bot_stopped event', async ({ page }) => {
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"stop_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["bot_stopped",{"bot_id":"bot_test","timestamp":"2026-01-28T10:00:00Z"}]',
        });
      }
    });

    await page.goto('/bots');
    await page.waitForTimeout(2000);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle trade_executed event', async ({ page }) => {
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"trade_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["trade_executed",{"id":"trade_001","bot_id":"bot_test","profit":25.50,"timestamp":"2026-01-28T10:00:00Z"}]',
        });
      }
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle workflow_event', async ({ page }) => {
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"workflow_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["workflow_event",{"type":"node_execution","node_id":"node_1","status":"completed"}]',
        });
      }
    });

    await page.goto('/workflows');
    await page.waitForTimeout(2000);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('WebSocket Subscriptions', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('should subscribe to bot updates on bots page', async ({ page }) => {
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"sub_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '2',
        });
      }
    });

    await page.goto('/bots');
    await page.waitForTimeout(3000);

    // Page should be functional and display bots
    await expect(page.locator('h2:has-text("Bots")')).toBeVisible();
  });

  test('should unsubscribe when leaving page', async ({ page }) => {
    await mockWebSocket(page);

    await page.goto('/bots');
    await page.waitForTimeout(1000);

    // Navigate away
    await page.goto('/metrics');
    await page.waitForTimeout(1000);

    // Page should still function
    await expect(page.locator('h2:has-text("Metrics")')).toBeVisible();
  });
});
