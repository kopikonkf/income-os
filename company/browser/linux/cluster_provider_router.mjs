import crypto from 'node:crypto';

const READINESS_SCHEDULABLE = new Set(['HEALTHY']);
const CAPACITY_SCHEDULABLE = new Set(['AVAILABLE']);
const RETRYABLE_FAILURES = new Set(['RATE_LIMITED', 'CAPACITY_UNAVAILABLE', 'PROVIDER_TIMEOUT', 'PROVIDER_ERROR', 'LEASE_LOST']);
const VALID_TRANSPORTS = new Set(['SESSION_API', 'BROWSER_CDP']);
const BLOCKING_TAB_PROVIDER_STATES = new Set(['AUTH_REQUIRED', 'CHECKPOINT', 'UNAVAILABLE']);

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}

function sha(value) { return crypto.createHash('sha256').update(stable(value)).digest('hex'); }
function finiteNumber(value) { return typeof value === 'number' && Number.isFinite(value); }
function copy(value) { return value === undefined ? undefined : JSON.parse(JSON.stringify(value)); }
function routeKey(candidate) { return `${candidate.provider_id}@${candidate.cluster_id}:${candidate.transport}`; }

export class ClusterRoutingError extends Error {
  constructor(code, message, details = null) {
    super(`${code}: ${message}`);
    this.code = code;
    this.details = details;
  }
}

function parseTime(raw) {
  if (typeof raw !== 'string' || !raw) return Number.NaN;
  const value = Date.parse(raw);
  return Number.isFinite(value) ? value : Number.NaN;
}

function freshness(record, nowMs, maxAgeMs, label) {
  if (!record || typeof record !== 'object') return { ok: false, reason: `${label}_UNKNOWN` };
  const observed = parseTime(record.observed_at);
  if (!Number.isFinite(observed)) return { ok: false, reason: `${label}_OBSERVED_AT_MISSING` };
  if (observed > nowMs + 1000) return { ok: false, reason: `${label}_OBSERVED_AT_FUTURE` };
  if (nowMs - observed > maxAgeMs) return { ok: false, reason: `${label}_STALE` };
  return { ok: true, age_ms: nowMs - observed };
}

function queueFacts(queue, nowMs, maxAgeMs) {
  const fresh = freshness(queue, nowMs, maxAgeMs, 'QUEUE');
  if (!fresh.ok) return { ok: false, reasons: [fresh.reason] };
  if (!Number.isInteger(queue.depth) || queue.depth < 0 || !Number.isInteger(queue.limit) || queue.limit < 1) {
    return { ok: false, reasons: ['QUEUE_BOUNDS_INVALID'] };
  }
  if (queue.depth >= queue.limit) return { ok: false, reasons: ['QUEUE_BACKPRESSURE'] };
  return { ok: true, pressure: queue.depth / queue.limit, age_ms: fresh.age_ms };
}

function browserFacts(candidate, nowMs, maxAgeMs) {
  const wrapper = candidate.tab_capacity;
  const fresh = freshness(wrapper, nowMs, maxAgeMs, 'TAB_CAPACITY');
  if (!fresh.ok) return { ok: false, reasons: [fresh.reason] };
  if (!wrapper?.cluster_id) return { ok: false, reasons: ['TAB_CAPACITY_CLUSTER_KEY_UNKNOWN'] };
  if (wrapper.cluster_id !== candidate.cluster_id) return { ok: false, reasons: ['TAB_CAPACITY_CLUSTER_KEY_MISMATCH'] };
  const snapshot = wrapper?.snapshot;
  if (!snapshot || snapshot.schema !== 'die.muxia.cluster-tab-lease-snapshot.v1') {
    return { ok: false, reasons: ['TAB_CAPACITY_SCHEMA_INVALID'] };
  }
  if (!Number.isInteger(snapshot.max_tabs) || snapshot.max_tabs < 1 || snapshot.max_tabs > 8) {
    return { ok: false, reasons: ['TAB_MAX_INVALID'] };
  }
  if (!Number.isInteger(snapshot.active_leases) || snapshot.active_leases < 0 || snapshot.active_leases > snapshot.max_tabs) {
    return { ok: false, reasons: ['TAB_ACTIVE_INVALID'] };
  }
  if (!Number.isInteger(snapshot.open_pages) || snapshot.open_pages < snapshot.active_leases) {
    return { ok: false, reasons: ['TAB_OPEN_PAGES_INVALID'] };
  }
  if (snapshot.open_pages > snapshot.max_tabs) return { ok: false, reasons: ['CLUSTER_OPEN_PAGES_OVER_BUDGET'] };
  const providerLimit = candidate.provider_tab_limit;
  if (!Number.isInteger(providerLimit) || providerLimit < 1 || providerLimit > snapshot.max_tabs) {
    return { ok: false, reasons: ['PROVIDER_TAB_LIMIT_UNKNOWN'] };
  }
  const leases = Array.isArray(snapshot.leases) ? snapshot.leases : [];
  const providerActive = leases.filter((x) => x?.provider_id === candidate.provider_id).length;
  const providerState = snapshot.provider_states?.[candidate.provider_id] || 'HEALTHY';
  if (BLOCKING_TAB_PROVIDER_STATES.has(providerState)) {
    return { ok: false, reasons: [`TAB_PROVIDER_STATE_${providerState}`] };
  }
  const browserGenerationLimit = candidate.cluster_browser_generation_limit;
  if (!Number.isInteger(browserGenerationLimit) || browserGenerationLimit < 1 || browserGenerationLimit > snapshot.max_tabs) {
    return { ok: false, reasons: ['CLUSTER_BROWSER_GENERATION_LIMIT_UNKNOWN'] };
  }
  if (snapshot.active_leases >= browserGenerationLimit || snapshot.active_leases >= snapshot.max_tabs) {
    return { ok: false, reasons: ['CLUSTER_TAB_BACKPRESSURE'] };
  }
  if (providerActive >= providerLimit) return { ok: false, reasons: ['PROVIDER_TAB_BACKPRESSURE'] };
  return {
    ok: true,
    active_tabs: snapshot.active_leases,
    max_tabs: snapshot.max_tabs,
    browser_generation_limit: browserGenerationLimit,
    provider_active_tabs: providerActive,
    provider_tab_limit: providerLimit,
    load_ratio: snapshot.active_leases / browserGenerationLimit,
    age_ms: fresh.age_ms,
  };
}

function candidateFacts(candidate, job, queue, config, nowMs, historicalFailures) {
  const reasons = [];
  if (!candidate || typeof candidate !== 'object') return { eligible: false, reasons: ['CANDIDATE_INVALID'] };
  if (!candidate.provider_id || !candidate.cluster_id) reasons.push('ROUTE_IDENTITY_INVALID');
  if (!VALID_TRANSPORTS.has(candidate.transport)) reasons.push('TRANSPORT_UNKNOWN');
  if (candidate.enabled === false) reasons.push('ROUTE_DISABLED');
  if (candidate.policy_allowed !== true) reasons.push('POLICY_NOT_ALLOWED');
  if (!Array.isArray(candidate.asset_types) || !candidate.asset_types.includes(job.asset_type)) reasons.push('CAPABILITY_MISMATCH');

  const readyFresh = freshness(candidate.readiness, nowMs, config.readiness_freshness_ms, 'READINESS');
  if (!readyFresh.ok) reasons.push(readyFresh.reason);
  else {
    if (!candidate.readiness.provider_id) reasons.push('READINESS_PROVIDER_KEY_UNKNOWN');
    else if (candidate.readiness.provider_id !== candidate.provider_id) reasons.push('READINESS_PROVIDER_KEY_MISMATCH');
    if (!READINESS_SCHEDULABLE.has(candidate.readiness.state)) reasons.push(`READINESS_${candidate.readiness.state || 'UNKNOWN'}`);
  }

  const capacityFresh = freshness(candidate.capacity, nowMs, config.capacity_freshness_ms, 'CAPACITY');
  if (!capacityFresh.ok) reasons.push(capacityFresh.reason);
  else {
    if (!candidate.capacity.provider_id || !candidate.capacity.cluster_id) reasons.push('CAPACITY_KEY_UNKNOWN');
    else {
      if (candidate.capacity.provider_id !== candidate.provider_id) reasons.push('CAPACITY_PROVIDER_KEY_MISMATCH');
      if (candidate.capacity.cluster_id !== candidate.cluster_id) reasons.push('CAPACITY_CLUSTER_KEY_MISMATCH');
    }
    if (!CAPACITY_SCHEDULABLE.has(candidate.capacity.state)) reasons.push(`CAPACITY_${candidate.capacity.state || 'UNKNOWN'}`);
  }

  const q = queueFacts(candidate.queue || queue, nowMs, config.queue_freshness_ms);
  if (!q.ok) reasons.push(...q.reasons);

  const recentFailures = candidate.recent_failures;
  if (!Number.isInteger(recentFailures) || recentFailures < 0) reasons.push('RECENT_FAILURES_UNKNOWN');
  const effectiveFailures = Number.isInteger(recentFailures) ? recentFailures + historicalFailures : Number.POSITIVE_INFINITY;
  if (effectiveFailures >= config.recent_failure_circuit_threshold) reasons.push('RECENT_FAILURE_CIRCUIT_OPEN');

  if (!finiteNumber(candidate.latency_ms) || candidate.latency_ms < 0) reasons.push('LATENCY_UNKNOWN');

  let browser = null;
  if (candidate.transport === 'BROWSER_CDP') {
    browser = browserFacts(candidate, nowMs, config.tab_capacity_freshness_ms);
    if (!browser.ok) reasons.push(...browser.reasons);
  }

  if (reasons.length) return { eligible: false, reasons: [...new Set(reasons)] };

  const queuePressure = q.pressure;
  const browserLoad = browser ? browser.load_ratio : 0;
  const preferredTransportBonus = candidate.provider_id === 'qwen' && candidate.transport === 'SESSION_API'
    ? config.qwen_session_api_bonus
    : (candidate.transport === 'SESSION_API' ? config.session_api_bonus : 0);
  const score = preferredTransportBonus
    - (queuePressure * config.queue_pressure_weight)
    - (effectiveFailures * config.recent_failure_weight)
    - (candidate.latency_ms * config.latency_weight)
    - (browserLoad * config.tab_load_weight)
    - (Number.isInteger(candidate.priority) ? candidate.priority : 1000) * config.priority_weight;

  return {
    eligible: true,
    score,
    queue_pressure: queuePressure,
    effective_recent_failures: effectiveFailures,
    latency_ms: candidate.latency_ms,
    browser,
    readiness_age_ms: readyFresh.age_ms,
    capacity_age_ms: capacityFresh.age_ms,
  };
}

export const DEFAULT_CLUSTER_ROUTING_CONFIG = Object.freeze({
  readiness_freshness_ms: 300000,
  capacity_freshness_ms: 300000,
  tab_capacity_freshness_ms: 300000,
  queue_freshness_ms: 300000,
  max_retries: 2,
  recent_failure_circuit_threshold: 3,
  qwen_session_api_bonus: 10000,
  session_api_bonus: 2500,
  queue_pressure_weight: 1200,
  recent_failure_weight: 900,
  latency_weight: 0.5,
  tab_load_weight: 1000,
  priority_weight: 0.1,
});

function validateConfig(config) {
  for (const key of ['readiness_freshness_ms', 'capacity_freshness_ms', 'tab_capacity_freshness_ms', 'queue_freshness_ms']) {
    if (!Number.isInteger(config[key]) || config[key] < 1000) throw new ClusterRoutingError('E_ROUTER_CONFIG', key);
  }
  if (!Number.isInteger(config.max_retries) || config.max_retries < 0 || config.max_retries > 5) throw new ClusterRoutingError('E_ROUTER_CONFIG', 'max_retries');
  if (!Number.isInteger(config.recent_failure_circuit_threshold) || config.recent_failure_circuit_threshold < 1) throw new ClusterRoutingError('E_ROUTER_CONFIG', 'recent_failure_circuit_threshold');
}

function validateJob(job) {
  if (!job || typeof job !== 'object' || !job.job_id || !job.idempotency_key || !job.asset_type) {
    throw new ClusterRoutingError('E_JOB_INVALID', 'job_id, idempotency_key and asset_type are required');
  }
}

export class ClusterAwareProviderRouter {
  constructor({ config = {}, now = () => Date.now() } = {}) {
    this.config = { ...DEFAULT_CLUSTER_ROUTING_CONFIG, ...config };
    validateConfig(this.config);
    this.now = now;
    this.jobs = new Map();
  }

  _intentHash(job) {
    return sha({ job_id: job.job_id, asset_type: job.asset_type, intent: job.intent || null });
  }

  _choose({ job, candidates, queue, state, attempt }) {
    if (!Array.isArray(candidates) || candidates.length === 0) throw new ClusterRoutingError('E_NO_CANDIDATES', job.job_id);
    const nowMs = this.now();
    const accepted = [];
    const rejected = [];
    for (const candidate of candidates) {
      const key = routeKey(candidate || {});
      const historicalFailures = state.route_failures[key] || 0;
      const facts = candidateFacts(candidate, job, queue, this.config, nowMs, historicalFailures);
      if (!facts.eligible) {
        rejected.push({ provider_id: candidate?.provider_id || null, cluster_id: candidate?.cluster_id || null, transport: candidate?.transport || null, reasons: facts.reasons });
        continue;
      }
      accepted.push({ candidate, facts, key });
    }
    if (!accepted.length) throw new ClusterRoutingError('E_NO_ELIGIBLE_ROUTE', job.job_id, { rejected });
    accepted.sort((a, b) => (
      b.facts.score - a.facts.score
      || (a.candidate.priority ?? 1000) - (b.candidate.priority ?? 1000)
      || a.key.localeCompare(b.key)
    ));
    const selected = accepted[0];
    const routeId = sha({ idempotency_key: job.idempotency_key, attempt, route: selected.key });
    return {
      schema: 'die.factory-asset.cluster-provider-route.v1',
      job_id: job.job_id,
      idempotency_key: job.idempotency_key,
      attempt,
      retry_index: attempt - 1,
      route_id: routeId,
      provider_id: selected.candidate.provider_id,
      cluster_id: selected.candidate.cluster_id,
      transport: selected.candidate.transport,
      requires_tab_lease: selected.candidate.transport === 'BROWSER_CDP',
      tab_capacity_consumed_by_router: false,
      browser_owner_action: 'NONE',
      score: Number(selected.facts.score.toFixed(6)),
      factors: {
        readiness_state: selected.candidate.readiness.state,
        capacity_state: selected.candidate.capacity.state,
        queue_pressure: Number(selected.facts.queue_pressure.toFixed(6)),
        active_tab_load: selected.facts.browser ? Number(selected.facts.browser.load_ratio.toFixed(6)) : 0,
        active_tabs: selected.facts.browser?.active_tabs ?? 0,
        browser_generation_limit: selected.facts.browser?.browser_generation_limit ?? null,
        provider_active_tabs: selected.facts.browser?.provider_active_tabs ?? 0,
        recent_failures: selected.facts.effective_recent_failures,
        latency_ms: selected.facts.latency_ms,
      },
      rejected,
      dispatch_committed: false,
      provider_calls_performed: false,
      idempotent_replay: false,
    };
  }

  route({ job, candidates, queue }) {
    validateJob(job);
    const intentHash = this._intentHash(job);
    const existing = this.jobs.get(job.idempotency_key);
    if (existing) {
      if (existing.intent_hash !== intentHash) throw new ClusterRoutingError('E_IDEMPOTENCY_CONFLICT', job.idempotency_key);
      const replay = copy(existing.attempts[existing.attempts.length - 1]);
      replay.idempotent_replay = true;
      return replay;
    }
    const state = { intent_hash: intentHash, attempts: [], retry_events: new Map(), route_failures: {}, job_asset_type: job.asset_type, job_intent: job.intent || null };
    const decision = this._choose({ job, candidates, queue, state, attempt: 1 });
    state.attempts.push(decision);
    this.jobs.set(job.idempotency_key, state);
    return copy(decision);
  }

  markDispatchCommitted({ idempotencyKey, attempt }) {
    const state = this.jobs.get(idempotencyKey);
    if (!state) throw new ClusterRoutingError('E_JOB_NOT_ROUTED', idempotencyKey);
    const row = state.attempts.find((x) => x.attempt === attempt);
    if (!row) throw new ClusterRoutingError('E_ATTEMPT_NOT_FOUND', `${idempotencyKey}:${attempt}`);
    row.dispatch_committed = true;
    return copy(row);
  }

  retry({ idempotencyKey, eventId, failureCode, candidates, queue }) {
    const state = this.jobs.get(idempotencyKey);
    if (!state) throw new ClusterRoutingError('E_JOB_NOT_ROUTED', idempotencyKey);
    if (!eventId || typeof eventId !== 'string') throw new ClusterRoutingError('E_RETRY_EVENT_INVALID', 'eventId required');
    if (state.retry_events.has(eventId)) {
      const prior = state.retry_events.get(eventId);
      if (prior.kind === 'error') throw new ClusterRoutingError(prior.code, prior.message, copy(prior.details));
      const replay = copy(prior.decision);
      replay.idempotent_replay = true;
      return replay;
    }
    const last = state.attempts[state.attempts.length - 1];
    if (last.dispatch_committed) throw new ClusterRoutingError('E_RETRY_AFTER_DISPATCH_COMMIT', idempotencyKey);
    if (!RETRYABLE_FAILURES.has(failureCode)) throw new ClusterRoutingError('E_FAILURE_NOT_RETRYABLE', failureCode);
    const retriesUsed = state.attempts.length - 1;
    if (retriesUsed >= this.config.max_retries) throw new ClusterRoutingError('E_RETRY_LIMIT', idempotencyKey);
    const failedKey = `${last.provider_id}@${last.cluster_id}:${last.transport}`;
    state.route_failures[failedKey] = (state.route_failures[failedKey] || 0) + 1;
    const job = { job_id: last.job_id, idempotency_key: last.idempotency_key, asset_type: state.asset_type || null, intent: state.intent || null };
    // Preserve the original identity without storing arbitrary provider payloads.
    const originalAssetType = state.job_asset_type;
    if (!originalAssetType) throw new ClusterRoutingError('E_ROUTER_STATE_INVALID', 'asset type missing');
    job.asset_type = originalAssetType;
    job.intent = state.job_intent || null;
    let decision;
    try {
      decision = this._choose({ job, candidates, queue, state, attempt: state.attempts.length + 1 });
    } catch (error) {
      if (error instanceof ClusterRoutingError) {
        const rawMessage = error.message.startsWith(`${error.code}: `) ? error.message.slice(error.code.length + 2) : error.message;
        state.retry_events.set(eventId, { kind: 'error', code: error.code, message: rawMessage, details: copy(error.details) });
      }
      throw error;
    }
    state.attempts.push(decision);
    state.retry_events.set(eventId, { kind: 'decision', decision });
    return copy(decision);
  }

  snapshot(idempotencyKey) {
    const state = this.jobs.get(idempotencyKey);
    if (!state) return null;
    return {
      schema: 'die.factory-asset.cluster-provider-router-state.v1',
      idempotency_key: idempotencyKey,
      attempts: state.attempts.map((x) => copy(x)),
      retries_used: Math.max(0, state.attempts.length - 1),
      max_retries: this.config.max_retries,
      route_failures: { ...state.route_failures },
    };
  }
}
