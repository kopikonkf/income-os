import fs from 'node:fs';
import path from 'node:path';
import { PlaywrightChromiumDriver } from '../../dist/browser/playwright-driver.js';
import {
  CHATGPT_STATE_DETECTOR_VERSION,
  detectChatGptPageState,
} from '../../dist/providers/chatgpt/state-detector.js';

if (process.platform !== 'linux') throw new Error('MX051_RESTART_PROOF_REQUIRES_LINUX');

const root = process.env.MUXIA_ROOT ?? '/var/lib/muxia';
const profileId = process.env.MUXIA_PROFILE_ID ?? 'chatgpt-linux-a';
const profileDir = path.join(root, 'profiles', profileId, 'browser');
const stateDir = path.join(root, 'state');
const receiptPath = path.join(stateDir, 'mx051-sanitized-state-restart.json');
const executablePath = process.env.MUXIA_CHROME
  ?? '/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome';
const headless = process.env.MUXIA_HEADLESS !== 'false';

if (!fs.existsSync(profileDir)) throw new Error(`MX051_PROFILE_NOT_FOUND:${profileDir}`);
if (!fs.existsSync(executablePath)) throw new Error(`MX051_CHROMIUM_NOT_FOUND:${executablePath}`);
fs.mkdirSync(stateDir, { recursive: true });

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function sanitizedUrl(raw) {
  try {
    const parsed = new URL(raw);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return 'about:blank';
  }
}

async function detectReady(page) {
  const deadline = Date.now() + 30_000;
  let last;
  while (Date.now() < deadline) {
    last = await detectChatGptPageState(page, new Date().toISOString());
    if (last.state === 'READY') return last;
    if (last.state === 'AUTH_REQUIRED' || last.state === 'BLOCKED') return last;
    await sleep(1_000);
  }
  return last ?? {
    state: 'UNKNOWN',
    reason: 'UNRECOGNIZED_PAGE',
    url: page.url(),
    observedAt: new Date().toISOString(),
    signals: ['no-observation'],
    operatorActionRequired: true,
  };
}

async function openAndObserve(driver) {
  const handle = await driver.launch(profileDir);
  const context = handle.browser.contexts()[0];
  if (!context) throw new Error('MX051_BROWSER_CONTEXT_MISSING');
  const pages = context.pages();
  const page = pages[0] ?? await context.newPage();
  await page.goto('https://chatgpt.com/', {
    waitUntil: 'domcontentloaded',
    timeout: 60_000,
  });
  const observation = await detectReady(page);
  return {
    browser_pid: handle.pid,
    debug_host: handle.debugHost,
    debug_port_ephemeral: handle.debugPort > 0,
    debug_loopback_only: handle.debugHost === '127.0.0.1',
    state: observation.state,
    reason: observation.reason,
    signals: [...observation.signals],
    url: sanitizedUrl(observation.url),
    operator_action_required: observation.operatorActionRequired,
    observed_at: observation.observedAt,
  };
}

const driver = new PlaywrightChromiumDriver({
  executablePath,
  headless,
  launchTimeoutMs: 30_000,
  shutdownTimeoutMs: 8_000,
});

let first;
let second;
try {
  first = await openAndObserve(driver);
  if (first.state !== 'READY') throw new Error(`MX051_FIRST_STATE_NOT_READY:${first.state}:${first.reason}`);
  await driver.stop();
  second = await openAndObserve(driver);
  if (second.state !== 'READY') throw new Error(`MX051_RESTART_STATE_NOT_READY:${second.state}:${second.reason}`);
  if (first.browser_pid === second.browser_pid) throw new Error('MX051_PROCESS_IDENTITY_DID_NOT_CHANGE');
} finally {
  await driver.stop().catch(() => undefined);
}

const receipt = {
  schema: 'die.muxia.mx051.sanitized-state-restart.v1',
  task_id: 'MX-051',
  status: 'PASS',
  profile_id: profileId,
  profile_dir: profileDir,
  detector_version: CHATGPT_STATE_DETECTOR_VERSION,
  rendering_mode: headless ? 'HEADLESS' : 'HEADED_OPERATOR_SESSION',
  first_observation: first,
  post_restart_observation: second,
  acceptance: {
    first_state_ready: first?.state === 'READY',
    post_restart_state_ready: second?.state === 'READY',
    same_profile_reused: true,
    browser_process_identity_changed: first?.browser_pid !== second?.browser_pid,
    debug_loopback_only: first?.debug_loopback_only === true && second?.debug_loopback_only === true,
  },
  credential_values_read: false,
  cookies_or_tokens_read: false,
  prompt_submitted: false,
  output_extracted: false,
  bypass_attempted: false,
  completed_at: new Date().toISOString(),
};
if (!Object.values(receipt.acceptance).every(Boolean)) {
  throw new Error(`MX051_RESTART_ACCEPTANCE_FAILED:${JSON.stringify(receipt.acceptance)}`);
}
fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
console.log(JSON.stringify(receipt, null, 2));
