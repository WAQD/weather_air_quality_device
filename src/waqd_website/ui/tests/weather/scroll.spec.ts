import { test, expect, type Page } from '@playwright/test';

// Use a mobile viewport for all tests — on desktop the forecast is always visible
// alongside the current weather card (2-column grid), so scrolling is never needed.
// ?day=N deep-links come from the Android widget which is a mobile/tablet feature.
const MOBILE_VIEWPORT = { width: 390, height: 844 };

async function loginAsAdmin(page: Page) {
  await page.request.post('/api/public/token', {
    form: {
      grant_type: 'password',
      username: 'admin',
      password: 'admin12345',
      remember_me: 'false',
    },
  });
}

/** Returns true when the element's top edge is within the visible viewport. */
async function isInViewport(page: Page, selector: string): Promise<boolean> {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.top < window.innerHeight && rect.bottom > 0;
  }, selector);
}

test.describe('Weather Page - Deep Link Scrolling (mobile)', () => {

  test.use({ viewport: MOBILE_VIEWPORT });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('forecast_container scrolls into view and selects today with ?day=0', async ({ page }) => {
    await page.goto('/rest/weather?day=0');
    await page.waitForLoadState('networkidle');

    const forecastContainer = page.locator('#forecast_container');
    await expect(forecastContainer).toBeAttached({ timeout: 10000 });

    await page.waitForTimeout(4000);

    expect(
      await isInViewport(page, '#forecast_container'),
      'forecast_container should be scrolled into view',
    ).toBe(true);

    // day=0 = today → first button must be selected
    const dayButtons = page.locator('#forecast_container button.card');
    await expect(dayButtons).toHaveCount(7, { timeout: 8000 });
    await expect(dayButtons.nth(0)).toHaveClass(/ring-2/, { timeout: 5000 });
  });

  test('forecast_container scrolls into view and selects day 1 (tomorrow) with ?day=1', async ({ page }) => {
    // day=1 → index 1 in the forecast array (0 = today, 1 = tomorrow)
    await page.goto('/rest/weather?day=1');
    await page.waitForLoadState('networkidle');

    const forecastContainer = page.locator('#forecast_container');
    await expect(forecastContainer).toBeAttached({ timeout: 10000 });

    await page.waitForTimeout(4000);

    // Scroll assertion
    expect(
      await isInViewport(page, '#forecast_container'),
      'forecast_container should be scrolled into view when day param provided',
    ).toBe(true);

    // Day-selection assertion: the second day button (index 1 = tomorrow) must carry
    // the 'ring-2' class that WeatherForecast.vue applies to the selected day.
    const dayButtons = page.locator('#forecast_container button.card');
    await expect(dayButtons).toHaveCount(7, { timeout: 8000 }); // 7-day forecast
    await expect(dayButtons.nth(1)).toHaveClass(/ring-2/, { timeout: 5000 });
  });

  test('page stays at top without scroll query params', async ({ page }) => {
    await page.goto('/rest/weather');
    await page.waitForLoadState('networkidle');
    // Brief pause to catch any rogue auto-scroll
    await page.waitForTimeout(1000);

    const scrollY = await page.evaluate(() => window.scrollY);
    expect(scrollY, 'page should not auto-scroll without query params').toBeLessThan(50);
  });
});

