import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { PlaywrightChromiumDriver } from '../../dist/browser/playwright-driver.js';

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-browser-driver-'));
  const profilesRoot = path.join(root, 'profiles');
  const profileDir = path.join(profilesRoot, 'chatgpt-a', 'browser');
  fs.mkdirSync(profileDir, { recursive: true });
  return { root, profilesRoot, profileDir };
}

function cleanupRoot(root) {
  fs.rmSync(root, { recursive: true, force: true });
}

test('MX-030: launches Chromium with dedicated profile and loopback-only debug endpoint', async (t) => {
  const { root, profilesRoot, profileDir } = fixture();
  const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000 });
  t.after(async () => {
    await driver.stop();
    cleanupRoot(root);
  });
  driver.assertProfileWithin(profilesRoot, profileDir);

  const handle = await driver.launch(profileDir);
  assert.ok(handle.pid > 0);
  assert.equal(handle.userDataDir, path.resolve(profileDir));
  assert.equal(handle.debugHost, '127.0.0.1');
  assert.match(handle.debugUrl, /^http:\/\/127\.0\.0\.1:\d+$/);

  const version = await fetch(`${handle.debugUrl}/json/version`).then((r) => {
    assert.equal(r.ok, true);
    return r.json();
  });
  assert.match(version.Browser, /Chrome|Chromium/i);

  const contexts = handle.browser.contexts();
  assert.ok(contexts.length >= 1);
  const page = contexts[0].pages()[0] ?? await contexts[0].newPage();
  await page.goto('data:text/html,<title>MUXIA-MX030</title><h1>browser-foundation</h1>', {
    waitUntil: 'load',
    timeout: 10_000,
  });
  assert.equal(await page.title(), 'MUXIA-MX030');
});

test('MX-030: browser process can stop and restart against the same persistent profile directory', async (t) => {
  const { root, profileDir } = fixture();
  const marker = path.join(profileDir, 'muxia-persistence-marker.txt');
  fs.writeFileSync(marker, 'same-profile');

  const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000 });
  t.after(async () => {
    await driver.stop();
    cleanupRoot(root);
  });

  const first = await driver.launch(profileDir);
  const firstPid = first.pid;
  const firstDebugPort = first.debugPort;
  await driver.stop();
  assert.equal(driver.activeHandle, null);
  assert.equal(fs.readFileSync(marker, 'utf8'), 'same-profile');

  const second = await driver.launch(profileDir);
  assert.ok(second.pid > 0);
  assert.equal(second.userDataDir, path.resolve(profileDir));
  assert.equal(fs.readFileSync(marker, 'utf8'), 'same-profile');
  assert.ok(second.pid !== firstPid || second.debugPort !== firstDebugPort, 'restart must create a fresh runtime endpoint/process identity');
});

test('MX-030: second launch while active fails closed', async (t) => {
  const { root, profileDir } = fixture();
  const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000 });
  t.after(async () => {
    await driver.stop();
    cleanupRoot(root);
  });
  await driver.launch(profileDir);
  await assert.rejects(() => driver.launch(profileDir), /BROWSER_ALREADY_RUNNING/);
});

test('MX-030: profile confinement rejects paths outside configured profile root', (t) => {
  const { root, profilesRoot } = fixture();
  t.after(() => cleanupRoot(root));
  const driver = new PlaywrightChromiumDriver({ headless: true });
  assert.throws(() => driver.assertProfileWithin(profilesRoot, path.join(root, 'escape', 'browser')), /BROWSER_PROFILE_OUTSIDE_ROOT/);
});
