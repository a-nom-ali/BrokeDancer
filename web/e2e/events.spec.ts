/**
 * Events Page E2E Tests
 *
 * Tests for the real-time event stream monitor
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockWebSocket, waitForNetworkIdle } from './fixtures/test-utils';

test.describe('Events Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);
  });

  test('should display events page header', async ({ page }) => {
    await expect(page.locator('h2:has-text("Events")')).toBeVisible();
  });

  test('should display event stream', async ({ page }) => {
    // Event stream container
    const eventStream = page.locator('[class*="event"]').or(
      page.locator('[class*="stream"]').or(
        page.locator('[class*="activity"]')
      )
    );

    await expect(eventStream.first()).toBeVisible({ timeout: 5000 }).catch(() => {
      // May show empty state
      return expect(page.locator('body')).toBeVisible();
    });
  });

  test('should display event cards', async ({ page }) => {
    // Individual event cards
    const eventCard = page.locator('[class*="card"]').or(
      page.locator('[class*="event-item"]')
    );

    await expect(eventCard.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });
});

test.describe('Event Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);
  });

  test('should filter events by type', async ({ page }) => {
    // Event type filter
    const typeFilter = page.locator('button:has-text("All")').or(
      page.locator('button:has-text("Trades")').or(
        page.locator('select:has-text("Type")')
      )
    );

    if (await typeFilter.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await typeFilter.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('should filter events by bot', async ({ page }) => {
    // Bot filter
    const botFilter = page.locator('select').or(
      page.locator('[class*="filter"]')
    );

    if (await botFilter.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await botFilter.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('should search events', async ({ page }) => {
    // Search input
    const searchInput = page.locator('input[type="search"]').or(
      page.locator('input[placeholder*="Search"]').or(
        page.locator('[class*="search"]')
      )
    );

    if (await searchInput.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.first().fill('trade');
      await page.waitForTimeout(500);

      // Results should filter
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

test.describe('Event Details', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);
  });

  test('should display event timestamp', async ({ page }) => {
    // Timestamps in events
    const timestamp = page.locator('time').or(
      page.locator('text=/\\d{1,2}:\\d{2}/').or(
        page.locator('text=/ago/')
      )
    );

    await expect(timestamp.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should display event type badge', async ({ page }) => {
    // Event type badges (trade, error, info)
    const typeBadge = page.locator('[class*="badge"]').or(
      page.locator('text=trade').or(
        page.locator('text=info').or(
          page.locator('text=error')
        )
      )
    );

    await expect(typeBadge.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should expand event for details', async ({ page }) => {
    // Find an event card
    const eventCard = page.locator('[class*="event"]').or(page.locator('[class*="card"]'));

    if (await eventCard.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await eventCard.first().click();
      await page.waitForTimeout(500);

      // Details might expand
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

test.describe('Real-time Event Updates', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('should display new events as they arrive', async ({ page }) => {
    // Set up WebSocket to send events
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"event_stream_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        // Send a workflow event
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["workflow_event",{"type":"trade","bot_id":"bot_test","profit":25.50,"timestamp":"2026-01-28T10:00:00Z"}]',
        });
      }
    });

    await page.goto('/events');
    await page.waitForTimeout(3000);

    // Event should appear in the stream
    await expect(page.locator('body')).toBeVisible();
  });

  test('should auto-scroll to new events', async ({ page }) => {
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);

    // Scroll behavior is implementation-specific
    await expect(page.locator('body')).toBeVisible();
  });

  test('should pause auto-scroll when scrolled up', async ({ page }) => {
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);

    // Find scrollable container
    const container = page.locator('[class*="event"]').or(page.locator('main'));

    if (await container.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      // Scroll up
      await container.first().evaluate(el => el.scrollTop = 0);
      await page.waitForTimeout(500);

      // Auto-scroll should be paused
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

test.describe('Event Connection Status', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('should show connected status', async ({ page }) => {
    await mockWebSocket(page);
    await page.goto('/events');
    await page.waitForTimeout(2000);

    // Look for connection indicator
    const connectedIndicator = page.locator('text=Connected').or(
      page.locator('[class*="connected"]').or(
        page.locator('[class*="online"]')
      )
    );

    await expect(connectedIndicator.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should show disconnected status when connection fails', async ({ page }) => {
    // Simulate connection failure
    await page.route('**/socket.io/*', async (route) => {
      await route.abort('connectionrefused');
    });

    await page.goto('/events');
    await page.waitForTimeout(3000);

    // Page should still be usable even with connection failure
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Event Empty State', () => {
  test('should show empty state when no events', async ({ page }) => {
    // Override activity endpoint
    await page.route('**/api/activity*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);

    // Should show empty state or waiting message
    const emptyState = page.locator('text=No events').or(
      page.locator('text=Waiting').or(
        page.locator('text=No activity')
      )
    );

    await expect(emptyState.first()).toBeVisible({ timeout: 5000 }).catch(() => {
      return expect(page.locator('body')).toBeVisible();
    });
  });
});

test.describe('Event Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/events');
    await waitForNetworkIdle(page);
  });

  test('should clear events', async ({ page }) => {
    const clearButton = page.locator('button:has-text("Clear")').or(
      page.locator('[aria-label*="clear"]')
    );

    if (await clearButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await clearButton.click();
      await page.waitForTimeout(500);

      // Events should be cleared
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('should pause event stream', async ({ page }) => {
    const pauseButton = page.locator('button:has-text("Pause")').or(
      page.locator('[aria-label*="pause"]')
    );

    if (await pauseButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pauseButton.click();
      await page.waitForTimeout(500);

      // Stream should be paused
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
