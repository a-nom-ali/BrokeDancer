import { test, expect } from '@playwright/test';

test.describe('Emergency Control Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/emergency');
  });

  test('should display emergency state', async ({ page }) => {
    await expect(page.locator('text=Emergency State')).toBeVisible();
    // Should show one of the states: NORMAL, ALERT, HALT, SHUTDOWN
    const stateIndicator = page.locator('text=NORMAL, text=ALERT, text=HALT, text=SHUTDOWN');
    await expect(stateIndicator.first()).toBeVisible();
  });

  test('should display manual control buttons', async ({ page }) => {
    await expect(page.locator('text=Manual Controls')).toBeVisible();
    await expect(page.locator('button:has-text("Emergency Halt")')).toBeVisible();
    await expect(page.locator('button:has-text("Set Alert")')).toBeVisible();
    await expect(page.locator('button:has-text("Resume Normal")')).toBeVisible();
  });

  test('should display trading status indicators', async ({ page }) => {
    await expect(page.locator('text=Can Trade')).toBeVisible();
    await expect(page.locator('text=Can Operate')).toBeVisible();
  });

  test('should display risk limits section', async ({ page }) => {
    await expect(page.locator('text=Risk Limits')).toBeVisible();
  });

  test('should display emergency event history', async ({ page }) => {
    await expect(page.locator('text=Emergency Event History')).toBeVisible();
  });
});

test.describe('Emergency Controls Interaction', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/emergency');
  });

  test('should change state when Emergency Halt is clicked', async ({ page }) => {
    // Find and click the Emergency Halt button (if not already in HALT state)
    const haltButton = page.locator('button:has-text("Emergency Halt")');

    if (await haltButton.isEnabled()) {
      await haltButton.click();
      // After clicking, the state should change to HALT
      await expect(page.locator('text=HALT')).toBeVisible({ timeout: 2000 });
    }
  });

  test('should change state when Resume Normal is clicked', async ({ page }) => {
    // First trigger an alert or halt
    const alertButton = page.locator('button:has-text("Set Alert")');
    if (await alertButton.isEnabled()) {
      await alertButton.click();
      await expect(page.locator('text=ALERT')).toBeVisible({ timeout: 2000 });
    }

    // Then resume
    const resumeButton = page.locator('button:has-text("Resume Normal")');
    if (await resumeButton.isEnabled()) {
      await resumeButton.click();
      await expect(page.locator('text=NORMAL')).toBeVisible({ timeout: 2000 });
    }
  });
});
