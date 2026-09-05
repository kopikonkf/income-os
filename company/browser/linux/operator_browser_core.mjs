#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { enforceTabBudget, MAX_TABS_PER_PRINCIPAL } from './tab_budget.mjs';

const DEVTOOLS_ACTIVE_PORT = 'DevToolsActivePort';

export function sanitizeStatusUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return '';
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRunning(child) {
  return child.exitCode === null && child.signalCode === null;
}

async function waitForDevToolsPort(profileDir, child, timeoutMs = 20000) {
  const portFile = path.join(profileDir, DEVTOOLS_ACTIVE_PORT);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!isRunning(child)) throw new Error(`E_BROWSER_EXITED:${child.exitCode ?? child.signalCode ?? 'unknown'}`);
    if (fs.existsSync(portFile)) {
      const firstLine = fs.readFileSync(portFile, 'utf8').split(/\r?\n/, 1)[0]?.trim();
      const port = Number.parseInt(firstLine || '', 10);
      if (Number.isInteger(port) && port > 0 && port <= 65535) return port;
    }
    await sleep(100);
  }
  throw new Error('E_DEVTOOLS_PORT_TIMEOUT');
}

async function settleClose(browser, child) {
  try {
    const session = await browser.newBrowserCDPSession();
    await session.send('Browser.close');
  } catch {
    // Connection may already be gone. Process termination below is authoritative.
  }
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline && isRunning(child)) await sleep(100);
  if (isRunning(child)) {
    try { child.kill('SIGTERM'); } catch {}
  }
}

export async function runOperatorBrowser(options) {
  const {
    dieHome,
    profileDir,
    statusFile,
    browserExecutable,
    browserClass,
    schema,
    principalId,
    policy = 'operator-controlled-acquisition-only',
    command = 'probe',
    startUrl = 'https://chatgpt.com/',
  } = options;

  for (const value of [dieHome, profileDir, statusFile, browserExecutable]) {
    if (!path.isAbsolute(value)) throw new Error('E_ABSOLUTE_PATH_REQUIRED');
  }
  if (!fs.existsSync(browserExecutable)) throw new Error(`E_BROWSER_EXECUTABLE_MISSING:${browserExecutable}`);
  const playwrightEntry = path.join(dieHome, 'company', 'muxia', 'node_modules', 'playwright', 'index.mjs');
  if (!fs.existsSync(playwrightEntry)) throw new Error(`E_PLAYWRIGHT_MISSING:${playwrightEntry}`);
  if (!['probe', 'launch'].includes(command)) throw new Error('E_COMMAND: use probe|launch');

  fs.mkdirSync(profileDir, { recursive: true, mode: 0o700 });
  fs.rmSync(path.join(profileDir, DEVTOOLS_ACTIVE_PORT), { force: true });

  const args = [
    `--user-data-dir=${profileDir}`,
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=0',
    '--no-first-run',
    '--no-default-browser-check',
  ];
  if (browserClass) args.push(`--class=${browserClass}`);
  args.push(startUrl);

  const child = spawn(browserExecutable, args, {
    stdio: 'ignore',
    windowsHide: true,
    env: process.env,
  });
  if (!child.pid) throw new Error('E_BROWSER_PID_MISSING');

  let browser = null;
  try {
    const debugPort = await waitForDevToolsPort(profileDir, child);
    const debugUrl = `http://127.0.0.1:${debugPort}`;
    const { chromium } = await import(pathToFileURL(playwrightEntry).href);
    browser = await chromium.connectOverCDP(debugUrl, { timeout: 20000 });
    const context = browser.contexts()[0];
    if (!context) throw new Error('E_BROWSER_CONTEXT_MISSING');
    let page = context.pages().find((p) => p.url().startsWith('https://chatgpt.com')) || context.pages()[0];
    if (!page) page = await context.newPage();
    await enforceTabBudget(context, { preserve: [page], maxTabs: MAX_TABS_PER_PRINCIPAL });
    if (!page.url().startsWith('https://chatgpt.com')) {
      await page.goto(startUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    }
    await page.bringToFront();
    await page.waitForTimeout(2500);

    async function classify() {
      const rawUrl = page.url();
      const url = sanitizeStatusUrl(rawUrl);
      const title = await page.title().catch(() => '');
      const editableCount = await page.locator('textarea, [contenteditable="true"]').count().catch(() => 0);
      const loginButtonCount = await page.getByRole('button', { name: /log in/i }).count().catch(() => 0);
      const loginLinkCount = await page.getByRole('link', { name: /log in/i }).count().catch(() => 0);
      const loginUiCount = loginButtonCount + loginLinkCount;
      let state = 'UNKNOWN';
      if (/auth|login|signup/i.test(rawUrl) || loginUiCount > 0) state = 'AUTH_REQUIRED';
      else if (rawUrl.startsWith('https://chatgpt.com') && editableCount > 0) state = 'READY';
      else if (rawUrl.startsWith('https://chatgpt.com')) state = 'OPERATOR_CHECK_REQUIRED';
      return { state, url, title, editableCount, loginUiCount, browserPid: child.pid, debugHost: '127.0.0.1', debugPort };
    }

    function writeStatus(status) {
      const payload = {
        schema,
        principal_id: principalId,
        policy,
        profile: profileDir,
        browser_executable: browserExecutable,
        launch_mode: 'DIRECT_SPAWN_LOOPBACK_CDP',
        observed_at: new Date().toISOString(),
        ...status,
        url: sanitizeStatusUrl(status?.url),
      };
      fs.mkdirSync(path.dirname(statusFile), { recursive: true, mode: 0o750 });
      const tmp = `${statusFile}.tmp`;
      fs.writeFileSync(tmp, JSON.stringify(payload) + '\n', { mode: 0o640 });
      fs.renameSync(tmp, statusFile);
      return payload;
    }

    let status = await classify();
    console.log(JSON.stringify(writeStatus(status)));

    if (command === 'probe') {
      await settleClose(browser, child);
      return status.state === 'READY' ? 0 : 3;
    }

    console.error(`${principalId} browser opened using direct-spawn Chrome and loopback CDP observation.`);
    console.error('Login/recovery and any prompt submission remain operator-controlled; no cookies, tokens, private backend calls, prompt submission, or output extraction are performed.');

    const timer = setInterval(async () => {
      await enforceTabBudget(context, { preserve: [page], maxTabs: MAX_TABS_PER_PRINCIPAL }).catch(() => {});
      status = await classify().catch(() => ({ state: 'UNKNOWN', url: sanitizeStatusUrl(page.url()), title: '', editableCount: 0, loginUiCount: 0, browserPid: child.pid, debugHost: '127.0.0.1', debugPort }));
      writeStatus(status);
    }, 5000);

    await new Promise((resolve) => {
      const done = () => resolve();
      process.once('SIGINT', done);
      process.once('SIGTERM', done);
      child.once('exit', done);
      browser.on('disconnected', done);
    });
    clearInterval(timer);
    await settleClose(browser, child);
    return 0;
  } catch (error) {
    if (browser) await settleClose(browser, child).catch(() => {});
    else if (isRunning(child)) {
      try { child.kill('SIGTERM'); } catch {}
    }
    throw error;
  }
}
