#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { MultiClusterScheduler } from '../../browser/linux/multi_cluster_scheduler.mjs';
import { probeConsoleProvider, generateConsoleProviderImage } from '../lib/console_broker_provider_worker.mjs';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 });
  const tmp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o640 });
  fs.renameSync(tmp, file);
}
function nowIso() { return new Date().toISOString(); }
function safeStatus(status) {
  const tabs = status?.tab_leases || {};
  return {
    schema: 'die.factory-asset.fa-c010-broker-observation.v1',
    cluster_id: status?.cluster_id || null,
    profile_id: status?.profile_id || null,
    state: status?.state || null,
    browser_owner_pid: status?.browser_owner_pid || null,
    browser_owner_model: status?.browser_owner_model || null,
    control_host: status?.control_host || null,
    control_port: status?.control_port || null,
    max_tabs: status?.max_tabs ?? null,
    active_leases: tabs.active_leases ?? null,
    open_pages: tabs.open_pages ?? null,
    provider_states: tabs.provider_states || {},
    credential_values_read: false,
    cookies_or_tokens_read: false,
  };
}
async function requestJson(base, pathname) {
  const url = new URL(pathname, base);
  if (url.hostname !== '127.0.0.1') throw new Error('E_FA_C010_CONTROL_NOT_LOOPBACK');
  const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
  const v = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(v.error || `E_HTTP_${r.status}`);
  return v;
}
function validateRequest(request) {
  if (request?.schema !== 'die.factory-asset.console-provider-canary-request.v1' || request?.task_id !== 'FA-C010') throw new Error('E_FA_C010_REQUEST');
  const clusterId = request?.routing_constraint?.cluster_id;
  if (!['cluster-a', 'cluster-b'].includes(clusterId) || request?.routing_constraint?.transport !== 'BROWSER_CDP') throw new Error('E_FA_C010_ROUTE_SCOPE');
  if (JSON.stringify(request?.routing_constraint?.allowed_provider_ids) !== JSON.stringify(['qwen'])) throw new Error('E_FA_C010_PROVIDER_SCOPE');
  if (request?.routing_constraint?.direct_gui_provider_browser_ownership !== false) throw new Error('E_FA_C010_GUI_OWNERSHIP');
  const a = request?.authority || {};
  if (a.founder_authorized_live_provider_call !== true || a.spend_usd !== 0 || a.marketplace_submission_authorized !== false || a.publication_authorized !== false || a.account_creation_or_action_authorized !== false || a.captcha_checkpoint_bypass_authorized !== false || a.credential_cookie_token_session_value_read_authorized !== false) throw new Error('E_FA_C010_AUTHORITY');
}

const repoRoot = path.resolve(arg('--repo-root', path.resolve(import.meta.dirname, '../../..')));
const requestPath = path.resolve(arg('--request'));
const workspace = path.resolve(arg('--workspace'));
const playwrightEntry = path.resolve(arg('--playwright-entry', path.join(repoRoot, 'company/muxia/node_modules/playwright/index.mjs')));
const controlBaseUrl = String(arg('--control-base-url', 'http://127.0.0.1:39121'));
const request = readJson(requestPath);
validateRequest(request);
const expectedCluster = request.routing_constraint.cluster_id;
fs.mkdirSync(workspace, { recursive: true, mode: 0o750 });

const finalPath = path.join(workspace, 'provider-executor-result.json');
const journalPath = path.join(workspace, 'provider-attempt.json');
const generationCommitPath = path.join(workspace, 'generation-commit.json');
const readinessPath = path.join(workspace, 'provider-readiness.json');
if (fs.existsSync(finalPath)) {
  const prior = readJson(finalPath);
  if (prior?.schema !== 'die.factory-asset.console-provider-executor.v1' || prior?.job_id !== request.job_id || prior?.idempotency_key !== request.idempotency_key || prior?.result !== 'PASS') throw new Error('E_FA_C010_EXECUTOR_FINAL_CONFLICT');
  process.stdout.write(`${JSON.stringify({ ...prior, idempotent_replay: true, provider_call_performed: false })}\n`);
  process.exit(0);
}
if (fs.existsSync(journalPath)) {
  const prior = readJson(journalPath);
  if (prior?.dispatch_committed === true) throw new Error('E_FA_C010_PRIOR_DISPATCH_COMMITTED');
  throw new Error('E_FA_C010_PRIOR_ATTEMPT_PRESENT');
}

const beforeRaw = await requestJson(controlBaseUrl, '/v1/status');
const before = safeStatus(beforeRaw);
if (before.cluster_id !== expectedCluster || before.state !== 'READY') throw new Error(`E_FA_C010_CLUSTER_NOT_READY:${before.cluster_id}:${before.state}`);
if (before.active_leases !== 0 || !Number.isInteger(before.open_pages) || before.open_pages > before.max_tabs) throw new Error('E_FA_C010_CLUSTER_BUSY');

const registry = readJson(path.join(repoRoot, 'company/factory-asset/registries/web-ai-clusters.v1.json'));
const cluster = registry.clusters.find((x) => x.cluster_id === expectedCluster);
if (!cluster || !['ACTIVE', 'ACTIVE_REFERENCE'].includes(cluster.lifecycle_state)) throw new Error('E_FA_C010_CLUSTER_REGISTRY');
const qwenMembership = cluster.providers?.find((x) => x.provider_id === 'qwen');
if (!qwenMembership || qwenMembership.membership !== 'ACTIVE') throw new Error('E_FA_C010_QWEN_CLUSTER_MEMBERSHIP');
const readinessProfiles = readJson(path.join(repoRoot, 'company/factory-asset/registries/provider-readiness-profiles.v1.json'));
const qwenProfile = readinessProfiles.providers?.qwen;
if (!qwenProfile) throw new Error('E_FA_C010_QWEN_PROFILE');
const providerConfig = {
  generation_enabled: true,
  browser_url: 'https://chat.qwen.ai/',
  actual_live_transport: 'BROWSER_CDP',
  transport_role: 'FALLBACK',
  primary_transport_contract: 'SESSION_API',
  session_api_live_executor_claimed: false,
};

const readiness = await probeConsoleProvider({
  controlBaseUrl,
  playwrightEntry,
  providerId: 'qwen',
  providerConfig,
  readinessProfile: qwenProfile,
  jobId: `${request.job_id}-preflight`,
  clusterId: expectedCluster,
  ttlMs: 120000,
});
atomicJson(readinessPath, readiness);
if (readiness.status !== 'OBSERVED' || readiness.readiness?.state !== 'HEALTHY') {
  const state = readiness.readiness?.state || readiness.failure_code || readiness.status || 'UNKNOWN';
  throw new Error(`E_FA_C010_QWEN_NOT_HEALTHY:${state}`);
}

const routedRaw = await requestJson(controlBaseUrl, '/v1/status');
const routedBroker = safeStatus(routedRaw);
if (routedBroker.cluster_id !== expectedCluster || routedBroker.browser_owner_pid !== before.browser_owner_pid) throw new Error('E_FA_C010_BROKER_OWNER_DRIFT_PRE_DISPATCH');
if (routedBroker.active_leases !== 0 || routedBroker.open_pages > routedBroker.max_tabs) throw new Error('E_FA_C010_PREFLIGHT_LEASE_LEAK');

const observedAt = nowIso();
const tabSnapshot = routedRaw.tab_leases;
const candidate = {
  provider_id: 'qwen',
  cluster_id: expectedCluster,
  transport: 'BROWSER_CDP',
  enabled: true,
  policy_allowed: true,
  asset_types: ['PHOTO'],
  readiness: readiness.readiness,
  capacity: { provider_id: 'qwen', cluster_id: expectedCluster, state: 'AVAILABLE', observed_at: observedAt, basis: 'BROKER_ACTIVE_LEASES_BELOW_LIMIT' },
  tab_capacity: { cluster_id: expectedCluster, observed_at: observedAt, snapshot: tabSnapshot },
  provider_tab_limit: cluster.provider_tab_limits?.qwen || 1,
  cluster_browser_generation_limit: cluster.max_active_browser_generations,
  recent_failures: 0,
  latency_ms: Number.isFinite(readiness.latency_ms) ? readiness.latency_ms : 1000,
  priority: 0,
};
const queue = { schema: 'die.factory-asset.queue-observation.v1', depth: 0, limit: 1, observed_at: observedAt };
const scheduler = new MultiClusterScheduler({ config: { max_retries: 0 } });
const job = { job_id: request.job_id, idempotency_key: request.idempotency_key, asset_type: request.asset_type, intent: { source_surface: 'FACTORY_CONSOLE', blueprint_id: request.blueprint_id, semantic_asset_id: request.semantic_asset_id } };
const route = scheduler.schedule({ job, candidates: [candidate], queue });
if (route.provider_id !== 'qwen' || route.cluster_id !== expectedCluster || route.transport !== 'BROWSER_CDP' || route.requires_tab_lease !== true || route.browser_owner_action !== 'NONE') throw new Error('E_FA_C010_ROUTER_TRUTH');

let generationCommit = null;
let commitError = null;
const providerPromise = generateConsoleProviderImage({
  controlBaseUrl,
  playwrightEntry,
  providerId: 'qwen',
  providerConfig,
  readinessProfile: qwenProfile,
  jobId: request.job_id,
  prompt: request.prompt,
  artifactDir: path.join(workspace, 'provider-artifact'),
  clusterId: expectedCluster,
  journalPath,
  ttlMs: 420000,
  timeoutMs: 300000,
});
const poll = setInterval(() => {
  if (generationCommit || commitError || !fs.existsSync(journalPath)) return;
  try {
    const j = readJson(journalPath);
    if (j.dispatch_committed === true && j.dispatch_committed_at) {
      generationCommit = scheduler.markDispatchCommitted({ idempotencyKey: request.idempotency_key, attempt: route.attempt, externalCommitKey: `qwen:${expectedCluster}:${request.job_id}:${j.dispatch_committed_at}` });
      atomicJson(generationCommitPath, generationCommit);
    }
  } catch (error) {
    commitError = error;
  }
}, 50);
const attempt = await providerPromise;
clearInterval(poll);
if (commitError) throw commitError;
if (attempt.dispatch_committed === true && !generationCommit) {
  generationCommit = scheduler.markDispatchCommitted({ idempotencyKey: request.idempotency_key, attempt: route.attempt, externalCommitKey: `qwen:${expectedCluster}:${request.job_id}:${attempt.dispatch_committed_at}` });
  atomicJson(generationCommitPath, generationCommit);
}
if (attempt.status !== 'SUCCEEDED') {
  const code = attempt.failure_code || 'PROVIDER_FAILED';
  throw new Error(`E_FA_C010_PROVIDER:${code}:dispatch_committed=${attempt.dispatch_committed === true}`);
}
if (!generationCommit) throw new Error('E_FA_C010_MISSING_GENERATION_COMMIT');
const completion = scheduler.complete({ idempotencyKey: request.idempotency_key });
const afterRaw = await requestJson(controlBaseUrl, '/v1/status');
const after = safeStatus(afterRaw);
if (after.cluster_id !== expectedCluster || after.browser_owner_pid !== before.browser_owner_pid || after.active_leases !== 0 || after.open_pages > after.max_tabs) throw new Error('E_FA_C010_BROKER_POSTCONDITION');

const result = {
  schema: 'die.factory-asset.console-provider-executor.v1',
  task_id: 'FA-C010',
  result: 'PASS',
  status: 'SUCCEEDED',
  job_id: request.job_id,
  idempotency_key: request.idempotency_key,
  route,
  generation_commit: generationCommit,
  dispatch_committed_count: 1,
  completion,
  readiness,
  artifact: attempt.artifact,
  provider_attempt: {
    schema: attempt.schema,
    provider_id: attempt.provider_id,
    cluster_id: attempt.cluster_id,
    actual_transport: attempt.actual_transport,
    transport_role: attempt.transport_role,
    primary_transport_contract: attempt.primary_transport_contract,
    qwen_session_api_live_executor_claimed: attempt.qwen_session_api_live_executor_claimed,
    prompt_sha256: attempt.prompt_sha256,
    started_at: attempt.started_at,
    dispatch_committed: attempt.dispatch_committed,
    dispatch_committed_at: attempt.dispatch_committed_at,
    completed_at: attempt.completed_at,
    latency_ms: attempt.latency_ms,
    original_byte_acquisition_method: attempt.artifact?.original_byte_acquisition_method || null,
    lease_release: attempt.lease_release || null,
  },
  broker_before: before,
  broker_after: after,
  browser_owner_action: 'NONE',
  direct_gui_provider_browser_ownership: false,
  provider_call_performed: true,
  credential_values_read: false,
  cookies_or_tokens_read: false,
  provider_login_automated: false,
  submission_authorized: false,
  publication_authorized: false,
  spend_usd: 0,
  cluster_b_runtime_used: expectedCluster === 'cluster-b',
  cluster_b_auth_touched: false,
  fa305_306_canonical_state_touched: false,
  fa121_state_touched: false,
  production_runtime_touched: false,
};
atomicJson(finalPath, result);
process.stdout.write(`${JSON.stringify(result)}\n`);
