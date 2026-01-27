import { test, expect } from '@playwright/test';

test.describe('Bots Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/bots');
  });

  test('should display bot management header', async ({ page }) => {
    await expect(page.locator('h2:has-text("Bots")')).toBeVisible();
  });

  test('should show summary statistics', async ({ page }) => {
    // Check for metric cards
    await expect(page.locator('text=Total Bots')).toBeVisible();
    await expect(page.locator('text=Running')).toBeVisible();
    await expect(page.locator('text=Success Rate')).toBeVisible();
  });

  test('should display filter tabs', async ({ page }) => {
    await expect(page.locator('button:has-text("All")')).toBeVisible();
    await expect(page.locator('button:has-text("Running")')).toBeVisible();
    await expect(page.locator('button:has-text("Stopped")')).toBeVisible();
  });

  test('should show empty state when no bots', async ({ page }) => {
    // When no bots are connected, should show empty state
    const emptyState = page.locator('text=No bots').or(page.locator('text=No bot activity'));
    await expect(emptyState).toBeVisible({ timeout: 3000 }).catch(() => {
      // If bots exist, we should see bot cards instead
      return expect(page.locator('[class*="BotCard"]').or(page.locator('text=Start'))).toBeVisible();
    });
  });
});

test.describe('Bot Controls', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/bots');
  });

  test('should have control buttons on bot cards', async ({ page }) => {
    // Wait for any bot cards to appear
    const hasBots = await page.locator('[class*="bg-gray-800"]').count() > 0;

    if (hasBots) {
      // Check for control buttons (Start, Pause, Stop)
      const controlButtons = page.locator('button:has-text("Start"), button:has-text("Pause"), button:has-text("Stop")');
      await expect(controlButtons.first()).toBeVisible();
    }
  });
});
