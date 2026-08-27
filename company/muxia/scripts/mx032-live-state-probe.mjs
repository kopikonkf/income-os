import fs from 'node:fs';
import path from 'node:path';
import { PlaywrightChromiumDriver } from '../dist/browser/playwright-driver.js';
import { detectChatGptPageState, CHATGPT_STATE_DETECTOR_VERSION } from '../dist/providers/chatgpt/state-detector.js';

const root = process.env.MUXIA_ROOT;
if (!root) throw new Error('MUXIA_ROOT_REQUIRED');

const profileId = process.env.MUXIA_PROFILE_ID ?? 'chatgpt-a';
const profileDir = path.join(path.resolve(root), 'profiles', profileId, 'browser');
fs.mkdirSync(profileDir, { recursive: true });

const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000, shutdownTimeoutMs: 5_000 });
const observedAt = new Date().toISOString();
let result;

try {
  const handle = await driver.launch(profileDir);
  const context = handle.browser.contexts()[0];
  const page = context.pages()[0] ?? await context.newPage();
  await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(2_000);
  const observation = await detectChatGptPageState(page, observedAt);
  result = {
    schema: 'die.muxia.mx032-live-state-probe.v1',
    profile_id: profileId,
    profile_dir: profileDir,
    detector_version: CHATGPT_STATE_DETECTOR_VERSION,
    browser_pid: handle.pid,
    debug_host: handle.debugHost,
    state: observation.state,
    reason: observation.reason,
    signals: observation.signals,
    operator_action_required: observation.operatorActionRequired,
    url: observation.url,
    observed_at: observation.observedAt,
    prompt_submitted: false,
    output_extracted: false,
    credential_values_read: false
  };
} catch (error) {
  result = {
    schema: 'die.muxia.mx032-live-state-probe.v1',
    profile_id: profileId,
    profile_dir: profileDir,
    detector_version: CHATGPT_STATE_DETECTOR_VERSION,
    state: 'UNKNOWN',
    reason: 'PROBE_ERROR',
    operator_action_required: true,
    observed_at: observedAt,
    prompt_submitted: false,
    output_extracted: false,
    credential_values_read: false,
    error: String(error?.message ?? error).slice(0, 500)
  };
} finally {
  await driver.stop().catch(() => undefined);
}

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
