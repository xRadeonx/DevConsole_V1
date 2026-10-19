import { test, expect } from '@playwright/test';

const baseURL = process.env.DEVCONSOLE_E2E_URL || 'http://127.0.0.1:19099';
const devPin = process.env.DEVCONSOLE_E2E_DEV_PIN || 'devconsole-e2e-dev';
const adminPin = process.env.DEVCONSOLE_E2E_ADMIN_PIN || 'devconsole-e2e-admin';

async function api(page, path, options = {}) {
  return page.evaluate(async ({ path, options }) => {
    const response = await fetch(path, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const text = await response.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    return { status: response.status, data };
  }, { path, options });
}

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

  const apiResult = await api(page, '/api/v1.1/capabilities');
  expect(apiResult.status).toBe(200);
  expect(apiResult.data.role).toBe('viewer');

  const cssLoaded = await page.evaluate(() =>
    Array.from(document.styleSheets).some((sheet) => String(sheet.href || '').includes('/static/css/v11.css'))
  );
  expect(cssLoaded).toBeTruthy();
});

test('role escalation requires explicit product credentials', async ({ page }) => {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.documentElement.dataset.devconsoleV11 === 'ready');

  const viewerProjects = await api(page, '/api/v1.1/projects');
  expect(viewerProjects.status).toBe(403);
  expect(viewerProjects.data.required_role).toBe('dev');

  const badDev = await api(page, '/api/auth/verify_pin', {
    method: 'POST',
    body: JSON.stringify({ role: 'dev', pin: 'wrong-pin' }),
  });
  expect(badDev.status).toBe(401);

  const devLogin = await api(page, '/api/auth/verify_pin', {
    method: 'POST',
    body: JSON.stringify({ role: 'dev', pin: devPin }),
  });
  expect(devLogin.status).toBe(200);
  expect(devLogin.data.role).toBe('dev');

  await page.evaluate(() => window.DevConsoleV11.refreshCapabilities());
  await expect.poll(() => page.evaluate(() => window.DevConsoleV11.role)).toBe('dev');
  const devProjects = await api(page, '/api/v1.1/projects');
  expect(devProjects.status).toBe(200);

  const logout = await api(page, '/api/auth/logout', {
    method: 'POST',
    body: JSON.stringify({}),
  });
  expect(logout.status).toBe(200);
  await page.evaluate(() => window.DevConsoleV11.refreshCapabilities());
  await expect.poll(() => page.evaluate(() => window.DevConsoleV11.role)).toBe('viewer');

  const badAdmin = await api(page, '/api/auth/verify_pin', {
    method: 'POST',
    body: JSON.stringify({ role: 'admin', pin: 'wrong-pin' }),
  });
  expect(badAdmin.status).toBe(401);

  const adminLogin = await api(page, '/api/auth/verify_pin', {
    method: 'POST',
    body: JSON.stringify({ role: 'admin', pin: adminPin }),
  });
  expect(adminLogin.status).toBe(200);
  expect(adminLogin.data.role).toBe('admin');

  await page.evaluate(() => window.DevConsoleV11.refreshCapabilities());
  await expect.poll(() => page.evaluate(() => window.DevConsoleV11.role)).toBe('admin');
});
