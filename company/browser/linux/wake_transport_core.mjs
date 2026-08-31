#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const CHATGPT_THREAD = /^https:\/\/chatgpt\.com\/c\/([A-Za-z0-9-]+)(?:[/?#].*)?$/;
const MAX_BRIEFING_CHARS = 12000;

function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2) + '\n', { mode: 0o640 });
  fs.renameSync(tmp, file);
}

function sha256(text) { return crypto.createHash('sha256').update(text, 'utf8').digest('hex'); }

export function normalizeThreadUrl(url) {
  const match = String(url || '').match(CHATGPT_THREAD);
  if (!match) throw new Error('E_THREAD_URL');
  return { conversationUrl: `https://chatgpt.com/c/${match[1]}`, conversationId: match[1] };
}

export function validateEnvelope(value, principalId) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('E_ENVELOPE_OBJECT');
  if (value.schema !== 'die.wake.envelope.v1') throw new Error('E_ENVELOPE_SCHEMA');
  if (value.company_instance_id !== 'DIE-LINUX') throw new Error('E_COMPANY_INSTANCE');
  if (value.principal_id !== principalId) throw new Error('E_PRINCIPAL_MISMATCH');
  for (const key of ['wake_id', 'mission_id', 'action_type', 'briefing', 'created_at']) {
    if (typeof value[key] !== 'string' || !value[key].trim()) throw new Error(`E_ENVELOPE_FIELD:${key}`);
  }
  if (value.briefing.length > MAX_BRIEFING_CHARS) throw new Error('E_BRIEFING_OVERSIZE');
  if (!Array.isArray(value.evidence_refs || [])) throw new Error('E_EVIDENCE_REFS');
  return value;
}

export function updateThreadState(previous, { principalId, conversationUrl, conversationId, at }) {
  if (previous && previous.principal_id && previous.principal_id !== principalId) throw new Error('E_THREAD_STATE_PRINCIPAL_MISMATCH');
  const oldId = previous?.conversation_id || null;
  const generation = Number(previous?.generation || 0) + (oldId === conversationId ? 0 : 1);
  const history = Array.isArray(previous?.history) ? [...previous.history] : [];
  if (oldId && oldId !== conversationId) history.push({ conversation_id: oldId, lifecycle_state: 'superseded', superseded_by: conversationId, at });
  return { schema: 'die.wake.thread.v2', company_instance_id: 'DIE-LINUX', principal_id: principalId, conversation_id: conversationId, conversation_url: conversationUrl, lifecycle_state: 'active', generation: Math.max(1, generation), history: history.slice(-20), updated_at: at };
}

async function connectBrowser({ dieHome, statusFile, principalId }) {
  const status = JSON.parse(fs.readFileSync(statusFile, 'utf8'));
  if (status.principal_id !== principalId) throw new Error('E_BROWSER_STATUS_PRINCIPAL_MISMATCH');
  if (status.state !== 'READY') throw new Error(`E_BROWSER_NOT_READY:${status.state}`);
  if (status.debugHost !== '127.0.0.1') throw new Error('E_CDP_NOT_LOOPBACK');
  const port = Number(status.debugPort);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('E_CDP_PORT');
  const playwrightEntry = path.join(dieHome, 'company', 'muxia', 'node_modules', 'playwright', 'index.mjs');
  if (!fs.existsSync(playwrightEntry)) throw new Error(`E_PLAYWRIGHT_MISSING:${playwrightEntry}`);
  const { chromium } = await import(pathToFileURL(playwrightEntry).href);
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 20000 });
  const context = browser.contexts()[0];
  if (!context) throw new Error('E_BROWSER_CONTEXT');
  const pages = context.pages().filter((page) => page.url().startsWith('https://chatgpt.com'));
  if (!pages.length) throw new Error('E_CHATGPT_PAGE');
  return { browser, pages };
}

async function currentThreadPage(pages) {
  const page = pages.find((p) => CHATGPT_THREAD.test(p.url())) || pages[0];
  const thread = normalizeThreadUrl(page.url());
  return { page, ...thread };
}

async function composer(page) {
  const primary = page.locator('#prompt-textarea').first();
  if (await primary.count()) return primary;
  const fallback = page.locator('textarea, [contenteditable="true"]').first();
  if (!(await fallback.count())) throw new Error('E_COMPOSER_NOT_FOUND');
  return fallback;
}

function normalizeSafe(url) { try { return normalizeThreadUrl(url).conversationUrl; } catch { return ''; } }

export async function runWakeTransport(options) {
  const { dieHome, principalId, statusFile, threadStateFile, receiptDir, command, envelopeFile } = options;
  for (const value of [dieHome, statusFile, threadStateFile, receiptDir]) if (!path.isAbsolute(value)) throw new Error('E_ABSOLUTE_PATH_REQUIRED');
  if (!['bind', 'focus', 'stage', 'canary'].includes(command)) throw new Error('E_WAKE_COMMAND');
  const { browser, pages } = await connectBrowser({ dieHome, statusFile, principalId });
  try {
    if (command === 'bind') {
      const { page, conversationUrl, conversationId } = await currentThreadPage(pages);
      await page.bringToFront();
      const previous = fs.existsSync(threadStateFile) ? JSON.parse(fs.readFileSync(threadStateFile, 'utf8')) : null;
      const state = updateThreadState(previous, { principalId, conversationUrl, conversationId, at: new Date().toISOString() });
      atomicJson(threadStateFile, state);
      return { status: 'PASS', command, principal_id: principalId, conversation_id: conversationId, generation: state.generation };
    }
    if (!fs.existsSync(threadStateFile)) throw new Error('E_THREAD_STATE_MISSING');
    const state = JSON.parse(fs.readFileSync(threadStateFile, 'utf8'));
    if (state.principal_id !== principalId || state.lifecycle_state !== 'active') throw new Error('E_THREAD_STATE');
    const thread = normalizeThreadUrl(state.conversation_url);
    let page = pages.find((p) => normalizeSafe(p.url()) === thread.conversationUrl) || pages[0];
    if (normalizeSafe(page.url()) !== thread.conversationUrl) await page.goto(thread.conversationUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.bringToFront();
    if (command === 'focus') return { status: 'PASS', command, principal_id: principalId, conversation_id: thread.conversationId, generation: state.generation };
    if (!envelopeFile || !path.isAbsolute(envelopeFile)) throw new Error('E_ENVELOPE_PATH');
    const envelope = validateEnvelope(JSON.parse(fs.readFileSync(envelopeFile, 'utf8')), principalId);
    const box = await composer(page);
    const existingText = await box.inputValue().catch(async () => await box.textContent() || '');
    if (existingText.trim()) throw new Error('E_COMPOSER_NOT_EMPTY');
    const marker = command === 'canary' ? `[${envelope.wake_id}] ${envelope.briefing}` : envelope.briefing;
    await box.fill(marker);
    const stagedText = await box.inputValue().catch(async () => await box.textContent() || '');
    if (stagedText !== marker) throw new Error('E_COMPOSER_STAGE_MISMATCH');
    if (command === 'canary') await box.fill('');
    const receipt = { schema: 'die.wake.stage-receipt.v1', company_instance_id: 'DIE-LINUX', wake_id: envelope.wake_id, principal_id: principalId, conversation_id: thread.conversationId, thread_generation: state.generation, briefing_sha256: sha256(envelope.briefing), composer_prefilled: true, canary_cleared: command === 'canary', submitted: false, output_extracted: false, credential_material_accessed: false, private_backend_called: false, observed_at: new Date().toISOString() };
    fs.mkdirSync(receiptDir, { recursive: true, mode: 0o750 });
    const receiptRef = path.join(receiptDir, `${envelope.wake_id}.json`);
    atomicJson(receiptRef, receipt);
    return { status: 'PASS', command, principal_id: principalId, wake_id: envelope.wake_id, submitted: false, receipt_ref: receiptRef };
  } finally {
    // Never terminate the remote browser: this transport attaches to an operator-owned live Chrome.
    // The short-lived wrapper exits its own process to drop the CDP socket without terminating Chrome.
  }
}
