#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const dieHome = process.env.DIE_HOME || '/srv/die';
const profileDir = process.env.DIE_EXECUTIVE_BROWSER_PROFILE || '/var/lib/die/executive/browser-profile';
const browserRoot = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/muxia/playwright-browsers';
const statusFile = process.env.DIE_EXECUTIVE_BROWSER_STATUS || '/var/lib/die/executive/browser-status.json';
const playwrightEntry = path.join(dieHome, 'company', 'muxia', 'node_modules', 'playwright', 'index.mjs');
const command = process.argv[2] || 'probe';

if (!path.isAbsolute(dieHome) || !path.isAbsolute(profileDir) || !path.isAbsolute(browserRoot) || !path.isAbsolute(statusFile)) {
  console.error('E_ABSOLUTE_PATH_REQUIRED');
  process.exit(2);
}
if (!fs.existsSync(playwrightEntry)) {
  console.error(`E_PLAYWRIGHT_MISSING:${playwrightEntry}`);
  process.exit(2);
}
fs.mkdirSync(profileDir, { recursive: true, mode: 0o700 });
process.env.PLAYWRIGHT_BROWSERS_PATH = browserRoot;

const { chromium } = await import(pathToFileURL(playwrightEntry).href);

async function classify(page) {
  const url = page.url();
  const title = await page.title().catch(() => '');
  const editableCount = await page.locator('textarea, [contenteditable="true"]').count().catch(() => 0);
  const loginButtonCount = await page.getByRole('button', { name: /log in/i }).count().catch(() => 0);
  const loginLinkCount = await page.getByRole('link', { name: /log in/i }).count().catch(() => 0);
  const loginUiCount = loginButtonCount + loginLinkCount;
  let state = 'UNKNOWN';
  if (/auth|login|signup/i.test(url) || loginUiCount > 0) state = 'AUTH_REQUIRED';
  else if (url.startsWith('https://chatgpt.com') && editableCount > 0) state = 'READY';
  else if (url.startsWith('https://chatgpt.com')) state = 'OPERATOR_CHECK_REQUIRED';
  return { state, url, title, editableCount, loginUiCount };
}

const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  viewport: null,
});
let page = context.pages().find((p) => p.url().startsWith('https://chatgpt.com'));
if (!page) page = await context.newPage();
if (!page.url().startsWith('https://chatgpt.com')) {
  await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
}
await page.bringToFront();
await page.waitForTimeout(3000);
function statusPayload(status) {
  return {
    schema: 'die.executive.operator-browser.v1',
    principal_id: 'chatgpt-plus-executive',
    policy: 'operator-controlled-acquisition-only',
    profile: profileDir,
    observed_at: new Date().toISOString(),
    ...status,
  };
}
function writeStatus(status) {
  const payload = statusPayload(status);
  fs.mkdirSync(path.dirname(statusFile), { recursive: true, mode: 0o750 });
  const tmp = `${statusFile}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(payload) + '\n', { mode: 0o640 });
  fs.renameSync(tmp, statusFile);
  return payload;
}

const status = await classify(page);
console.log(JSON.stringify(writeStatus(status)));

if (command === 'probe') {
  await context.close();
  process.exit(status.state === 'READY' ? 0 : 3);
}
if (command !== 'launch') {
  await context.close();
  console.error('E_COMMAND: use probe|launch');
  process.exit(2);
}

console.error('Executive browser opened. Login/recovery and any prompt submission remain operator-controlled.');
console.error('No cookies, tokens, private backend calls, prompt submission, or output extraction are performed by this launcher.');
const timer = setInterval(async () => {
  const current = await classify(page).catch(() => ({ state: 'UNKNOWN', url: page.url(), title: '', editableCount: 0, loginUiCount: 0 }));
  writeStatus(current);
}, 5000);
await new Promise((resolve) => {
  const done = () => resolve();
  process.once('SIGINT', done);
  process.once('SIGTERM', done);
  context.on('close', done);
});
clearInterval(timer);
await context.close().catch(() => {});
