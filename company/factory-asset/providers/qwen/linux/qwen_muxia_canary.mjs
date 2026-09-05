#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { PlaywrightChromiumDriver } from '../../../../muxia/dist/browser/playwright-driver.js';
import { enforceTabBudget, MAX_TABS_PER_PRINCIPAL } from '../../../../browser/linux/tab_budget.mjs';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

const jobId = String(arg('--job-id', '')).trim();
const promptFile = String(arg('--prompt-file', '')).trim();
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{4,120}$/.test(jobId)) throw new Error('E_JOB_ID');
if (!promptFile || !path.isAbsolute(promptFile)) throw new Error('E_PROMPT_FILE');
const prompt = fs.readFileSync(promptFile, 'utf8').trim();
if (prompt.length < 10 || prompt.length > 4000) throw new Error('E_PROMPT_LENGTH');

const profileDir = '/var/lib/muxia/profiles/chatgpt-linux-a/browser';
const providerDir = path.join('/var/lib/die/workspaces', jobId, 'provider');
const timeoutMs = 240000;
const receipt = {
  schema: 'die.factory-asset.qwen-linux-canary.v1',
  task_id: 'FA-112',
  job_id: jobId,
  provider_id: 'qwen',
  transport_class: 'BROWSER_CDP',
  transport_role: 'FALLBACK',
  primary_transport: 'SESSION_API',
  browser_runtime_owner: 'MUXIA',
  profile_id: 'chatgpt-linux-a',
  prompt_sha256: crypto.createHash('sha256').update(prompt).digest('hex'),
  prompt_submitted_by_automation: false,
  output_extracted_by_automation: false,
  credential_values_read: false,
  cookies_or_tokens_read: false,
  operator_actions_after_dispatch: 0,
  status: 'FAILED',
};

const now = () => new Date().toISOString();

function mimeAndExt(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return ['image/png', 'png'];
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return ['image/jpeg', 'jpg'];
  if (bytes.length >= 12 && bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP') return ['image/webp', 'webp'];
  throw new Error('E_IMAGE_MAGIC');
}

function providerOriginal(src) {
  if (!src.includes('cdn.qwenlm.ai/output/')) return src;
  const u = new URL(src);
  u.searchParams.delete('x-oss-process');
  return u.toString();
}

async function bodyText(page) {
  return (await page.locator('body').innerText({ timeout: 3000 }).catch(() => '')).slice(0, 16000).toLowerCase();
}

async function assertReady(page) {
  const body = await bodyText(page);
  if (['verify you are human', 'captcha', 'security verification', 'unusual activity', 'access denied'].some((x) => body.includes(x))) {
    throw new Error('E_PROTECTION_CHALLENGE');
  }
  const auth = page.locator('button:has-text("Log in"), a:has-text("Log in"), button:has-text("Sign up"), a:has-text("Sign up")');
  for (let i = 0; i < await auth.count(); i += 1) {
    if (await auth.nth(i).isVisible().catch(() => false)) throw new Error('E_AUTH_REQUIRED');
  }
}

async function acquireComposer(page) {
  const selectors = [
    'textarea[placeholder*="Ask Qwen" i]',
    'textarea',
    '[contenteditable="true"][role="textbox"]',
    '[contenteditable="true"]',
  ];
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    await assertReady(page);
    for (const selector of selectors) {
      const loc = page.locator(selector);
      for (let i = 0; i < await loc.count(); i += 1) {
        const candidate = loc.nth(i);
        if (await candidate.isVisible().catch(() => false)) return candidate;
      }
    }
    await page.waitForTimeout(250);
  }
  throw new Error('E_COMPOSER_UNAVAILABLE');
}

async function inventory(page) {
  return new Set(await page.locator('img').evaluateAll((imgs) => imgs.map((x) => x.getAttribute('src')).filter(Boolean)));
}

async function fetchBytes(page, context, src) {
  if (src.startsWith('data:image/')) {
    const payload = src.split(',', 2)[1];
    return [Buffer.from(payload, 'base64'), 'provider_data_uri_dom'];
  }
  if (src.startsWith('blob:')) {
    const b64 = await page.evaluate(async (url) => {
      const response = await fetch(url);
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return btoa(binary);
    }, src);
    return [Buffer.from(b64, 'base64'), 'provider_blob_dom'];
  }
  if (src.startsWith('http://') || src.startsWith('https://')) {
    const original = providerOriginal(src);
    const response = await context.request.get(original, { timeout: 45000 });
    if (!response.ok()) throw new Error(`E_IMAGE_FETCH_HTTP_${response.status()}`);
    return [Buffer.from(await response.body()), original !== src ? 'provider_original_cdn_url_browser_context' : 'provider_image_url_browser_context'];
  }
  throw new Error('E_IMAGE_SOURCE');
}

fs.mkdirSync(providerDir, { recursive: true, mode: 0o770 });
const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30000, shutdownTimeoutMs: 8000 });
try {
  receipt.started_at = now();
  const handle = await driver.launch(profileDir);
  const context = handle.browser.contexts()[0];
  let page = context.pages().find((p) => p.url().includes('qwen.ai')) || context.pages()[0] || await context.newPage();
  await enforceTabBudget(context, { preserve: [page], maxTabs: MAX_TABS_PER_PRINCIPAL });
  await page.goto('https://chat.qwen.ai/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2500);
  await assertReady(page);
  const composer = await acquireComposer(page);
  const baseline = await inventory(page);
  receipt.preflight_at = now();
  receipt.dispatch_started_at = now();
  await composer.fill(prompt);
  await composer.press('Enter');
  receipt.dispatch_committed_at = now();
  receipt.prompt_submitted_by_automation = true;

  const deadline = Date.now() + timeoutMs;
  let found = null;
  while (Date.now() < deadline && !found) {
    const images = page.locator('img');
    for (let i = (await images.count()) - 1; i >= 0; i -= 1) {
      const image = images.nth(i);
      const src = await image.getAttribute('src').catch(() => null);
      if (!src || baseline.has(src)) continue;
      const dimensions = await image.evaluate((e) => [e.naturalWidth || 0, e.naturalHeight || 0]).catch(() => [0, 0]);
      const qwenOutput = src.includes('cdn.qwenlm.ai/output/');
      if (!qwenOutput && (dimensions[0] < 512 || dimensions[1] < 512)) continue;
      if (qwenOutput && Math.max(...dimensions) < 400) continue;
      try {
        const [bytes, method] = await fetchBytes(page, context, src);
        const [mime, ext] = mimeAndExt(bytes);
        if (bytes.length < 10000) continue;
        found = { bytes, method, mime, ext, dimensions };
        break;
      } catch {
        // Keep scanning bounded candidates until one validates as original image bytes.
      }
    }
    if (!found) {
      await assertReady(page);
      const body = await bodyText(page);
      if (body.includes('generation failed') || body.includes('failed to generate')) throw new Error('E_PROVIDER_GENERATION_FAILED');
      await page.waitForTimeout(1000);
    }
  }
  if (!found) throw new Error('E_BOUNDED_COMPLETION_TIMEOUT');

  const outputPath = path.join(providerDir, `source-original.${found.ext}`);
  fs.writeFileSync(outputPath, found.bytes, { mode: 0o660 });
  receipt.generation_completed_at = now();
  receipt.output_extracted_by_automation = true;
  receipt.original_byte_acquisition_method = found.method;
  receipt.local_path = outputPath;
  receipt.mime = found.mime;
  receipt.bytes = found.bytes.length;
  receipt.sha256 = crypto.createHash('sha256').update(found.bytes).digest('hex');
  receipt.dom_dimensions = found.dimensions;
  receipt.status = 'PASS';
  receipt.completed_at = now();
} catch (error) {
  receipt.failure_code = String(error?.message || error).slice(0, 240);
  receipt.completed_at = now();
} finally {
  await driver.stop().catch(() => {});
  fs.writeFileSync(path.join(providerDir, 'qwen-canary-result.json'), JSON.stringify(receipt, null, 2) + '\n', { mode: 0o660 });
  console.log(JSON.stringify(receipt));
}
process.exitCode = receipt.status === 'PASS' ? 0 : 1;
