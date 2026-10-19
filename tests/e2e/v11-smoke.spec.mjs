import { test, expect } from '@playwright/test';

const baseURL = process.env.DEVCONSOLE_E2E_URL || 'http://127.0.0.1:19099';

test('V1 UI loads with additive V1.1 modules and Viewer default', async ({ page }) => {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.documentElement.dataset.devconsoleV11 === 'ready');

  const state = await page.evaluate(() => ({
    ready: document.documentElement.dataset.devconsoleV11,
    role: window.DevConsoleV11?.role,
    hasApi: !!window.DevConsoleV11?.api,
    hasProjects: !!window.DevConsoleV11?.projects,
    hasOperations: !!window.DevConsoleV11?.operations,
    hasTerminal: !!window.DevConsoleV11?.terminal,
    version: window.DevConsoleV11?.capabilities?.version,
  }));

  expect(state.ready).toBe('ready');
  expect(state.role).toBe('viewer');
  expect(state.version).toBe('1.1');
  expect(state.hasApi).toBeTruthy();
  expect(state.hasProjects).toBeTruthy();
  expect(state.hasOperations).toBeTruthy();
  expect(state.hasTerminal).toBeTruthy();

  const apiResult = await page.evaluate(async () => {
    const response = await fetch('/api/v1.1/capabilities', { credentials: 'same-origin' });
    return { status: response.status, data: await response.json() };
  });
  expect(apiResult.status).toBe(200);
  expect(apiResult.data.role).toBe('viewer');

  const cssLoaded = await page.evaluate(() =>
    Array.from(document.styleSheets).some((sheet) => String(sheet.href || '').includes('/static/css/v11.css'))
  );
  expect(cssLoaded).toBeTruthy();
});
