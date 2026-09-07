import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  acquireClusterTab,
  connectLeasedClusterTab,
  fetchClusterLeases,
  markClusterTab,
  releaseClusterTab,
  setClusterProviderState,
} from '../../browser/linux/cluster_broker_client.mjs';
import { classifyProviderPage } from '../../browser/linux/provider_readiness.mjs';

const PROVIDER_STATES = new Set(['HEALTHY', 'DEGRADED', 'AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);
const SAFE_ERROR_LIMIT = 480;

function sha256(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function atomicJson(file, value) {
  if (!file) return;
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o640 });
  fs.renameSync(tmp, file);
}
function nowIso() { return new Date().toISOString(); }
function safeUrl(raw) {
  try { const u = new URL(raw); return `${u.origin}${u.pathname}`; } catch { return ''; }
}
function safeError(error) {
  let text = String(error?.message || error || 'E_UNKNOWN').replace(/https?:\/\/[^\s"']+/g, (raw) => safeUrl(raw) || 'URL_REDACTED');
  text = text.replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim();
  return text.slice(0, SAFE_ERROR_LIMIT);
}
function detectImageFormat(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return { ext: 'png', mime: 'image/png' };
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return { ext: 'jpg', mime: 'image/jpeg' };
  if (bytes.length >= 12 && bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP') return { ext: 'webp', mime: 'image/webp' };
  throw new Error('E_IMAGE_MAGIC');
}
async function bodyText(page) { return (await page.locator('body').innerText({ timeout: 3000 }).catch(() => '')).slice(0, 18000).toLowerCase(); }
function classifyFailure(message, body = '') {
  const text = `${message} ${body}`.toLowerCase();
  if (text.includes('rate limit') || text.includes('too many requests') || text.includes('usage limit') || text.includes('try again later') || text.includes('reached your limit')) return 'RATE_LIMITED';
  if (text.includes('auth_required') || text.includes('log in') || text.includes('sign in')) return 'AUTH_REQUIRED';
  if (text.includes('checkpoint') || text.includes('captcha') || text.includes('verify you are human') || text.includes('security check') || text.includes('protection')) return 'CHECKPOINT';
  if (text.includes('timeout')) return 'PROVIDER_TIMEOUT';
  if (text.includes('not schedulable') || text.includes('tab_capacity') || text.includes('cluster_tab_capacity')) return 'CAPACITY_UNAVAILABLE';
  return 'PROVIDER_ERROR';
}
async function inventoryImages(page, providerId) {
  const rows = await page.locator('img').evaluateAll((imgs) => imgs.map((e) => ({
    src: e.currentSrc || e.src || '',
    width: e.naturalWidth || 0,
    height: e.naturalHeight || 0,
    complete: Boolean(e.complete),
  })).filter((x) => x.complete && x.src));
  if (providerId === 'chatgpt') return rows.filter((x) => x.width >= 900 && x.height >= 900);
  return rows;
}
async function fetchImageBytes(page, context, src, providerId) {
  if (src.startsWith('data:image/')) {
    const idx = src.indexOf(',');
    if (idx < 0) throw new Error('E_IMAGE_DATA_URI');
    return { bytes: Buffer.from(src.slice(idx + 1), 'base64'), method: 'provider_data_uri_dom' };
  }
  if (src.startsWith('blob:')) {
    const b64 = await page.evaluate(async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`E_IMAGE_FETCH_HTTP_${response.status}`);
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = '';
      for (let i = 0; i < bytes.length; i += 32768) binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
      return btoa(binary);
    }, src);
    return { bytes: Buffer.from(b64, 'base64'), method: 'provider_blob_dom' };
  }
  if (src.startsWith('https://') || src.startsWith('http://')) {
    let target = src;
    if (providerId === 'qwen' && src.includes('cdn.qwenlm.ai/output/')) {
      const u = new URL(src);
      u.searchParams.delete('x-oss-process');
      target = u.toString();
    }
    const response = await context.request.get(target, { timeout: 45000 });
    if (!response.ok()) throw new Error(`E_IMAGE_FETCH_HTTP_${response.status()}`);
    return { bytes: Buffer.from(await response.body()), method: target !== src ? 'provider_original_cdn_url_browser_context' : 'provider_image_url_browser_context' };
  }
  throw new Error('E_IMAGE_SOURCE');
}
async function fillAndSubmitChatGpt(page, prompt) {
  const selectors = ['[data-testid="prompt-textarea"]', '#prompt-textarea', 'textarea[placeholder*="Message" i]', 'textarea[placeholder*="Ask" i]', '[contenteditable="true"][data-lexical-editor="true"]', '[contenteditable="true"]'];
  let composer = null; let composerSelector = null;
  for (let attempt = 0; attempt < 6 && !composer; attempt += 1) {
    for (const selector of selectors) {
      const loc = page.locator(selector).first();
      if (!await loc.isVisible({ timeout: 350 }).catch(() => false)) continue;
      try { await loc.click({ timeout: 1500 }); await loc.fill(prompt, { timeout: 3000 }); composer = loc; composerSelector = selector; break; } catch {}
    }
    if (!composer) await page.waitForTimeout(400 * (attempt + 1));
  }
  if (!composer) throw new Error('E_CHATGPT_COMPOSER_UNAVAILABLE');
  for (const selector of ['[data-testid="send-button"]', 'button[aria-label*="Send" i]', 'button[data-testid*="send" i]']) {
    const button = page.locator(selector).first();
    if (await button.isVisible({ timeout: 300 }).catch(() => false)) { await button.click(); return { composer_selector: composerSelector, send_selector: selector }; }
  }
  await composer.press('Enter');
  return { composer_selector: composerSelector, send_selector: 'composer-enter' };
}
async function fillAndSubmitQwen(page, prompt) {
  const selectors = ['textarea[placeholder*="Ask Qwen" i]', 'textarea', '[contenteditable="true"][role="textbox"]', '[contenteditable="true"]'];
  for (let attempt = 0; attempt < 6; attempt += 1) {
    for (const selector of selectors) {
      const loc = page.locator(selector).first();
      if (!await loc.isVisible({ timeout: 350 }).catch(() => false)) continue;
      try { await loc.click({ timeout: 1500 }); await loc.fill(prompt, { timeout: 3000 }); await loc.press('Enter'); return { composer_selector: selector, send_selector: 'composer-enter' }; } catch {}
    }
    await page.waitForTimeout(400 * (attempt + 1));
  }
  throw new Error('E_QWEN_COMPOSER_UNAVAILABLE');
}
async function waitForGeneratedImage({ page, context, providerId, baseline, timeoutMs }) {
  const deadline = Date.now() + timeoutMs;
  let lastBody = '';
  while (Date.now() < deadline) {
    await page.waitForTimeout(providerId === 'chatgpt' ? 2000 : 1000);
    const images = await inventoryImages(page, providerId);
    for (let i = images.length - 1; i >= 0; i -= 1) {
      const row = images[i];
      if (!row.src || baseline.has(row.src)) continue;
      if (providerId === 'qwen') {
        const qwenOutput = row.src.includes('cdn.qwenlm.ai/output/');
        if (!qwenOutput && (row.width < 512 || row.height < 512)) continue;
        if (qwenOutput && Math.max(row.width, row.height) < 400) continue;
      }
      try {
        const fetched = await fetchImageBytes(page, context, row.src, providerId);
        if (fetched.bytes.length < (providerId === 'chatgpt' ? 50000 : 10000)) continue;
        const format = detectImageFormat(fetched.bytes);
        return { ...fetched, ...format, width: row.width, height: row.height };
      } catch {}
    }
    lastBody = await bodyText(page);
    if (lastBody.includes('generation failed') || lastBody.includes('failed to generate')) throw new Error('E_PROVIDER_GENERATION_FAILED');
    if (lastBody.includes('rate limit') || lastBody.includes('too many requests') || lastBody.includes('reached your limit')) throw new Error('E_PROVIDER_RATE_LIMITED');
    if (lastBody.includes('verify you are human') || lastBody.includes('security check') || lastBody.includes('captcha')) throw new Error('E_PROTECTION_CHALLENGE');
  }
  throw new Error('E_BOUNDED_COMPLETION_TIMEOUT');
}
function assertProviderConfig(providerId, providerConfig) {
  if (!['qwen', 'chatgpt'].includes(providerId)) throw new Error(`E_CONSOLE_PROVIDER_PROVIDER_UNSUPPORTED:${providerId}`);
  if (!providerConfig || providerConfig.actual_live_transport !== 'BROWSER_CDP') throw new Error('E_CONSOLE_PROVIDER_TRANSPORT_CONFIG');
  if (providerId === 'qwen' && providerConfig.session_api_live_executor_claimed !== false) throw new Error('E_CONSOLE_PROVIDER_QWEN_TRANSPORT_TRUTH');
}

export async function probeConsoleProvider({ controlBaseUrl, playwrightEntry, providerId, providerConfig, readinessProfile, jobId, clusterId, ttlMs = 120000 }) {
  assertProviderConfig(providerId, providerConfig);
  const started = Date.now(); let lease = null; let released = null; let disconnect = null;
  const out = { schema: 'die.factory-asset.console-provider-readiness-observation.v1', provider_id: providerId, cluster_id: clusterId, actual_transport: 'BROWSER_CDP', job_id: jobId, observed_at: nowIso(), credential_values_read: false, cookies_or_tokens_read: false };
  try {
    lease = await acquireClusterTab(controlBaseUrl, { providerId, jobId, ttlMs });
    out.lease = { lease_id: lease.lease_id, state: lease.state, acquired_at: lease.acquired_at, expires_at: lease.expires_at };
    const connected = await connectLeasedClusterTab({ controlBaseUrl, lease, playwrightEntry, timeoutMs: 10000 });
    disconnect = connected.disconnect;
    const page = connected.page;
    await page.goto(providerConfig.browser_url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(2200);
    const readiness = await classifyProviderPage({ page, providerId, profile: readinessProfile });
    out.readiness = readiness;
    if (PROVIDER_STATES.has(readiness.state)) await setClusterProviderState(controlBaseUrl, providerId, readiness.state);
    out.latency_ms = Date.now() - started;
    out.status = 'OBSERVED';
    return out;
  } catch (error) {
    const message = safeError(error);
    out.status = 'FAILED'; out.failure_code = classifyFailure(message); out.error = message; out.latency_ms = Date.now() - started;
    return out;
  } finally {
    if (lease?.lease_id) released = await releaseClusterTab(controlBaseUrl, lease.lease_id, 'FA_C010_READINESS_PROBE_COMPLETE').catch(() => null);
    if (released) out.lease_release = released;
    if (disconnect) await disconnect();
  }
}

export async function generateConsoleProviderImage({ controlBaseUrl, playwrightEntry, providerId, providerConfig, readinessProfile, jobId, prompt, artifactDir, clusterId, journalPath = null, ttlMs = 600000, timeoutMs = 300000 }) {
  assertProviderConfig(providerId, providerConfig);
  if (typeof prompt !== 'string' || prompt.length < 10 || prompt.length > 4000) throw new Error('E_CONSOLE_PROVIDER_PROMPT');
  fs.mkdirSync(artifactDir, { recursive: true, mode: 0o750 });
  const startedAt = nowIso(); const startedMs = Date.now(); let lease = null; let disconnect = null; let dispatchCommitted = false; let body = '';
  const receipt = {
    schema: 'die.factory-asset.console-provider-attempt.v1', job_id: jobId, provider_id: providerId, cluster_id: clusterId,
    actual_transport: 'BROWSER_CDP', transport_role: providerConfig.transport_role, primary_transport_contract: providerConfig.primary_transport_contract,
    qwen_session_api_live_executor_claimed: providerId === 'qwen' ? false : null,
    prompt_sha256: sha256(Buffer.from(prompt)), started_at: startedAt, status: 'STARTED', dispatch_committed: false,
    credential_values_read: false, cookies_or_tokens_read: false, provider_login_automated: false, submission_authorized: false, publication_authorized: false, spend_usd: 0,
  };
  atomicJson(journalPath, receipt);
  try {
    lease = await acquireClusterTab(controlBaseUrl, { providerId, jobId, ttlMs });
    receipt.lease = { lease_id: lease.lease_id, state: lease.state, acquired_at: lease.acquired_at, expires_at: lease.expires_at, max_tabs: lease.max_tabs, provider_limit: lease.provider_limit };
    atomicJson(journalPath, receipt);
    const connected = await connectLeasedClusterTab({ controlBaseUrl, lease, playwrightEntry, timeoutMs: 10000 });
    disconnect = connected.disconnect;
    const page = connected.page; const context = connected.browser.contexts()[0];
    if (!context) throw new Error('E_CONSOLE_PROVIDER_BROWSER_CONTEXT');
    await page.goto(providerConfig.browser_url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(2200);
    const readiness = await classifyProviderPage({ page, providerId, profile: readinessProfile });
    receipt.readiness = readiness;
    atomicJson(journalPath, receipt);
    if (PROVIDER_STATES.has(readiness.state)) await setClusterProviderState(controlBaseUrl, providerId, readiness.state);
    if (readiness.state !== 'HEALTHY') throw new Error(`E_PRE_DISPATCH_READINESS_${readiness.state}`);
    const baseline = new Set((await inventoryImages(page, providerId)).map((x) => x.src));
    await markClusterTab(controlBaseUrl, lease.lease_id, 'IN_FLIGHT');
    const submit = providerId === 'qwen' ? await fillAndSubmitQwen(page, prompt) : await fillAndSubmitChatGpt(page, prompt);
    dispatchCommitted = true; receipt.dispatch_committed = true; receipt.dispatch_committed_at = nowIso(); receipt.composer_selector = submit.composer_selector; receipt.send_selector = submit.send_selector;
    atomicJson(journalPath, receipt);
    const output = await waitForGeneratedImage({ page, context, providerId, baseline, timeoutMs });
    const artifactPath = path.join(artifactDir, `source-original.${output.ext}`);
    fs.writeFileSync(artifactPath, output.bytes, { mode: 0o640 });
    receipt.artifact = { path: artifactPath, sha256: sha256(output.bytes), bytes: output.bytes.length, mime: output.mime, dom_width_px: output.width, dom_height_px: output.height, original_byte_acquisition_method: output.method };
    receipt.status = 'SUCCEEDED'; receipt.completed_at = nowIso(); receipt.latency_ms = Date.now() - startedMs;
    atomicJson(journalPath, receipt);
    await markClusterTab(controlBaseUrl, lease.lease_id, 'COOLDOWN').catch(() => null);
    return receipt;
  } catch (error) {
    body = body || '';
    const message = safeError(error); const failureCode = classifyFailure(message, body);
    receipt.status = 'FAILED'; receipt.failure_code = failureCode; receipt.error = message; receipt.dispatch_committed = dispatchCommitted; receipt.failed_at = nowIso(); receipt.latency_ms = Date.now() - startedMs;
    atomicJson(journalPath, receipt);
    if (lease?.lease_id) await markClusterTab(controlBaseUrl, lease.lease_id, failureCode === 'CHECKPOINT' ? 'CHECKPOINT' : 'FAILED').catch(() => null);
    return receipt;
  } finally {
    if (lease?.lease_id) {
      const release = await releaseClusterTab(controlBaseUrl, lease.lease_id, 'FA_C010_ATTEMPT_COMPLETE').catch((error) => ({ released: false, error: safeError(error) }));
      receipt.lease_release = release;
    }
    receipt.cluster_lease_snapshot_after = await fetchClusterLeases(controlBaseUrl).then((v) => ({ schema: v.schema, max_tabs: v.max_tabs, active_leases: v.active_leases, open_pages: v.open_pages, provider_states: v.provider_states })).catch(() => null);
    if (disconnect) await disconnect();
    atomicJson(journalPath, receipt);
  }
}


