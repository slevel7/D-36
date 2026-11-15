import { test, expect } from '@playwright/test';
test('capture existing recovery baseline', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'How can Brahma help?' })).toBeVisible();
  await page.screenshot({ path: '../../docs/screenshots/baseline-home.png', fullPage: true });
  await page.getByRole('button', { name: 'Open account menu' }).click();
  await page.getByRole('button', { name: 'My Profile', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'My Profile', exact: true })).toBeVisible();
  await page.screenshot({ path: '../../docs/screenshots/baseline-profile.png', fullPage: true });
  await page.getByRole('button', { name: 'Customize', exact: true }).click();
  await page.screenshot({ path: '../../docs/screenshots/baseline-customize.png', fullPage: true });
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({ path: '../../docs/screenshots/baseline-mobile.png', fullPage: true });
});
