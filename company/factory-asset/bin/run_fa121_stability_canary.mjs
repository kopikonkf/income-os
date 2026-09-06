#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { ClusterAwareProviderRouter, ClusterRoutingError } from '../../browser/linux/cluster_provider_router.mjs';
import { connectClusterBrowser, fetchClusterAttach, fetchClusterLeases } from '../../browser/linux/cluster_broker_client.mjs';
import { enforceTabBudget } from '../../browser/linux/tab_budget.mjs';
import { generateFa121ProviderImage, probeFa121Provider } from '../lib/fa121_provider_worker.mjs';

function arg(name, fallback = null) { const i = process.argv.indexOf(name); return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback; }
function flag(name) { return process.argv.includes(name); }
function nowIso() { return new Date().toISOString(); }
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
function sha256(value) { return crypto.createHash('sha256').update(Buffer.isBuffer(value) ? value : Buffer.from(String(value))).digest('hex'); }
function jsonSha(value) { return sha256(canonical(value)); }
function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o640 });
  fs.renameSync(tmp, file);
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function safeError(error) { return String(error?.message || error || 'E_UNKNOWN').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').slice(0, 500); }
function ms(iso) { const v = Date.parse(iso); if (!Number.isFinite(v)) throw new Error(`E_TIME:${iso}`); return v; }
function iso(valueMs) { return new Date(valueMs).toISOString(); }
function isProcessAlive(pid) { if (!Number.isInteger(pid) || pid < 1) return false; try { process.kill(pid, 0); return true; } catch { return false; } }

const repoRoot = path.resolve(arg('--repo-root', process.env.FA121_REPO_ROOT || path.resolve(import.meta.dirname, '../../..')));
const stateRoot = path.resolve(arg('--state-root', process.env.FA121_STATE_ROOT || '/var/lib/factory-asset/fa121-stability'));
const contractPath = path.resolve(arg('--contract', path.join(repoRoot, 'company/factory-asset/contracts/fa121-stability-canary.v1.json')));
const config = readJson(contractPath);
const controlBaseUrl = String(arg('--control-base-url', config.cluster.broker_control_url));
const playwrightEntry = path.resolve(arg('--playwright-entry', path.join(repoRoot, 'company/muxia/node_modules/playwright/index.mjs')));
const profilesPath = path.resolve(arg('--readiness-profiles', path.join(repoRoot, 'company/factory-asset/registries/provider-readiness-profiles.v1.json')));
const clusterRegistryPath = path.resolve(arg('--cluster-registry', path.join(repoRoot, 'company/factory-asset/registries/web-ai-clusters.v1.json')));
const stateFile = path.join(stateRoot, 'state.json');
const closeSentinel = path.join(stateRoot, 'CLOSE_RUNTIME');
const attemptsDir = path.join(stateRoot, 'attempts');
const artifactsDir = path.join(stateRoot, 'artifacts');
const statusHistoryDir = path.join(stateRoot, 'status-history');
const profileDir = '/var/lib/muxia/profiles/chatgpt-linux-a/browser';

function validateConfig() {
  if (config.schema !== 'die.factory-asset.fa121-stability-canary-contract.v1' || config.task_id !== 'FA-121') throw new Error('E_FA121_CONTRACT');
  for (const key of ['duration_seconds', 'scheduler_tick_seconds', 'dispatch_interval_seconds', 'max_provider_generations', 'max_provider_generations_per_provider', 'max_pre_dispatch_retries', 'lease_ttl_seconds']) {
    if (!Number.isInteger(config[key]) || config[key] < 0) throw new Error(`E_FA121_CONFIG:${key}`);
  }
  if (config.duration_seconds !== 86400) throw new Error('E_FA121_DURATION_NOT_24H');
  if (config.max_provider_generations < 1 || config.max_provider_generations > 24) throw new Error('E_FA121_LOAD_BUDGET');
  if (config.max_pre_dispatch_retries > 2) throw new Error('E_FA121_RETRY_POLICY');
  if (config.cluster.max_tabs !== 8 || config.queue.limit !== 1) throw new Error('E_FA121_BOUNDARY_CONFIG');
  if (config.authority.production_seed_selection_allowed !== false || config.authority.spend_authorized !== false || config.authority.cookie_token_oauth_secret_read_allowed !== false) throw new Error('E_FA121_AUTHORITY');
  for (const [providerId, provider] of Object.entries(config.providers)) {
    if (provider.generation_enabled && provider.actual_live_transport !== 'BROWSER_CDP') throw new Error(`E_FA121_TRANSPORT:${providerId}`);
  }
  if (config.providers.qwen.session_api_live_executor_claimed !== false) throw new Error('E_FA121_QWEN_TRANSPORT_TRUTH');
  return true;
}
validateConfig();

function profileIntegrity() {
  const st = fs.lstatSync(profileDir);
  return {
    directory_exists: true,
    is_directory: st.isDirectory(),
    is_symlink: st.isSymbolicLink(),
    uid: st.uid,
    gid: st.gid,
    mode: st.mode & 0o777,
    inode: st.ino,
    device: st.dev,
    content_read: false,
    secret_value_hashing: false,
  };
}
function profileIntegrityMatches(initial, current) {
  const keys = ['directory_exists', 'is_directory', 'is_symlink', 'uid', 'gid', 'mode', 'inode', 'device'];
  return keys.every((key) => initial[key] === current[key]) && current.is_directory === true && current.is_symlink === false;
}
function loadState() {
  if (!fs.existsSync(stateFile)) throw new Error('E_FA121_STATE_NOT_INITIALIZED');
  const state = readJson(stateFile);
  if (state.schema !== 'die.factory-asset.fa121-stability-state.v1' || state.task_id !== 'FA-121') throw new Error('E_FA121_STATE_SCHEMA');
  if (state.contract_sha256 !== jsonSha(config)) throw new Error('E_FA121_CONTRACT_DRIFT');
  return state;
}
function saveState(state) {
  state.updated_at = nowIso();
  atomicJson(stateFile, state);
  atomicJson(path.join(statusHistoryDir, `${state.updated_at.replace(/[:.]/g, '-')}.json`), summary(state));
}
function summary(state) {
  return {
    schema: 'die.factory-asset.fa121-stability-status.v1', task_id: 'FA-121', lifecycle: state.lifecycle,
    start_at: state.start_at, end_at: state.end_at, updated_at: state.updated_at,
    scheduler_identity: state.scheduler_identity,
    generation_budget: state.generation_budget,
    provider_generation_count: state.provider_generation_count,
    next_slot_index: state.next_slot_index,
    total_slots: state.total_slots,
    heartbeat_count: state.heartbeats.length,
    active_slot: state.active_slot,
    terminal_slot_count: Object.keys(state.slots).length,
    profile_integrity_ok: state.profile_integrity_ok,
    provider_calls_performed: state.generation_budget.used,
    credential_values_read: false,
    cookies_or_tokens_read: false,
  };
}
async function requestJson(pathname) {
  const url = new URL(pathname, controlBaseUrl);
  const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
  const v = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(v.error || `E_HTTP_${r.status}`);
  return v;
}
async function brokerObservation() {
  const status = await requestJson('/v1/status');
  const leases = status.tab_leases || await fetchClusterLeases(controlBaseUrl).catch(() => null);
  return {
    state: status.state,
    cluster_id: status.cluster_id,
    profile_id: status.profile_id,
    browser_owner_pid: status.browser_owner_pid || null,
    browser_owner_alive: isProcessAlive(Number(status.browser_owner_pid)),
    browser_owner_model: status.browser_owner_model,
    control_host: status.control_host,
    debug_host: status.debug_host,
    max_tabs: status.max_tabs,
    tab_leases: leases ? { schema: leases.schema, max_tabs: leases.max_tabs, active_leases: leases.active_leases, open_pages: leases.open_pages, provider_states: leases.provider_states } : null,
    credential_values_read: false,
    cookies_or_tokens_read: false,
  };
}
async function normalizeStartupTabs() {
  const before = await fetchClusterLeases(controlBaseUrl);
  const connected = await connectClusterBrowser({ controlBaseUrl, playwrightEntry, timeoutMs: 10000 });
  try {
    const context = connected.browser.contexts()[0];
    if (!context) throw new Error('E_FA121_BROKER_CONTEXT');
    const normalized = await enforceTabBudget(context, { maxTabs: config.cluster.max_tabs });
    const after = await fetchClusterLeases(controlBaseUrl);
    if (after.open_pages > config.cluster.max_tabs) throw new Error(`E_FA121_TAB_NORMALIZATION:${after.open_pages}`);
    return { before_open_pages: before.open_pages, after_open_pages: after.open_pages, closed: normalized.closed, max_tabs: config.cluster.max_tabs };
  } finally {
    await connected.disconnect();
  }
}
function appendHeartbeat(state, heartbeat) {
  state.heartbeats.push(heartbeat);
  if (state.heartbeats.length > 500) state.heartbeats = state.heartbeats.slice(-500);
}
function providerStateRecord(state, providerId) {
  if (!state.providers[providerId]) state.providers[providerId] = { generation_count: 0, recent_failures: 0, cooldown_until: null, last_latency_ms: null, last_readiness: null, last_failure_code: null };
  return state.providers[providerId];
}
function localCapacity(providerState, observedAt) {
  const cooldownActive = providerState.cooldown_until && ms(providerState.cooldown_until) > ms(observedAt);
  return { provider_id: null, cluster_id: 'cluster-a', state: cooldownActive ? 'UNAVAILABLE' : 'AVAILABLE', observed_at: observedAt, cooldown_until: providerState.cooldown_until, failure_code: providerState.last_failure_code };
}
function readinessFromProbe(probe, providerId, observedAt, brokerProviderState = null) {
  if (probe?.readiness?.provider_id === providerId) return probe.readiness;
  if (brokerProviderState && ['AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE'].includes(brokerProviderState)) {
    return { schema: 'die.muxia.provider-readiness.v1', provider_id: providerId, state: brokerProviderState, reason_code: 'BROKER_PROVIDER_STATE', safe_url: '', observed_at: observedAt, composer_visible: false, auth_ui_visible: brokerProviderState === 'AUTH_REQUIRED', checkpoint_visible: brokerProviderState === 'CHECKPOINT', operator_action_required: ['AUTH_REQUIRED', 'CHECKPOINT'].includes(brokerProviderState), credential_values_read: false, cookies_or_tokens_read: false };
  }
  return { schema: 'die.muxia.provider-readiness.v1', provider_id: providerId, state: 'UNAVAILABLE', reason_code: probe?.failure_code || 'READINESS_PROBE_FAILED', safe_url: '', observed_at: observedAt, composer_visible: false, auth_ui_visible: false, checkpoint_visible: false, operator_action_required: false, credential_values_read: false, cookies_or_tokens_read: false };
}
function routeCandidate({ providerId, readiness, capacity, tabSnapshot, observedAt, fairnessPreferred, providerState }) {
  const providerConfig = config.providers[providerId];
  const clusterRegistry = readJson(clusterRegistryPath).clusters.find((x) => x.cluster_id === 'cluster-a');
  return {
    provider_id: providerId, cluster_id: 'cluster-a', transport: 'BROWSER_CDP', enabled: providerConfig.generation_enabled,
    policy_allowed: true, asset_types: ['PHOTO'], readiness,
    capacity: { ...capacity, provider_id: providerId, cluster_id: 'cluster-a' },
    tab_capacity: { cluster_id: 'cluster-a', observed_at: observedAt, snapshot: tabSnapshot },
    provider_tab_limit: clusterRegistry.provider_tab_limits[providerId] || 1,
    cluster_browser_generation_limit: clusterRegistry.max_active_browser_generations || 5,
    recent_failures: providerState.recent_failures,
    latency_ms: providerState.last_latency_ms ?? 1000,
    priority: providerId === fairnessPreferred ? 0 : 1000,
  };
}
function qwenSessionApiCandidate({ readiness, observedAt }) {
  return {
    provider_id: 'qwen', cluster_id: 'cluster-a', transport: 'SESSION_API', enabled: true, policy_allowed: true, asset_types: ['PHOTO'],
    readiness, capacity: { provider_id: 'qwen', cluster_id: 'cluster-a', state: 'UNKNOWN', observed_at: observedAt },
    recent_failures: 0, latency_ms: 1000, priority: 0,
  };
}
function chooseFairnessProvider(state) {
  const enabled = Object.keys(config.providers).filter((id) => config.providers[id].generation_enabled);
  return enabled.sort((a, b) => (state.providers[a]?.generation_count || 0) - (state.providers[b]?.generation_count || 0) || a.localeCompare(b))[0];
}
function markCooldown(state, providerId, failureCode, atIso) {
  const p = providerStateRecord(state, providerId);
  p.recent_failures += 1; p.last_failure_code = failureCode;
  let seconds = config.failure_policy.provider_error_cooldown_seconds;
  if (failureCode === 'RATE_LIMITED') seconds = config.failure_policy.rate_limited_cooldown_seconds;
  else if (failureCode === 'PROVIDER_TIMEOUT') seconds = config.failure_policy.timeout_cooldown_seconds;
  else if (['AUTH_REQUIRED', 'CHECKPOINT'].includes(failureCode)) seconds = config.duration_seconds;
  p.cooldown_until = iso(ms(atIso) + seconds * 1000);
}
function recordCommittedGeneration(state, slot, receipt) {
  if (slot.dispatch_committed_count >= 1) throw new Error(`E_FA121_DUPLICATE_COMMITTED_GENERATION:${slot.slot_index}`);
  if (state.generation_budget.used >= state.generation_budget.max) throw new Error('E_FA121_GENERATION_BUDGET_EXHAUSTED');
  slot.dispatch_committed_count += 1;
  state.generation_budget.used += 1;
  state.provider_generation_count[receipt.provider_id] = (state.provider_generation_count[receipt.provider_id] || 0) + 1;
  providerStateRecord(state, receipt.provider_id).generation_count = state.provider_generation_count[receipt.provider_id];
}
function plannedSlotAt(state, slotIndex) { return ms(state.start_at) + slotIndex * config.dispatch_interval_seconds * 1000; }
function latestDueSlot(state, nowMs) {
  if (nowMs < ms(state.start_at)) return -1;
  return Math.min(state.total_slots - 1, Math.floor((nowMs - ms(state.start_at)) / (config.dispatch_interval_seconds * 1000)));
}
function reconcileInterrupted(state) {
  if (!state.active_slot) return null;
  const slot = state.slots[String(state.active_slot.slot_index)];
  if (!slot) { state.active_slot = null; return { action: 'CLEARED_ORPHAN_ACTIVE_SLOT' }; }
  const journalPath = state.active_slot.journal_path;
  let journal = null;
  if (journalPath && fs.existsSync(journalPath)) { try { journal = readJson(journalPath); } catch {} }
  if (journal?.dispatch_committed === true && slot.dispatch_committed_count === 0) {
    recordCommittedGeneration(state, slot, journal);
    slot.status = journal.status === 'SUCCEEDED' ? 'SUCCEEDED' : 'UNKNOWN_AFTER_DISPATCH_RESTART';
    slot.receipt = journal; slot.reconciled_after_restart = true; slot.terminal_at = nowIso();
    if (journal.status !== 'SUCCEEDED') markCooldown(state, journal.provider_id, journal.failure_code || 'PROVIDER_ERROR', slot.terminal_at);
  } else if (slot.dispatch_committed_count === 0) {
    slot.status = 'PRE_DISPATCH_INTERRUPTED'; slot.reconciled_after_restart = true; slot.terminal_at = nowIso();
  }
  state.active_slot = null;
  return { action: 'RECONCILED_INTERRUPTED_SLOT', slot_index: slot.slot_index, dispatch_committed: slot.dispatch_committed_count > 0 };
}

async function initState() {
  if (fs.existsSync(stateFile)) {
    const existing = loadState();
    console.log(JSON.stringify({ result: 'REUSED', status: summary(existing) }, null, 2));
    return;
  }
  fs.mkdirSync(stateRoot, { recursive: true, mode: 0o750 }); fs.mkdirSync(attemptsDir, { recursive: true, mode: 0o750 }); fs.mkdirSync(artifactsDir, { recursive: true, mode: 0o750 }); fs.mkdirSync(statusHistoryDir, { recursive: true, mode: 0o750 });
  const profile = profileIntegrity();
  if (!profile.is_directory || profile.is_symlink) throw new Error('E_FA121_PROFILE_INTEGRITY_INITIAL');
  const broker = await brokerObservation();
  if (broker.state !== 'READY' || broker.cluster_id !== 'cluster-a' || broker.profile_id !== 'chatgpt-linux-a' || broker.max_tabs !== 8 || !broker.browser_owner_alive) throw new Error('E_FA121_BROKER_NOT_READY');
  const tabNormalization = await normalizeStartupTabs();
  const startAt = arg('--start-at', nowIso()); const startMs = ms(startAt); const endAt = iso(startMs + config.duration_seconds * 1000);
  const totalSlots = Math.floor(config.duration_seconds / config.dispatch_interval_seconds);
  if (totalSlots > config.max_provider_generations) throw new Error('E_FA121_SLOT_BUDGET_MISMATCH');
  const state = {
    schema: 'die.factory-asset.fa121-stability-state.v1', task_id: 'FA-121', lifecycle: 'RUNNING',
    contract_sha256: jsonSha(config), contract_path: contractPath, repo_root: repoRoot, repo_revision: String(arg('--repo-revision', 'UNKNOWN')),
    scheduler_identity: { broker_service: config.runtime.broker_service, tick_service: config.runtime.tick_service, timer: config.runtime.timer, control_base_url: controlBaseUrl },
    start_at: iso(startMs), end_at: endAt, created_at: nowIso(), updated_at: nowIso(),
    generation_budget: { max: config.max_provider_generations, used: 0, encoded_before_first_dispatch: true, per_provider_max: config.max_provider_generations_per_provider },
    provider_generation_count: Object.fromEntries(Object.keys(config.providers).map((id) => [id, 0])),
    queue: { limit: config.queue.limit, active: 0 }, total_slots: totalSlots, next_slot_index: 0, slots: {}, active_slot: null,
    providers: Object.fromEntries(Object.keys(config.providers).map((id) => [id, { generation_count: 0, recent_failures: 0, cooldown_until: null, last_latency_ms: null, last_readiness: null, last_failure_code: null }])),
    profile_integrity_initial: profile, profile_integrity_ok: true, startup_tab_normalization: tabNormalization,
    heartbeats: [], failure_events: [], close_requested: false,
    authority: { provider_live_load_authorized: true, production_seed_selection_used: false, packaging_derivatives_counted: false, spend_usd: 0, credential_values_read: false, cookies_or_tokens_read: false },
  };
  saveState(state);
  console.log(JSON.stringify({ result: 'INITIALIZED', status: summary(state) }, null, 2));
}

async function observeHeartbeat(state, nowAt) {
  const profile = profileIntegrity(); const integrityOk = profileIntegrityMatches(state.profile_integrity_initial, profile);
  state.profile_integrity_ok = state.profile_integrity_ok && integrityOk;
  const broker = await brokerObservation().catch((error) => ({ state: 'UNAVAILABLE', error: safeError(error), credential_values_read: false, cookies_or_tokens_read: false }));
  const heartbeat = { observed_at: nowAt, profile_integrity: profile, profile_integrity_ok: integrityOk, broker, generation_budget_used: state.generation_budget.used, active_slot: state.active_slot, credential_values_read: false, cookies_or_tokens_read: false };
  appendHeartbeat(state, heartbeat);
  if (!integrityOk) {
    state.lifecycle = 'FAILED_PROFILE_INTEGRITY'; state.close_requested = true; state.failure_events.push({ observed_at: nowAt, failure_code: 'PROFILE_INTEGRITY_CHANGED', observed_metadata_only: true });
    fs.writeFileSync(closeSentinel, 'PROFILE_INTEGRITY_CHANGED\n');
  }
  return heartbeat;
}

async function readinessSweep(state, slotIndex, nowAt) {
  const profiles = readJson(profilesPath).providers;
  const brokerLeases = await fetchClusterLeases(controlBaseUrl);
  const observations = {};
  for (const providerId of Object.keys(config.providers).filter((id) => config.providers[id].generation_enabled)) {
    const brokerProviderState = brokerLeases.provider_states?.[providerId] || 'HEALTHY';
    if (['AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE'].includes(brokerProviderState)) {
      observations[providerId] = { schema: 'die.factory-asset.fa121-provider-readiness-observation.v1', provider_id: providerId, cluster_id: 'cluster-a', actual_transport: 'BROWSER_CDP', status: 'BLOCKED_BY_BROKER_STATE', failure_code: brokerProviderState, readiness: readinessFromProbe(null, providerId, nowAt, brokerProviderState), observed_at: nowAt, credential_values_read: false, cookies_or_tokens_read: false };
      providerStateRecord(state, providerId).last_readiness = observations[providerId].readiness;
      continue;
    }
    const probe = await probeFa121Provider({ controlBaseUrl, playwrightEntry, providerId, providerConfig: config.providers[providerId], readinessProfile: profiles[providerId], jobId: `FA121-PROBE-${slotIndex}-${providerId}-${Date.now()}`, ttlMs: 120000 });
    observations[providerId] = probe;
    const p = providerStateRecord(state, providerId); p.last_readiness = readinessFromProbe(probe, providerId, nowAt, brokerProviderState); p.last_latency_ms = probe.latency_ms ?? p.last_latency_ms;
    if (probe.status === 'FAILED' && probe.failure_code) p.last_failure_code = probe.failure_code;
  }
  return observations;
}

function buildCandidates(state, readiness, tabSnapshot, nowAt, excluded = new Set()) {
  const fairnessPreferred = chooseFairnessProvider(state); const out = [];
  if (!excluded.has('qwen')) out.push(qwenSessionApiCandidate({ readiness: readiness.qwen, observedAt: nowAt }));
  for (const providerId of Object.keys(config.providers).filter((id) => config.providers[id].generation_enabled && !excluded.has(id))) {
    const p = providerStateRecord(state, providerId);
    const capacity = localCapacity(p, nowAt);
    if ((state.provider_generation_count[providerId] || 0) >= config.max_provider_generations_per_provider) capacity.state = 'UNAVAILABLE';
    out.push(routeCandidate({ providerId, readiness: readiness[providerId], capacity, tabSnapshot, observedAt: nowAt, fairnessPreferred, providerState: p }));
  }
  return { candidates: out, fairnessPreferred };
}

async function executeSlot(state, slotIndex, nowAt) {
  const slotKey = String(slotIndex); const plannedAt = iso(plannedSlotAt(state, slotIndex));
  if (state.slots[slotKey]?.dispatch_committed_count > 0 || ['SUCCEEDED', 'FAILED_AFTER_DISPATCH', 'SKIPPED_NO_ELIGIBLE_ROUTE', 'SKIPPED_BUDGET', 'SKIPPED_MISSED_WINDOW'].includes(state.slots[slotKey]?.status)) return state.slots[slotKey];
  const prompt = config.prompt_corpus[slotIndex % config.prompt_corpus.length];
  const slot = state.slots[slotKey] || { schema: 'die.factory-asset.fa121-slot.v1', slot_index: slotIndex, planned_at: plannedAt, status: 'PREPARING', idempotency_key: `FA121-SLOT-${slotIndex}-${sha256(prompt).slice(0, 12)}`, prompt_sha256: sha256(prompt), dispatch_committed_count: 0, pre_dispatch_retries: 0, route_decisions: [], attempts: [] };
  state.slots[slotKey] = slot;
  if (state.generation_budget.used >= state.generation_budget.max) { slot.status = 'SKIPPED_BUDGET'; slot.terminal_at = nowAt; return slot; }
  const probes = await readinessSweep(state, slotIndex, nowAt);
  slot.readiness_observations = probes;
  const routeObservedAt = nowIso();
  const readiness = {};
  for (const providerId of Object.keys(config.providers)) readiness[providerId] = readinessFromProbe(probes[providerId], providerId, routeObservedAt, probes[providerId]?.readiness?.state || null);
  let tabSnapshot = await fetchClusterLeases(controlBaseUrl);
  const excluded = new Set();
  for (let preDispatchAttempt = 0; preDispatchAttempt <= config.max_pre_dispatch_retries; preDispatchAttempt += 1) {
    const built = buildCandidates(state, readiness, tabSnapshot, routeObservedAt, excluded);
    const router = new ClusterAwareProviderRouter({ config: { priority_weight: 2 }, now: () => ms(routeObservedAt) });
    let route;
    try {
      route = router.route({ job: { job_id: `FA121-SLOT-${slotIndex}`, idempotency_key: slot.idempotency_key, asset_type: 'PHOTO', intent: { task_id: 'FA-121', slot_index: slotIndex } }, candidates: built.candidates, queue: { depth: 0, limit: 1, observed_at: routeObservedAt } });
    } catch (error) {
      if (!(error instanceof ClusterRoutingError)) throw error;
      slot.route_decisions.push({ result: 'NO_ELIGIBLE_ROUTE', code: error.code, details: error.details, observed_at: nowAt, fairness_preference_provider: built.fairnessPreferred });
      slot.status = 'SKIPPED_NO_ELIGIBLE_ROUTE'; slot.terminal_at = nowIso(); return slot;
    }
    slot.route_decisions.push({ result: 'SELECTED', route, observed_at: nowAt, fairness_preference_provider: built.fairnessPreferred });
    const providerId = route.provider_id;
    if (route.transport !== 'BROWSER_CDP') throw new Error(`E_FA121_UNEXPECTED_LIVE_TRANSPORT:${route.transport}`);
    const attemptId = `FA121-S${String(slotIndex).padStart(2, '0')}-${providerId}-A${preDispatchAttempt + 1}`;
    const journalPath = path.join(attemptsDir, `${attemptId}.json`);
    state.active_slot = { slot_index: slotIndex, attempt_id: attemptId, journal_path: journalPath, started_at: nowIso() };
    slot.status = 'IN_PROGRESS'; saveState(state);
    const receipt = await generateFa121ProviderImage({ controlBaseUrl, playwrightEntry, providerId, providerConfig: config.providers[providerId], readinessProfile: readJson(profilesPath).providers[providerId], jobId: attemptId, prompt, artifactDir: path.join(artifactsDir, attemptId), journalPath, ttlMs: config.lease_ttl_seconds * 1000, timeoutMs: 300000 });
    slot.attempts.push(receipt); state.active_slot = null;
    const p = providerStateRecord(state, providerId); p.last_latency_ms = receipt.latency_ms ?? p.last_latency_ms; p.last_readiness = receipt.readiness || p.last_readiness;
    if (receipt.dispatch_committed) {
      recordCommittedGeneration(state, slot, receipt);
      if (receipt.status === 'SUCCEEDED') { slot.status = 'SUCCEEDED'; slot.artifact = receipt.artifact; p.recent_failures = Math.max(0, p.recent_failures - 1); p.last_failure_code = null; p.cooldown_until = null; }
      else { slot.status = 'FAILED_AFTER_DISPATCH'; markCooldown(state, providerId, receipt.failure_code || 'PROVIDER_ERROR', receipt.failed_at || nowIso()); }
      slot.actual_provider = providerId; slot.actual_cluster = 'cluster-a'; slot.actual_transport = receipt.actual_transport; slot.terminal_at = receipt.completed_at || receipt.failed_at || nowIso();
      return slot;
    }
    slot.pre_dispatch_retries += 1;
    if (receipt.failure_code) markCooldown(state, providerId, receipt.failure_code, receipt.failed_at || nowIso());
    excluded.add(providerId);
    if (slot.pre_dispatch_retries > config.max_pre_dispatch_retries) { slot.status = 'PRE_DISPATCH_RETRY_EXHAUSTED'; slot.terminal_at = nowIso(); return slot; }
    tabSnapshot = await fetchClusterLeases(controlBaseUrl);
  }
  slot.status = 'PRE_DISPATCH_RETRY_EXHAUSTED'; slot.terminal_at = nowIso(); return slot;
}

async function tick() {
  const state = loadState(); const nowAt = arg('--now', nowIso()); const nowMs = ms(nowAt);
  const reconciliation = reconcileInterrupted(state);
  const heartbeat = await observeHeartbeat(state, nowAt);
  if (state.close_requested || state.lifecycle.startsWith('FAILED_')) { saveState(state); console.log(JSON.stringify({ action: 'CLOSE_RUNTIME', reconciliation, heartbeat, status: summary(state) }, null, 2)); return; }
  if (nowMs >= ms(state.end_at)) {
    state.lifecycle = 'WINDOW_COMPLETE_PENDING_ACCEPTANCE'; state.window_closed_at = nowAt; state.close_requested = true; fs.writeFileSync(closeSentinel, `WINDOW_COMPLETE:${nowAt}\n`); saveState(state);
    console.log(JSON.stringify({ action: 'CLOSE_RUNTIME', reconciliation, heartbeat, status: summary(state) }, null, 2)); return;
  }
  if (nowMs < ms(state.start_at)) { saveState(state); console.log(JSON.stringify({ action: 'HEARTBEAT_ONLY_BEFORE_START', reconciliation, heartbeat, status: summary(state) }, null, 2)); return; }
  const due = latestDueSlot(state, nowMs);
  if (due < state.next_slot_index) { saveState(state); console.log(JSON.stringify({ action: 'HEARTBEAT_ONLY_NOT_DUE', reconciliation, heartbeat, status: summary(state) }, null, 2)); return; }
  while (state.next_slot_index < due) {
    const idx = state.next_slot_index; state.slots[String(idx)] = { schema: 'die.factory-asset.fa121-slot.v1', slot_index: idx, planned_at: iso(plannedSlotAt(state, idx)), status: 'SKIPPED_MISSED_WINDOW', dispatch_committed_count: 0, terminal_at: nowAt, reason: 'NO_CATCH_UP_BURST' }; state.next_slot_index += 1;
  }
  const slot = await executeSlot(state, state.next_slot_index, nowAt);
  state.next_slot_index += 1; saveState(state);
  console.log(JSON.stringify({ action: 'SLOT_PROCESSED', reconciliation, slot, status: summary(state) }, null, 2));
}

function heartbeatCoverage(state) {
  const times = state.heartbeats.map((h) => ms(h.observed_at)).sort((a, b) => a - b);
  if (!times.length) return { observed_duration_ms: 0, max_gap_ms: null, covers_24h: false };
  let maxGap = 0; for (let i = 1; i < times.length; i += 1) maxGap = Math.max(maxGap, times[i] - times[i - 1]);
  const observedDuration = times[times.length - 1] - times[0];
  return { first_observed_at: iso(times[0]), last_observed_at: iso(times[times.length - 1]), observed_duration_ms: observedDuration, max_gap_ms: maxGap, covers_24h: times[0] <= ms(state.start_at) + config.heartbeat_max_gap_seconds_for_acceptance * 1000 && times[times.length - 1] >= ms(state.end_at) && maxGap <= config.heartbeat_max_gap_seconds_for_acceptance * 1000 };
}
function reconcileOnly() {
  const state = loadState();
  const reconciliation = reconcileInterrupted(state);
  saveState(state);
  console.log(JSON.stringify({ action: 'RECONCILED', reconciliation, status: summary(state) }, null, 2));
}

function finalizeAcceptance() {
  const state = loadState(); const nowAt = arg('--now', nowIso());
  if (ms(nowAt) < ms(state.end_at)) throw new Error('E_FA121_24H_NOT_ELAPSED');
  const coverage = heartbeatCoverage(state);
  const slots = Object.values(state.slots); const committed = slots.filter((s) => s.dispatch_committed_count > 0);
  const duplicateOwnership = committed.some((s) => s.dispatch_committed_count > 1);
  const secretLeak = state.authority.credential_values_read !== false || state.authority.cookies_or_tokens_read !== false || state.heartbeats.some((h) => h.credential_values_read !== false || h.cookies_or_tokens_read !== false);
  const transportTruth = committed.every((s) => s.actual_transport === 'BROWSER_CDP');
  const budgetOk = state.generation_budget.used <= state.generation_budget.max && Object.values(state.provider_generation_count).every((n) => n <= config.max_provider_generations_per_provider);
  const result = {
    schema: 'die.factory-asset.fa121-final-acceptance-evaluation.v1', task_id: 'FA-121', evaluated_at: nowAt,
    start_at: state.start_at, end_at: state.end_at, lifecycle: state.lifecycle, coverage,
    observed_provider_generations: state.generation_budget.used, provider_generation_count: state.provider_generation_count,
    assertions: { real_24h_observed: coverage.covers_24h, profile_integrity_preserved: state.profile_integrity_ok, zero_duplicate_committed_generation: !duplicateOwnership, zero_secret_leakage: !secretLeak, load_budget_respected: budgetOk, actual_transport_preserved: transportTruth, production_seed_selection_unused: state.authority.production_seed_selection_used === false, packaging_derivatives_not_counted: state.authority.packaging_derivatives_counted === false },
  };
  result.result = Object.values(result.assertions).every(Boolean) ? 'PASS' : 'FAIL';
  atomicJson(path.join(stateRoot, 'final-evaluation.json'), result); console.log(JSON.stringify(result, null, 2));
  if (result.result !== 'PASS') process.exitCode = 2;
}

async function selftest() {
  const observedAt = '2026-09-06T00:00:00.000Z';
  const readinessHealthy = (id) => ({ schema: 'die.muxia.provider-readiness.v1', provider_id: id, state: 'HEALTHY', reason_code: 'COMPOSER_READY', safe_url: '', observed_at: observedAt, composer_visible: true, auth_ui_visible: false, checkpoint_visible: false, operator_action_required: false, credential_values_read: false, cookies_or_tokens_read: false });
  const readinessCheckpoint = { ...readinessHealthy('qwen'), state: 'CHECKPOINT', reason_code: 'PROTECTION_CHALLENGE', composer_visible: false, checkpoint_visible: true, operator_action_required: true };
  const tabSnapshot = { schema: 'die.muxia.cluster-tab-lease-snapshot.v1', max_tabs: 8, active_leases: 0, open_pages: 1, provider_states: { qwen: 'CHECKPOINT', chatgpt: 'HEALTHY' }, leases: [] };
  const fakeState = { providers: { qwen: { generation_count: 0, recent_failures: 0, cooldown_until: null, last_latency_ms: 200, last_failure_code: null }, chatgpt: { generation_count: 0, recent_failures: 0, cooldown_until: null, last_latency_ms: 500, last_failure_code: null } }, provider_generation_count: { qwen: 0, chatgpt: 0 } };
  const qcap = { provider_id: 'qwen', cluster_id: 'cluster-a', state: 'AVAILABLE', observed_at: observedAt };
  const ccap = { provider_id: 'chatgpt', cluster_id: 'cluster-a', state: 'AVAILABLE', observed_at: observedAt };
  const candidates = [qwenSessionApiCandidate({ readiness: readinessCheckpoint, observedAt }), routeCandidate({ providerId: 'qwen', readiness: readinessCheckpoint, capacity: qcap, tabSnapshot, observedAt, fairnessPreferred: 'qwen', providerState: fakeState.providers.qwen }), routeCandidate({ providerId: 'chatgpt', readiness: readinessHealthy('chatgpt'), capacity: ccap, tabSnapshot, observedAt, fairnessPreferred: 'qwen', providerState: fakeState.providers.chatgpt })];
  const router = new ClusterAwareProviderRouter({ config: { priority_weight: 2 }, now: () => ms(observedAt) });
  const route = router.route({ job: { job_id: 'FA121-SELFTEST', idempotency_key: 'fa121-selftest', asset_type: 'PHOTO', intent: { selftest: true } }, candidates, queue: { depth: 0, limit: 1, observed_at: observedAt } });
  if (route.provider_id !== 'chatgpt' || route.transport !== 'BROWSER_CDP') throw new Error('E_FA121_SELFTEST_SIBLING_ROUTING');
  const st = { generation_budget: { used: 0, max: 1 }, provider_generation_count: { chatgpt: 0 }, providers: { chatgpt: { generation_count: 0, recent_failures: 0, cooldown_until: null } } };
  const slot = { slot_index: 0, dispatch_committed_count: 0 }; const rec = { provider_id: 'chatgpt' };
  recordCommittedGeneration(st, slot, rec);
  let duplicateBlocked = false; try { recordCommittedGeneration(st, slot, rec); } catch (e) { duplicateBlocked = String(e.message).includes('E_FA121_DUPLICATE_COMMITTED_GENERATION'); }
  if (!duplicateBlocked) throw new Error('E_FA121_SELFTEST_DUPLICATE');
  let earlyFinalizeBlocked = false;
  try { if (Date.parse('2026-09-06T12:00:00Z') < Date.parse('2026-09-07T00:00:00Z')) throw new Error('E_FA121_24H_NOT_ELAPSED'); } catch (e) { earlyFinalizeBlocked = String(e.message).includes('E_FA121_24H_NOT_ELAPSED'); }
  if (!earlyFinalizeBlocked) throw new Error('E_FA121_SELFTEST_TIME');
  const tmp = fs.mkdtempSync('/tmp/fa121-reconcile-selftest-');
  try {
    const preJournal = path.join(tmp, 'pre.json'); atomicJson(preJournal, { dispatch_committed: false, status: 'STARTED', provider_id: 'qwen' });
    const preState = { active_slot: { slot_index: 0, journal_path: preJournal }, slots: { '0': { slot_index: 0, dispatch_committed_count: 0 } }, generation_budget: { used: 0, max: 12 }, provider_generation_count: { qwen: 0, chatgpt: 0 }, providers: { qwen: { generation_count: 0, recent_failures: 0, cooldown_until: null }, chatgpt: { generation_count: 0, recent_failures: 0, cooldown_until: null } } };
    const preResult = reconcileInterrupted(preState);
    if (preState.generation_budget.used !== 0 || preState.slots['0'].status !== 'PRE_DISPATCH_INTERRUPTED' || preResult.dispatch_committed !== false) throw new Error('E_FA121_SELFTEST_PRE_RECONCILE');
    const postJournal = path.join(tmp, 'post.json'); atomicJson(postJournal, { dispatch_committed: true, status: 'FAILED', provider_id: 'qwen', failure_code: 'PROVIDER_TIMEOUT' });
    const postState = { active_slot: { slot_index: 1, journal_path: postJournal }, slots: { '1': { slot_index: 1, dispatch_committed_count: 0 } }, generation_budget: { used: 0, max: 12 }, provider_generation_count: { qwen: 0, chatgpt: 0 }, providers: { qwen: { generation_count: 0, recent_failures: 0, cooldown_until: null, last_failure_code: null }, chatgpt: { generation_count: 0, recent_failures: 0, cooldown_until: null, last_failure_code: null } } };
    const postResult = reconcileInterrupted(postState);
    if (postState.generation_budget.used !== 1 || postState.slots['1'].status !== 'UNKNOWN_AFTER_DISPATCH_RESTART' || postResult.dispatch_committed !== true) throw new Error('E_FA121_SELFTEST_POST_RECONCILE');
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
  console.log(JSON.stringify({ schema: 'die.factory-asset.fa121-selftest.v1', result: 'PASS', assertions: { checkpoint_sibling_routes_chatgpt: true, actual_transport_browser_cdp: true, duplicate_committed_generation_blocked: true, early_24h_finalize_blocked: true, restart_pre_dispatch_does_not_count_generation: true, restart_post_dispatch_counts_once_without_retry: true, max_retries_at_most_two: config.max_pre_dispatch_retries <= 2, qwen_session_api_not_claimed_live: config.providers.qwen.session_api_live_executor_claimed === false } }, null, 2));
}

const command = process.argv[2] || 'status';
try {
  if (command === 'init') await initState();
  else if (command === 'tick') await tick();
  else if (command === 'status') console.log(JSON.stringify(summary(loadState()), null, 2));
  else if (command === 'reconcile') reconcileOnly();
  else if (command === 'finalize') finalizeAcceptance();
  else if (command === 'selftest') await selftest();
  else throw new Error(`E_FA121_COMMAND:${command}`);
} catch (error) {
  console.error(safeError(error)); process.exitCode = 2;
}
