import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { PlaywrightChromiumDriver } from '../../dist/browser/playwright-driver.js';
import {
  classifyChatGptSnapshot,
  detectChatGptPageState,
  CHATGPT_STATE_DETECTOR_VERSION,
} from '../../dist/providers/chatgpt/state-detector.js';

const COMPOSER = '[data-testid="prompt-textarea"]';

function snapshot(overrides = {}) {
  return {
    url: 'https://chatgpt.com/',
    title: 'ChatGPT',
    bodyText: '',
    visibleSelectors: [],
    ...overrides,
  };
}

function browserFixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-chatgpt-state-'));
  const profileDir = path.join(root, 'profiles', 'chatgpt-a', 'browser');
  fs.mkdirSync(profileDir, { recursive: true });
  const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000 });
  t.after(async () => {
    await driver.stop();
    fs.rmSync(root, { recursive: true, force: true });
  });
  return { root, profileDir, driver };
}

test('MX-031: visible composer is READY when no higher-priority blocking signal exists', () => {
  const result = classifyChatGptSnapshot(snapshot({ visibleSelectors: [COMPOSER] }), '2026-08-27T06:00:00Z');
  assert.equal(result.state, 'READY');
  assert.equal(result.reason, 'COMPOSER_READY');
  assert.equal(result.operatorActionRequired, false);
});

test('MX-031: auth URL fails closed to AUTH_REQUIRED', () => {
  const result = classifyChatGptSnapshot(snapshot({ url: 'https://chatgpt.com/auth/login' }));
  assert.equal(result.state, 'AUTH_REQUIRED');
  assert.equal(result.reason, 'LOGIN_REQUIRED');
  assert.equal(result.operatorActionRequired, true);
});

test('MX-031: login text without composer is AUTH_REQUIRED', () => {
  const result = classifyChatGptSnapshot(snapshot({ bodyText: 'Welcome back. Log in or Sign up to continue.' }));
  assert.equal(result.state, 'AUTH_REQUIRED');
});

test('MX-031: rate-limit signal overrides composer and maps to BLOCKED', () => {
  const result = classifyChatGptSnapshot(snapshot({
    bodyText: "You've reached the current usage limit. Try again later.",
    visibleSelectors: [COMPOSER],
  }));
  assert.equal(result.state, 'BLOCKED');
  assert.equal(result.reason, 'RATE_LIMIT');
  assert.equal(result.operatorActionRequired, true);
});

test('MX-031: protection challenge body text overrides composer and maps to BLOCKED', () => {
  const result = classifyChatGptSnapshot(snapshot({
    bodyText: "Verify you're human before continuing",
    visibleSelectors: [COMPOSER],
  }));
  assert.equal(result.state, 'BLOCKED');
  assert.equal(result.reason, 'PROTECTION_CHALLENGE');
});

test('MX-031: Cloudflare-style protection title maps to BLOCKED even without body/selectors', () => {
  const result = classifyChatGptSnapshot(snapshot({ title: 'Just a moment...', bodyText: '', visibleSelectors: [] }));
  assert.equal(result.state, 'BLOCKED');
  assert.equal(result.reason, 'PROTECTION_CHALLENGE');
  assert.deepEqual(result.signals, ['protection-title']);
});

test('MX-031: account disabled and access denied map to BLOCKED', () => {
  const account = classifyChatGptSnapshot(snapshot({ bodyText: 'Your account has been disabled.' }));
  assert.equal(account.state, 'BLOCKED');
  assert.equal(account.reason, 'ACCOUNT_BLOCKED');

  const denied = classifyChatGptSnapshot(snapshot({ bodyText: 'Access denied for this request.' }));
  assert.equal(denied.state, 'BLOCKED');
  assert.equal(denied.reason, 'ACCESS_DENIED');
});

test('MX-031: unrecognized content returns UNKNOWN and requires operator action', () => {
  const result = classifyChatGptSnapshot(snapshot({ bodyText: 'Some unexpected page content.' }));
  assert.equal(result.state, 'UNKNOWN');
  assert.equal(result.reason, 'UNRECOGNIZED_PAGE');
  assert.equal(result.operatorActionRequired, true);
});

test('MX-031: detector never returns page body text in observation', () => {
  const secretLikeText = 'unexpected private-looking text 12345';
  const result = classifyChatGptSnapshot(snapshot({ bodyText: secretLikeText }));
  const serialized = JSON.stringify(result);
  assert.equal(serialized.includes(secretLikeText), false);
  assert.deepEqual(Object.keys(result).sort(), ['observedAt', 'operatorActionRequired', 'reason', 'signals', 'state', 'url'].sort());
});

test('MX-031: Playwright page integration detects local READY/AUTH/BLOCKED/UNKNOWN fixtures without provider network access', async (t) => {
  const { profileDir, driver } = browserFixture(t);
  const handle = await driver.launch(profileDir);
  const context = handle.browser.contexts()[0];
  const page = context.pages()[0] ?? await context.newPage();

  await page.setContent('<title>ChatGPT</title><main><div data-testid="prompt-textarea" contenteditable="true"></div></main>');
  let state = await detectChatGptPageState(page, '2026-08-27T06:01:00Z');
  assert.equal(state.state, 'READY');

  await page.setContent('<title>ChatGPT</title><main><a href="/auth/login">Log in</a><p>Sign up to continue</p></main>');
  state = await detectChatGptPageState(page, '2026-08-27T06:02:00Z');
  assert.equal(state.state, 'AUTH_REQUIRED');

  await page.setContent('<title>ChatGPT</title><main><p>Too many requests. Try again later.</p></main>');
  state = await detectChatGptPageState(page, '2026-08-27T06:03:00Z');
  assert.equal(state.state, 'BLOCKED');
  assert.equal(state.reason, 'RATE_LIMIT');

  await page.setContent('<title>ChatGPT</title><main><p>Unknown maintenance-like state</p></main>');
  state = await detectChatGptPageState(page, '2026-08-27T06:04:00Z');
  assert.equal(state.state, 'UNKNOWN');
});

test('MX-031: detector version is explicitly pinned', () => {
  assert.equal(CHATGPT_STATE_DETECTOR_VERSION, 'chatgpt-state-detector-v1.1');
});
