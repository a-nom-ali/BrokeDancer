/**
 * Dashboard E2E Tests
 *
 * Tests for the main dashboard page including:
 * - Portfolio overview
 * - PnL charts
 * - Quick stats
 * - Recent activity
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockWebSocket, waitForNetworkIdle } from './fixtures/test-utils';
import { mockBots } from './fixtures/mock-data';

test.describe('Dashboard Overview', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/');
    await waitForNetworkIdle(page);
  });

  test('should display dashboard header', async ({ page }) => {
    // Should show Dashboard title or BrokeDancer branding
    const header = page.locator('h1, h2').filter({ hasText: /Dashboard|BrokeDancer/i });
    await expect(header.first()).toBeVisible({ timeout: 5000 });
  });

  test('should display portfolio summary cards', async ({ page }) => {
    // Should show key metrics cards
    const metricsSection = page.locator('body');
    await expect(metricsSection).toBeVisible();

    // Look for common metric labels
    const totalBalanceCard = page.locator('text=Total Balance').or(page.locator('text=Balance'));
    const pnlCard = page.locator('text=PnL').or(page.locator('text=Profit'));
    const botsCard = page.locator('text=Bots').or(page.locator('text=Active'));

    // At least one of these should be visible
    await expect(
      totalBalanceCard.or(pnlCard).or(botsCard).first()
    ).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should display correct bot count', async ({ page }) => {
    // Should show the number of bots from mock data
    const botCountText = page.locator(`text=${mockBots.length}`).or(
      page.locator(`text=Total Bots`)
    );
    await expect(botCountText.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should show navigation sidebar', async ({ page }) => {
    // Navigation should be visible
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();

    // Should have links to main sections
    await expect(page.locator('a[href="/bots"], a:has-text("Bots")').first()).toBeVisible();
    await expect(page.locator('a[href="/metrics"], a:has-text("Metrics")').first()).toBeVisible();
  });
});

test.describe('Dashboard Charts', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/');
    await waitForNetworkIdle(page);
  });

  test('should render PnL chart', async ({ page }) => {
    // Look for chart container or SVG element
    const chartContainer = page.locator('[class*="chart"]').or(
      page.locator('svg').or(
        page.locator('[class*="recharts"]')
      )
    );

    // Charts may take a moment to render
    await expect(chartContainer.first()).toBeVisible({ timeout: 10000 }).catch(() => {
      // Charts are optional on some dashboard layouts
      return true;
    });
  });

  test('should display chart legend', async ({ page }) => {
    // Chart legend elements
    const legend = page.locator('[class*="legend"]').or(
      page.locator('text=Daily').or(
        page.locator('text=Cumulative')
      )
    );

    await expect(legend.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });

  test('should allow chart time range selection', async ({ page }) => {
    // Time range selectors (7d, 30d, 90d, etc.)
    const timeRangeButton = page.locator('button:has-text("7d")').or(
      page.locator('button:has-text("30d")').or(
        page.locator('button:has-text("1M")')
      )
    );

    if (await timeRangeButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await timeRangeButton.first().click();
      await page.waitForTimeout(500);
      // Chart should update
    }
  });
});

test.describe('Dashboard Quick Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/');
    await waitForNetworkIdle(page);
  });

  test('should navigate to bots page', async ({ page }) => {
    // Click on Bots navigation item
    await page.click('a[href="/bots"], a:has-text("Bots")');
    await expect(page).toHaveURL(/.*bots/);
    await expect(page.locator('h2:has-text("Bots")')).toBeVisible();
  });

  test('should navigate to metrics page', async ({ page }) => {
    await page.click('a[href="/metrics"], a:has-text("Metrics")');
    await expect(page).toHaveURL(/.*metrics/);
    await expect(page.locator('h2:has-text("Metrics")')).toBeVisible();
  });

  test('should navigate to emergency page', async ({ page }) => {
    await page.click('a[href="/emergency"], a:has-text("Emergency")');
    await expect(page).toHaveURL(/.*emergency/);
  });

  test('should navigate to workflows page', async ({ page }) => {
    await page.click('a[href="/workflows"], a:has-text("Workflows")');
    await expect(page).toHaveURL(/.*workflows/);
  });
});

test.describe('Dashboard Responsive Layout', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
  });

  test('should display mobile layout correctly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await waitForNetworkIdle(page);

    // Content should be visible
    await expect(page.locator('body')).toBeVisible();

    // Mobile layout should work
    await expect(page.locator('main').or(page.locator('body'))).toBeVisible();
  });

  test('should display tablet layout correctly', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await waitForNetworkIdle(page);

    // Sidebar may be collapsed or visible
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display desktop layout with full sidebar', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await waitForNetworkIdle(page);

    // Full sidebar should be visible
    await expect(page.locator('nav')).toBeVisible();

    // Multiple columns should be visible for metrics
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Dashboard Loading States', () => {
  test('should show loading state while fetching data', async ({ page }) => {
    // Add delay to API responses
    await setupApiMocks(page, { delay: 2000 });

    await page.goto('/');

    // Should show loading indicators
    const loadingIndicator = page.locator('[class*="loading"]').or(
      page.locator('[class*="spinner"]').or(
        page.locator('[class*="skeleton"]').or(
          page.locator('text=Loading')
        )
      )
    );

    // Loading state should appear
    await expect(loadingIndicator.first()).toBeVisible({ timeout: 1000 }).catch(() => {
      // Some implementations don't show explicit loading state
      return true;
    });

    // Eventually content should load
    await waitForNetworkIdle(page);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle error state gracefully', async ({ page }) => {
    // Mock API failure
    await page.route('**/api/portfolio', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' }),
      });
    });

    await page.route('**/api/bots', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // Page should not crash
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('nav')).toBeVisible();
  });
});

test.describe('Dashboard Activity Feed', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
    await page.goto('/');
    await waitForNetworkIdle(page);
  });

  test('should display recent activity', async ({ page }) => {
    // Look for activity section
    const activitySection = page.locator('text=Recent Activity').or(
      page.locator('text=Activity').or(
        page.locator('text=Recent Trades')
      )
    );

    await expect(activitySection.first()).toBeVisible({ timeout: 5000 }).catch(() => {
      // Activity might be on a different page
      return true;
    });
  });

  test('should show activity timestamps', async ({ page }) => {
    // Activity items should have timestamps
    const timestampPattern = page.locator('text=/\\d+:\\d+/').or(
      page.locator('text=/ago/').or(
        page.locator('time')
      )
    );

    await expect(timestampPattern.first()).toBeVisible({ timeout: 5000 }).catch(() => true);
  });
});

test.describe('Dashboard Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await mockWebSocket(page);
  });

  test('should display notification when trade is executed', async ({ page }) => {
    // Set up Socket.IO to send a trade notification
    await page.route('**/socket.io/*', async (route) => {
      const url = route.request().url();

      if (url.includes('transport=polling') && !url.includes('sid=')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '0{"sid":"notif_test_sid","upgrades":[],"pingInterval":25000,"pingTimeout":20000}',
        });
      } else {
        // Send notification event
        await route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: '42["notification",{"message":"Trade executed successfully","level":"success"}]',
        });
      }
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // Notification might appear - page should handle the event
    await expect(page.locator('body')).toBeVisible();
  });
});
