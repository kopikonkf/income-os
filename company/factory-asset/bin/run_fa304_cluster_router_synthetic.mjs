#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ClusterAwareProviderRouter, ClusterRoutingError } from '../../browser/linux/cluster_provider_router.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const CLUSTERS = JSON.parse(fs.readFileSync(path.join(ROOT, 'company/factory-asset/registries/web-ai-clusters.v1.json'), 'utf8'));
const NOW = Date.parse('2026-09-05T19:45:00Z');
const OBS = '2026-09-05T19:44:00Z';
const STALE = '2026-09-05T18:00:00Z';

function tabSnapshot({ active = 0, states = {}, leases = [] } = {}) {
  return {
    schema: 'die.muxia.cluster-tab-lease-snapshot.v1',
    max_tabs: 8,
    active_leases: active,
    open_pages: active,
    provider_states: states,
    leases,
  };
}

function browserCandidate(provider, cluster = 'cluster-a', overrides = {}) {
  const member = CLUSTERS.clusters[0].providers.find((x) => x.provider_id === provider);
  return {
    provider_id: provider,
    cluster_id: cluster,
    transport: 'BROWSER_CDP',
    enabled: true,
    policy_allowed: true,
    asset_types: ['PHOTO', 'ISOLATED_OBJECT'],
    readiness: { state: 'HEALTHY', observed_at: OBS },
    capacity: { state: 'AVAILABLE', observed_at: OBS },
    tab_capacity: { observed_at: OBS, snapshot: tabSnapshot() },
    provider_tab_limit: CLUSTERS.clusters[0].provider_tab_limits[provider] || 1,
    cluster_browser_generation_limit: CLUSTERS.clusters[0].max_active_browser_generations,
    recent_failures: 0,
    latency_ms: 900,
    priority: 100,
    evidence_membership: member?.membership || 'SYNTHETIC',
    ...overrides,
  };
}

function qwenSession(overrides = {}) {
  return {
    provider_id: 'qwen',
    cluster_id: 'cluster-a',
    transport: 'SESSION_API',
    enabled: true,
    policy_allowed: true,
    asset_types: ['PHOTO', 'ISOLATED_OBJECT'],
    readiness: { state: 'HEALTHY', observed_at: OBS },
    capacity: { state: 'AVAILABLE', observed_at: OBS },
    recent_failures: 0,
    latency_ms: 1200,
    priority: 10,
    ...overrides,
  };
}

function queue(depth = 10, limit = 256, observed_at = OBS) { return { depth, limit, observed_at }; }
function job(id) { return { job_id: id, idempotency_key: `idem-${id}`, asset_type: 'PHOTO', intent: { semantic_asset_id: `asset-${id}` } }; }
function expectCode(fn, code) {
  try { fn(); } catch (error) {
    if (error instanceof ClusterRoutingError && error.code === code) return { code, details: error.details || null };
    throw error;
  }
  throw new Error(`EXPECTED_${code}`);
}

const canonicalQwen = CLUSTERS.clusters[0].providers.find((x) => x.provider_id === 'qwen');
if (!canonicalQwen || canonicalQwen.preferred_transport !== 'SESSION_API' || canonicalQwen.browser_fallback !== 'BROWSER_CDP') {
  throw new Error('CANONICAL_QWEN_TRANSPORT_CONTRACT_MISMATCH');
}

const results = {};

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const browserBusy = tabSnapshot({ active: 4, leases: [
    { provider_id: 'chatgpt' }, { provider_id: 'gemini' }, { provider_id: 'manus' }, { provider_id: 'duckai' },
  ] });
  const decision = router.route({
    job: job('prefer-qwen-session'),
    queue: queue(20),
    candidates: [
      qwenSession({ latency_ms: 1800 }),
      browserCandidate('qwen', 'cluster-a', { latency_ms: 300, tab_capacity: { observed_at: OBS, snapshot: browserBusy } }),
      browserCandidate('gemini', 'cluster-a', { latency_ms: 250, tab_capacity: { observed_at: OBS, snapshot: browserBusy } }),
    ],
  });
  if (decision.provider_id !== 'qwen' || decision.transport !== 'SESSION_API' || decision.requires_tab_lease !== false) throw new Error('QWEN_SESSION_NOT_PREFERRED');
  results.qwen_session_preferred = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const heavy = tabSnapshot({ active: 4, leases: [{ provider_id: 'chatgpt' }, { provider_id: 'manus' }, { provider_id: 'duckai' }, { provider_id: 'qwen' }] });
  const light = tabSnapshot({ active: 0, leases: [] });
  const decision = router.route({
    job: job('choose-cluster-load'),
    queue: queue(40),
    candidates: [
      browserCandidate('gemini', 'synthetic-cluster-a', { latency_ms: 600, tab_capacity: { observed_at: OBS, snapshot: heavy }, provider_tab_limit: 1 }),
      browserCandidate('gemini', 'synthetic-cluster-b', { latency_ms: 650, tab_capacity: { observed_at: OBS, snapshot: light }, provider_tab_limit: 1 }),
    ],
  });
  if (decision.cluster_id !== 'synthetic-cluster-b' || decision.requires_tab_lease !== true) throw new Error('LOW_LOAD_CLUSTER_NOT_SELECTED');
  results.active_tab_load_cluster_choice = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const decision = router.route({
    job: job('sibling-isolation'),
    queue: queue(20),
    candidates: [
      browserCandidate('chatgpt', 'cluster-a', { readiness: { state: 'CHECKPOINT', observed_at: OBS }, latency_ms: 200 }),
      browserCandidate('gemini', 'cluster-a', { latency_ms: 700 }),
    ],
  });
  if (decision.provider_id !== 'gemini') throw new Error('CHECKPOINT_BLOCKED_SIBLING');
  if (!decision.rejected.some((x) => x.provider_id === 'chatgpt' && x.reasons.includes('READINESS_CHECKPOINT'))) throw new Error('CHECKPOINT_NOT_RECORDED');
  results.provider_failure_isolation = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const decision = router.route({
    job: job('stale-failclosed'),
    queue: queue(10),
    candidates: [
      qwenSession({ readiness: { state: 'HEALTHY', observed_at: STALE }, capacity: { state: 'AVAILABLE', observed_at: STALE } }),
      browserCandidate('manus', 'cluster-a', { latency_ms: 800 }),
    ],
  });
  if (decision.provider_id !== 'manus') throw new Error('STALE_ROUTE_NOT_REJECTED');
  const stale = decision.rejected.find((x) => x.provider_id === 'qwen');
  if (!stale || !stale.reasons.includes('READINESS_STALE') || !stale.reasons.includes('CAPACITY_STALE')) throw new Error('STALE_REASONS_MISSING');
  results.stale_readiness_capacity_failclosed = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const decision = router.route({
    job: job('unknown-failclosed'),
    queue: queue(10),
    candidates: [
      qwenSession({ readiness: null, capacity: { state: 'UNKNOWN', observed_at: OBS } }),
      browserCandidate('manus', 'cluster-a', { latency_ms: 800 }),
    ],
  });
  if (decision.provider_id !== 'manus') throw new Error('UNKNOWN_ROUTE_NOT_REJECTED');
  const unknown = decision.rejected.find((x) => x.provider_id === 'qwen');
  if (!unknown || !unknown.reasons.includes('READINESS_UNKNOWN') || !unknown.reasons.includes('CAPACITY_UNKNOWN')) throw new Error('UNKNOWN_REASONS_MISSING');
  results.unknown_readiness_capacity_failclosed = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const full = tabSnapshot({ active: 5, leases: [
    { provider_id: 'chatgpt' }, { provider_id: 'qwen' }, { provider_id: 'gemini' }, { provider_id: 'manus' }, { provider_id: 'duckai' },
  ] });
  const decision = router.route({
    job: job('session-survives-browser-backpressure'),
    queue: queue(20),
    candidates: [
      qwenSession(),
      browserCandidate('gemini', 'cluster-a', { tab_capacity: { observed_at: OBS, snapshot: full } }),
    ],
  });
  if (decision.transport !== 'SESSION_API') throw new Error('SESSION_ROUTE_CONSUMED_BROWSER_CAPACITY');
  const blocked = decision.rejected.find((x) => x.provider_id === 'gemini');
  if (!blocked?.reasons.includes('CLUSTER_TAB_BACKPRESSURE')) throw new Error('BROWSER_BACKPRESSURE_NOT_RECORDED');
  results.session_api_does_not_consume_tab_capacity = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const lowQueue = { depth: 20, limit: 100, observed_at: OBS };
  const highQueue = { depth: 80, limit: 100, observed_at: OBS };
  const decision = router.route({
    job: job('queue-failure-latency-choice'),
    queue: queue(1),
    candidates: [
      browserCandidate('gemini', 'synthetic-cluster-a', { queue: highQueue, latency_ms: 200, recent_failures: 1 }),
      browserCandidate('manus', 'synthetic-cluster-b', { queue: lowQueue, latency_ms: 450, recent_failures: 0 }),
    ],
  });
  if (decision.provider_id !== 'manus') throw new Error('QUEUE_FAILURE_LATENCY_FACTORS_NOT_APPLIED');
  results.queue_failure_latency_choice = decision;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const blocked = expectCode(() => router.route({
    job: job('queue-full'),
    queue: queue(256, 256),
    candidates: [qwenSession(), browserCandidate('gemini')],
  }), 'E_NO_ELIGIBLE_ROUTE');
  const reasons = blocked.details.rejected.flatMap((x) => x.reasons);
  if (!reasons.includes('QUEUE_BACKPRESSURE')) throw new Error('QUEUE_BACKPRESSURE_NOT_FAILCLOSED');
  results.queue_backpressure_failclosed = blocked;
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const j = job('retry-idempotency');
  const initialCandidates = [qwenSession(), browserCandidate('gemini'), browserCandidate('manus')];
  const first = router.route({ job: j, queue: queue(10), candidates: initialCandidates });
  const replay = router.route({ job: j, queue: queue(10), candidates: initialCandidates });
  if (replay.route_id !== first.route_id || replay.attempt !== 1 || replay.idempotent_replay !== true) throw new Error('INITIAL_ROUTE_NOT_IDEMPOTENT');

  const afterQwenFailure = [
    qwenSession({ capacity: { state: 'UNAVAILABLE', observed_at: OBS } }),
    browserCandidate('gemini', 'cluster-a', { latency_ms: 500 }),
    browserCandidate('manus', 'cluster-a', { latency_ms: 900 }),
  ];
  const second = router.retry({ idempotencyKey: j.idempotency_key, eventId: 'retry-event-1', failureCode: 'RATE_LIMITED', candidates: afterQwenFailure, queue: queue(10) });
  const secondReplay = router.retry({ idempotencyKey: j.idempotency_key, eventId: 'retry-event-1', failureCode: 'RATE_LIMITED', candidates: afterQwenFailure, queue: queue(10) });
  if (second.attempt !== 2 || second.provider_id !== 'gemini' || secondReplay.route_id !== second.route_id || secondReplay.idempotent_replay !== true) throw new Error('RETRY_EVENT_NOT_IDEMPOTENT');

  const afterGeminiFailure = [
    qwenSession({ capacity: { state: 'UNAVAILABLE', observed_at: OBS } }),
    browserCandidate('gemini', 'cluster-a', { readiness: { state: 'CHECKPOINT', observed_at: OBS } }),
    browserCandidate('manus', 'cluster-a', { latency_ms: 800 }),
  ];
  const third = router.retry({ idempotencyKey: j.idempotency_key, eventId: 'retry-event-2', failureCode: 'PROVIDER_TIMEOUT', candidates: afterGeminiFailure, queue: queue(10) });
  if (third.attempt !== 3 || third.provider_id !== 'manus') throw new Error('SECOND_RETRY_NOT_ROUTED_TO_HEALTHY_SIBLING');
  const retryLimit = expectCode(() => router.retry({ idempotencyKey: j.idempotency_key, eventId: 'retry-event-3', failureCode: 'PROVIDER_TIMEOUT', candidates: afterGeminiFailure, queue: queue(10) }), 'E_RETRY_LIMIT');
  router.markDispatchCommitted({ idempotencyKey: j.idempotency_key, attempt: 3 });
  const afterCommit = expectCode(() => router.retry({ idempotencyKey: j.idempotency_key, eventId: 'retry-event-4', failureCode: 'PROVIDER_TIMEOUT', candidates: afterGeminiFailure, queue: queue(10) }), 'E_RETRY_AFTER_DISPATCH_COMMIT');
  const conflict = expectCode(() => router.route({ job: { ...j, intent: { semantic_asset_id: 'different' } }, queue: queue(10), candidates: initialCandidates }), 'E_IDEMPOTENCY_CONFLICT');
  results.retry_idempotency = { first, second, secondReplay, third, retryLimit, afterCommit, conflict, state: router.snapshot(j.idempotency_key) };
}

{
  const router = new ClusterAwareProviderRouter({ now: () => NOW });
  const j = job('retry-blocked-event');
  router.route({ job: j, queue: queue(10), candidates: [qwenSession()] });
  const blockedCandidates = [
    qwenSession({ capacity: { state: 'UNAVAILABLE', observed_at: OBS } }),
    browserCandidate('gemini', 'cluster-a', { readiness: { state: 'CHECKPOINT', observed_at: OBS } }),
  ];
  const firstError = expectCode(() => router.retry({ idempotencyKey: j.idempotency_key, eventId: 'blocked-retry-event', failureCode: 'RATE_LIMITED', candidates: blockedCandidates, queue: queue(10) }), 'E_NO_ELIGIBLE_ROUTE');
  const secondError = expectCode(() => router.retry({ idempotencyKey: j.idempotency_key, eventId: 'blocked-retry-event', failureCode: 'RATE_LIMITED', candidates: [browserCandidate('manus')], queue: queue(10) }), 'E_NO_ELIGIBLE_ROUTE');
  const state = router.snapshot(j.idempotency_key);
  if (state.retries_used !== 0 || firstError.code !== secondError.code) throw new Error('FAILED_RETRY_EVENT_NOT_IDEMPOTENT');
  results.failed_retry_event_idempotency = { firstError, secondError, state };
}

const assertions = {
  canonical_qwen_session_primary: canonicalQwen.preferred_transport === 'SESSION_API',
  qwen_session_preferred: results.qwen_session_preferred.transport === 'SESSION_API' && !results.qwen_session_preferred.requires_tab_lease,
  provider_plus_cluster_selection: results.active_tab_load_cluster_choice.cluster_id === 'synthetic-cluster-b',
  checkpoint_isolated: results.provider_failure_isolation.provider_id === 'gemini',
  stale_fail_closed: results.stale_readiness_capacity_failclosed.provider_id === 'manus',
  unknown_fail_closed: results.unknown_readiness_capacity_failclosed.provider_id === 'manus',
  browser_backpressure_isolated_from_session_api: results.session_api_does_not_consume_tab_capacity.transport === 'SESSION_API',
  queue_failure_latency_used: results.queue_failure_latency_choice.provider_id === 'manus',
  queue_backpressure_fail_closed: results.queue_backpressure_failclosed.code === 'E_NO_ELIGIBLE_ROUTE',
  retries_bounded_idempotent: results.retry_idempotency.state.retries_used === 2 && results.retry_idempotency.retryLimit.code === 'E_RETRY_LIMIT',
  failed_retry_event_idempotent: results.failed_retry_event_idempotency.state.retries_used === 0 && results.failed_retry_event_idempotency.secondError.code === 'E_NO_ELIGIBLE_ROUTE',
  no_retry_after_dispatch_commit: results.retry_idempotency.afterCommit.code === 'E_RETRY_AFTER_DISPATCH_COMMIT',
  zero_provider_calls: true,
};

const receipt = {
  schema: 'die.factory-asset.fa304-cluster-router-synthetic-acceptance.v1',
  task_id: 'FA-304',
  status: Object.values(assertions).every(Boolean) ? 'DONE' : 'FAILED',
  result: Object.values(assertions).every(Boolean) ? 'PASS' : 'FAIL',
  provider_calls_performed: false,
  browser_processes_spawned: 0,
  cluster_a_profile_mutated: false,
  canonical_inputs: {
    fa302_tab_lease_snapshot_schema: 'die.muxia.cluster-tab-lease-snapshot.v1',
    fa303_readiness_schema: 'die.muxia.provider-readiness.v1',
    fa120_queue_semantics: 'bounded depth/limit + freshness/backpressure',
    qwen_preferred_transport: canonicalQwen.preferred_transport,
    qwen_browser_fallback: canonicalQwen.browser_fallback,
  },
  assertions,
  evidence: results,
};

process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
if (receipt.result !== 'PASS') process.exitCode = 1;
