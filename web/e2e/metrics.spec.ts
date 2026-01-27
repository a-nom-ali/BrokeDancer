import { test, expect } from '@playwright/test';

test.describe('Metrics Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/metrics');
  });

  test('should display metrics header', async ({ page }) => {
    await expect(page.locator('h2:has-text("Metrics")')).toBeVisible();
    await expect(page.locator('text=Real-time performance analytics')).toBeVisible();
  });

  test('should show summary metric cards', async ({ page }) => {
    // Check for the 4 summary cards
    await expect(page.locator('text=Total Executions')).toBeVisible();
    await expect(page.locator('text=Successful')).toBeVisible();
    await expect(page.locator('text=Failed')).toBeVisible();
    await expect(page.locator('text=Avg Duration')).toBeVisible();
  });

  test('should display chart containers', async ({ page }) => {
    // Check for chart titles
    await expect(page.locator('text=Performance Over Time')).toBeVisible();
    await expect(page.locator('text=Executions by Bot')).toBeVisible();
    await expect(page.locator('text=Execution Timeline')).toBeVisible();
  });

  test('should show session summary', async ({ page }) => {
    await expect(page.locator('text=Session Summary')).toBeVisible();
    await expect(page.locator('text=Success Rate')).toBeVisible();
    await expect(page.locator('text=Events Processed')).toBeVisible();
  });
});

test.describe('Charts Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/metrics');
  });

  test('should render chart containers without errors', async ({ page }) => {
    // Charts should render (may show "No data" messages if no events)
    const chartContainers = page.locator('.recharts-wrapper, [class*="rounded-lg"][class*="border"]');
    await expect(chartContainers.first()).toBeVisible({ timeout: 5000 });
  });

  test('should show empty state for charts when no data', async ({ page }) => {
    // Check for empty state messages
    const emptyMessages = page.locator('text=No performance data, text=No execution data, text=No timeline data');
    // At least one chart might show empty state
    const hasEmptyState = await emptyMessages.count() > 0;

    // Either we have empty states or actual chart data
    if (!hasEmptyState) {
      // If no empty states, we should have chart SVGs
      const chartSvgs = page.locator('.recharts-surface');
      await expect(chartSvgs.first()).toBeVisible();
    }
  });
});
