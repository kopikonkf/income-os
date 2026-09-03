#!/usr/bin/env node
import path from 'node:path';
import { runOperatorBrowser } from '../../../browser/linux/operator_browser_core.mjs';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

const dieHome = path.resolve(arg('--die-home', '/srv/die'));
const profileId = String(arg('--profile-id', 'web-ai-shared')).trim();
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,120}$/.test(profileId)) throw new Error('INVALID_PROFILE_ID');
const profileDir = path.resolve(arg('--profile-dir', `/var/lib/muxia/profiles/${profileId}/browser`));
const statusFile = path.resolve(arg('--status-file', `/var/lib/muxia/state/${profileId}-browser-status.json`));
const browserExecutable = path.resolve(arg('--browser-executable', '/usr/bin/google-chrome-stable'));
const command = arg('--command', 'launch');
const startUrl = arg('--start-url', 'https://chatgpt.com/');
const principalId = arg('--principal-id', `muxia-${profileId}`);

const code = await runOperatorBrowser({
  dieHome,
  profileDir,
  statusFile,
  browserExecutable,
  browserClass: `MUXIA-${profileId}`,
  schema: 'die.muxia.webai-browser-runtime.v1',
  principalId,
  policy: 'provider-adapter-external-cdp-only',
  command,
  startUrl,
});
process.exitCode = code;