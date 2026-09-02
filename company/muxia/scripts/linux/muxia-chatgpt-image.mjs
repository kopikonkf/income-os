import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { PlaywrightChromiumDriver } from '../../dist/browser/playwright-driver.js';
import { detectChatGptPageState } from '../../dist/providers/chatgpt/state-detector.js';
import { enforceTabBudget, MAX_TABS_PER_PRINCIPAL } from '../../../browser/linux/tab_budget.mjs';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}
function flag(name) { return process.argv.includes(name); }
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function safeId(value) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,120}$/.test(value)) throw new Error('INVALID_JOB_ID');
  return value;
}
const COMPOSER_SELECTORS = [
  '[data-testid="prompt-textarea"]',
  '#prompt-textarea',
  'textarea[placeholder*="Message" i]',
  'textarea[placeholder*="Ask" i]',
  '[contenteditable="true"][data-lexical-editor="true"]',
];
async function acquireAndFillComposer(page, prompt, attempts = 6) {
  let lastError = 'E_COMPOSER_NOT_FOUND';
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    for (const selector of COMPOSER_SELECTORS) {
      const box = page.locator(selector).first();
      if (!await box.isVisible({ timeout: 350 }).catch(() => false)) continue;
      try {
        await box.click({ timeout: 1500 });
        await box.fill(prompt, { timeout: 2500 });
        return { box, selector, attempt };
      } catch (error) {
        lastError = String(error?.message ?? error).slice(0, 240);
      }
    }
    const state = await detectChatGptPageState(page);
    if (state.state === 'BLOCKED') throw new Error(`CHATGPT_BLOCKED:${state.reason}`);
    if (state.state === 'AUTH_REQUIRED') throw new Error('CHATGPT_AUTH_REQUIRED');
    await page.waitForTimeout(350 * attempt);
  }
  throw new Error(`CHATGPT_COMPOSER_REACQUIRE_FAILED:${lastError}`);
}
function extensionFromBytes(bytes) {
  if (bytes.subarray(0, 8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]))) return 'png';
  if (bytes.length >= 2 && bytes[0] === 0xff && bytes[1] === 0xd8) return 'jpg';
  if (bytes.length >= 12 && bytes.subarray(0,4).toString() === 'RIFF' && bytes.subarray(8,12).toString() === 'WEBP') return 'webp';
  return 'bin';
}
async function inventory(page) {
  return await page.locator('img').evaluateAll((imgs) => imgs.map((e, i) => ({
    i,
    src: e.currentSrc || e.src || '',
    width: e.naturalWidth || 0,
    height: e.naturalHeight || 0,
    complete: e.complete,
  })).filter((x) => x.complete && x.width >= 900 && x.height >= 900 && x.src));
}
async function fetchImageBytes(page, context, src) {
  if (src.startsWith('blob:')) {
    const b64 = await page.evaluate(async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`IMAGE_FETCH_HTTP_${response.status}`);
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 32768) binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
      return btoa(binary);
    }, src);
    return { bytes: Buffer.from(b64, 'base64'), method: 'page-fetch-blob', contentType: '' };
  }
  const response = await context.request.get(src, { timeout: 30_000 });
  if (!response.ok()) throw new Error(`IMAGE_FETCH_HTTP_${response.status()}`);
  return {
    bytes: await response.body(),
    method: 'context-request-original-src',
    contentType: response.headers()['content-type'] || '',
  };
}

async function main() {
  if (flag('--help')) {
    console.log('Usage: node muxia-chatgpt-image.mjs --job-id ID (--prompt TEXT | --prompt-file FILE) [--profile chatgpt-linux-a] [--timeout-ms 600000]');
    return 0;
  }
  if (process.platform !== 'linux') throw new Error('LINUX_REQUIRED');
  if (!process.env.DISPLAY) throw new Error('HEADED_DISPLAY_REQUIRED');

  const root = path.resolve(process.env.MUXIA_ROOT || '/var/lib/muxia');
  const jobId = safeId(arg('--job-id') || `muxia-image-${Date.now()}`);
  const profileId = safeId(arg('--profile', 'chatgpt-linux-a'));
  const timeoutMs = Number(arg('--timeout-ms', '600000'));
  if (!Number.isInteger(timeoutMs) || timeoutMs < 30_000 || timeoutMs > 1_800_000) throw new Error('INVALID_TIMEOUT');
  const promptFile = arg('--prompt-file');
  const prompt = promptFile ? fs.readFileSync(promptFile, 'utf8').trim() : String(arg('--prompt') || '').trim();
  if (prompt.length < 10 || prompt.length > 12_000) throw new Error('INVALID_PROMPT_LENGTH');

  const profileDir = path.join(root, 'profiles', profileId, 'browser');
  const artifactDir = path.join(root, 'artifacts', jobId);
  const receiptDir = path.join(root, 'state', 'receipts');
  fs.mkdirSync(artifactDir, { recursive: true });
  fs.mkdirSync(receiptDir, { recursive: true });
  const receiptPath = path.join(receiptDir, `${jobId}.json`);
  const chrome = process.env.MUXIA_CHROME || '/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome';

  const receipt = {
    schema: 'die.muxia.chatgpt-image-run.v1',
    job_id: jobId,
    profile_id: profileId,
    prompt_sha256: sha256(prompt),
    prompt_submitted_by_automation: false,
    output_extracted_by_automation: false,
    credential_values_read: false,
    cookies_or_tokens_read: false,
    submission_authorized: false,
    publication_authorized: false,
    status: 'STARTED',
    started_at: new Date().toISOString(),
  };

  const driver = new PlaywrightChromiumDriver({ executablePath: chrome, headless: false, launchTimeoutMs: 30_000, shutdownTimeoutMs: 5_000 });
  try {
    const handle = await driver.launch(profileDir);
    const context = handle.browser.contexts()[0];
    const page = context.pages().find((p) => p.url().startsWith('https://chatgpt.com')) ?? context.pages()[0] ?? await context.newPage();
    await enforceTabBudget(context, { preserve: [page], maxTabs: MAX_TABS_PER_PRINCIPAL });
    await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await page.waitForTimeout(3_000);
    const initial = await detectChatGptPageState(page);
    receipt.initial_state = initial;
    if (initial.state !== 'READY') throw new Error(`CHATGPT_NOT_READY:${initial.state}:${initial.reason}`);

    const existing = new Set((await inventory(page)).map((x) => x.src));
    const composerAcquisition = await acquireAndFillComposer(page, prompt);
    const composer = composerAcquisition.box;
    receipt.composer_selector = composerAcquisition.selector;
    receipt.composer_acquisition_attempt = composerAcquisition.attempt;
    await page.waitForTimeout(250);
    let submitted = false;
    for (const selector of ['[data-testid="send-button"]', 'button[aria-label*="Send" i]', 'button[data-testid*="send" i]']) {
      const button = page.locator(selector).first();
      if (await button.isVisible({ timeout: 300 }).catch(() => false)) {
        await button.click();
        receipt.send_selector = selector;
        submitted = true;
        break;
      }
    }
    if (!submitted) {
      await composer.press('Enter');
      receipt.send_selector = 'composer-enter';
    }
    receipt.prompt_submitted_by_automation = true;
    receipt.submitted_at = new Date().toISOString();

    const deadline = Date.now() + timeoutMs;
    let candidate = null;
    while (Date.now() < deadline) {
      await page.waitForTimeout(2_000);
      const fresh = (await inventory(page)).filter((x) => !existing.has(x.src));
      if (fresh.length) { candidate = fresh[fresh.length - 1]; break; }
      const current = await detectChatGptPageState(page);
      if (current.state === 'BLOCKED') throw new Error(`CHATGPT_BLOCKED:${current.reason}`);
      if (current.state === 'AUTH_REQUIRED') throw new Error('CHATGPT_AUTH_REQUIRED');
    }
    if (!candidate) throw new Error('GENERATED_IMAGE_TIMEOUT');

    receipt.generated_image_observed = { width: candidate.width, height: candidate.height, src_scheme: candidate.src.split(':')[0] };
    const extracted = await fetchImageBytes(page, context, candidate.src);
    if (extracted.bytes.length < 50_000) throw new Error(`IMAGE_BYTES_TOO_SMALL:${extracted.bytes.length}`);
    const ext = extensionFromBytes(extracted.bytes);
    if (ext === 'bin') throw new Error('UNSUPPORTED_IMAGE_BYTES');
    const artifactPath = path.join(artifactDir, `source-original.${ext}`);
    fs.writeFileSync(artifactPath, extracted.bytes);

    receipt.output_extracted_by_automation = true;
    receipt.output_method = extracted.method;
    receipt.content_type = extracted.contentType;
    receipt.artifact_path = artifactPath;
    receipt.bytes = extracted.bytes.length;
    receipt.sha256 = sha256(extracted.bytes);
    receipt.status = 'SUCCEEDED';
    receipt.completed_at = new Date().toISOString();
  } catch (error) {
    receipt.status = 'FAILED';
    receipt.error = String(error?.message ?? error).slice(0, 1000);
    receipt.failed_at = new Date().toISOString();
  } finally {
    await driver.stop().catch(() => undefined);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  }
  console.log(JSON.stringify(receipt, null, 2));
  return receipt.status === 'SUCCEEDED' ? 0 : 2;
}

process.exitCode = await main();
