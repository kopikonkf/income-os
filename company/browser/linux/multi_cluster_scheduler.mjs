import crypto from 'node:crypto';
import { ClusterAwareProviderRouter, ClusterRoutingError } from './cluster_provider_router.mjs';

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
function sha(value) { return crypto.createHash('sha256').update(stable(value)).digest('hex'); }
function copy(value) { return value === undefined ? undefined : JSON.parse(JSON.stringify(value)); }
function routeKey(providerId, clusterId) { return `${providerId}@${clusterId}`; }

export class MultiClusterSchedulerError extends Error {
  constructor(code, message, details = null) {
    super(`${code}: ${message}`); this.code = code; this.details = details;
  }
}

export const DEFAULT_MULTI_CLUSTER_CONFIG = Object.freeze({
  queue_lease_ttl_ms: 300000,
  fairness_priority_step: 10000,
  provider_cluster_failure_threshold: 2,
  cluster_failure_threshold: 3,
  provider_cluster_cooldown_ms: 300000,
  cluster_cooldown_ms: 300000,
  max_retries: 2,
});

function validateConfig(c) {
  if (!Number.isInteger(c.queue_lease_ttl_ms) || c.queue_lease_ttl_ms < 1000 || c.queue_lease_ttl_ms > 3600000) throw new MultiClusterSchedulerError('E_MULTI_CONFIG','queue_lease_ttl_ms');
  if (!Number.isInteger(c.fairness_priority_step) || c.fairness_priority_step < 1) throw new MultiClusterSchedulerError('E_MULTI_CONFIG','fairness_priority_step');
  for (const k of ['provider_cluster_failure_threshold','cluster_failure_threshold']) if (!Number.isInteger(c[k]) || c[k] < 1) throw new MultiClusterSchedulerError('E_MULTI_CONFIG',k);
  for (const k of ['provider_cluster_cooldown_ms','cluster_cooldown_ms']) if (!Number.isInteger(c[k]) || c[k] < 1000) throw new MultiClusterSchedulerError('E_MULTI_CONFIG',k);
  if (!Number.isInteger(c.max_retries) || c.max_retries < 0 || c.max_retries > 5) throw new MultiClusterSchedulerError('E_MULTI_CONFIG','max_retries');
}
function validateJob(job) {
  if (!job || typeof job !== 'object' || !job.job_id || !job.idempotency_key || !job.asset_type) throw new MultiClusterSchedulerError('E_MULTI_JOB_INVALID','job_id, idempotency_key and asset_type required');
}

export class MultiClusterScheduler {
  constructor({ config = {}, routerConfig = {}, now = () => Date.now(), randomId = () => crypto.randomUUID() } = {}) {
    this.config = { ...DEFAULT_MULTI_CLUSTER_CONFIG, ...config }; validateConfig(this.config);
    this.now = now; this.randomId = randomId;
    this.router = new ClusterAwareProviderRouter({ config: { ...routerConfig, max_retries: this.config.max_retries }, now });
    this.jobs = new Map();
    this.activeJobIds = new Map();
    this.committedJobIds = new Map();
    this.clusterSelections = new Map();
    this.providerCircuits = new Map();
    this.clusterCircuits = new Map();
  }

  _intentHash(job) { return sha({ job_id: job.job_id, asset_type: job.asset_type, intent: job.intent || null }); }
  _circuitEntry(map, key) {
    if (!map.has(key)) map.set(key, { failures: 0, open_until_ms: 0, last_failure_code: null });
    return map.get(key);
  }
  _circuitState(map, key) {
    const e = this._circuitEntry(map, key);
    if (e.open_until_ms > this.now()) return { state: 'OPEN', failures: e.failures, open_until_ms: e.open_until_ms, last_failure_code: e.last_failure_code };
    if (e.open_until_ms && e.open_until_ms <= this.now()) { e.failures = 0; e.open_until_ms = 0; e.last_failure_code = null; }
    return { state: 'CLOSED', failures: e.failures, open_until_ms: 0, last_failure_code: e.last_failure_code };
  }
  _recordFailure(decision, failureCode) {
    const pk = routeKey(decision.provider_id, decision.cluster_id);
    const pe = this._circuitEntry(this.providerCircuits, pk); pe.failures += 1; pe.last_failure_code = failureCode;
    if (pe.failures >= this.config.provider_cluster_failure_threshold) pe.open_until_ms = this.now() + this.config.provider_cluster_cooldown_ms;
    const ce = this._circuitEntry(this.clusterCircuits, decision.cluster_id); ce.failures += 1; ce.last_failure_code = failureCode;
    if (ce.failures >= this.config.cluster_failure_threshold) ce.open_until_ms = this.now() + this.config.cluster_cooldown_ms;
  }
  _recordSuccess(decision) {
    const pk = routeKey(decision.provider_id, decision.cluster_id);
    this.providerCircuits.set(pk, { failures: 0, open_until_ms: 0, last_failure_code: null });
    this.clusterCircuits.set(decision.cluster_id, { failures: 0, open_until_ms: 0, last_failure_code: null });
  }
  _decorate(candidates) {
    return candidates.map((raw) => {
      const c = copy(raw); const clusterId = String(c.cluster_id || ''); const providerId = String(c.provider_id || '');
      const fairnessCount = this.clusterSelections.get(clusterId) || 0;
      c.priority = (Number.isInteger(c.priority) ? c.priority : 1000) + fairnessCount * this.config.fairness_priority_step;
      c.scheduler_fairness_count = fairnessCount;
      c.scheduler_provider_circuit = this._circuitState(this.providerCircuits, routeKey(providerId, clusterId));
      c.scheduler_cluster_circuit = this._circuitState(this.clusterCircuits, clusterId);
      if (c.scheduler_provider_circuit.state === 'OPEN' || c.scheduler_cluster_circuit.state === 'OPEN') c.enabled = false;
      return c;
    });
  }
  _registerSelection(decision) { this.clusterSelections.set(decision.cluster_id, (this.clusterSelections.get(decision.cluster_id) || 0) + 1); }
  _queueLease(job) {
    return { schema:'die.factory-asset.cross-cluster-queue-lease.v1', lease_id:this.randomId(), job_id:job.job_id, idempotency_key:job.idempotency_key, state:'LEASED', acquired_at_ms:this.now(), expires_at_ms:this.now()+this.config.queue_lease_ttl_ms, cluster_id:null, provider_id:null, route_id:null };
  }
  _publicLease(lease) {
    return { ...copy(lease), acquired_at:new Date(lease.acquired_at_ms).toISOString(), expires_at:new Date(lease.expires_at_ms).toISOString() };
  }
  _assertLeaseLive(state) {
    if (!state.committed && state.lease.state === 'LEASED' && state.lease.expires_at_ms <= this.now()) throw new MultiClusterSchedulerError('E_QUEUE_LEASE_EXPIRED', state.lease.job_id);
  }
  _augment(decision, state, { replay = false } = {}) {
    return { ...copy(decision), scheduler_schema:'die.factory-asset.multi-cluster-schedule.v1', queue_lease:this._publicLease(state.lease), fairness:{ cluster_selection_counts:Object.fromEntries([...this.clusterSelections.entries()].sort()), selected_cluster_prior_count:Math.max(0,(this.clusterSelections.get(decision.cluster_id)||1)-1) }, circuits:this.circuitSnapshot(), scheduler_idempotent_replay:replay, provider_calls_performed:false, browser_owner_action:'NONE' };
  }

  schedule({ job, candidates, queue }) {
    validateJob(job);
    const intentHash = this._intentHash(job);
    const existing = this.jobs.get(job.idempotency_key);
    if (existing) {
      if (existing.intent_hash !== intentHash) throw new MultiClusterSchedulerError('E_IDEMPOTENCY_CONFLICT',job.idempotency_key);
      this._assertLeaseLive(existing);
      return this._augment(existing.last_decision, existing, { replay:true });
    }
    if (this.committedJobIds.has(job.job_id)) throw new MultiClusterSchedulerError('E_JOB_ALREADY_COMMITTED',job.job_id,copy(this.committedJobIds.get(job.job_id)));
    const owner = this.activeJobIds.get(job.job_id);
    if (owner && owner !== job.idempotency_key) throw new MultiClusterSchedulerError('E_JOB_QUEUE_LEASE_CONFLICT',job.job_id,{active_idempotency_key:owner});
    const state = { job:copy(job), intent_hash:intentHash, lease:this._queueLease(job), last_decision:null, retry_events:new Map(), committed:null, complete:false };
    this.activeJobIds.set(job.job_id,job.idempotency_key);
    try {
      const decision=this.router.route({job,candidates:this._decorate(candidates),queue});
      state.last_decision=decision;state.lease.cluster_id=decision.cluster_id;state.lease.provider_id=decision.provider_id;state.lease.route_id=decision.route_id;
      this._registerSelection(decision);this.jobs.set(job.idempotency_key,state);
      return this._augment(decision,state);
    } catch (error) { this.activeJobIds.delete(job.job_id); throw error; }
  }

  reportPreDispatchFailure({ idempotencyKey, eventId, failureCode, candidates, queue }) {
    const state=this.jobs.get(idempotencyKey); if(!state) throw new MultiClusterSchedulerError('E_JOB_NOT_SCHEDULED',idempotencyKey);
    this._assertLeaseLive(state);
    if(state.committed) throw new MultiClusterSchedulerError('E_RETRY_AFTER_DISPATCH_COMMIT',idempotencyKey);
    if(!eventId || typeof eventId!=='string') throw new MultiClusterSchedulerError('E_FAILURE_EVENT_INVALID','eventId required');
    if(state.retry_events.has(eventId)) {
      const prior=state.retry_events.get(eventId); if(prior.kind==='error') throw new MultiClusterSchedulerError(prior.code,prior.message,copy(prior.details));
      return this._augment(prior.decision,state,{replay:true});
    }
    this._recordFailure(state.last_decision,failureCode);
    try {
      const d=this.router.retry({idempotencyKey,eventId,failureCode,candidates:this._decorate(candidates),queue});
      state.last_decision=d;state.lease.cluster_id=d.cluster_id;state.lease.provider_id=d.provider_id;state.lease.route_id=d.route_id;
      this._registerSelection(d);state.retry_events.set(eventId,{kind:'decision',decision:copy(d)});return this._augment(d,state);
    } catch(error) {
      const code=error?.code||'E_RETRY_FAILED';const message=String(error?.message||error);const details=copy(error?.details||null);
      state.retry_events.set(eventId,{kind:'error',code,message,details});throw error;
    }
  }

  markDispatchCommitted({ idempotencyKey, attempt, externalCommitKey }) {
    const state=this.jobs.get(idempotencyKey); if(!state) throw new MultiClusterSchedulerError('E_JOB_NOT_SCHEDULED',idempotencyKey);
    if(!externalCommitKey || typeof externalCommitKey!=='string') throw new MultiClusterSchedulerError('E_COMMIT_KEY_INVALID','externalCommitKey required');
    if(state.committed) {
      if(state.committed.attempt===attempt && state.committed.external_commit_key===externalCommitKey) return {...copy(state.committed),idempotent_replay:true};
      throw new MultiClusterSchedulerError('E_DUPLICATE_GENERATION_COMMIT',idempotencyKey,copy(state.committed));
    }
    if(state.last_decision.attempt!==attempt) throw new MultiClusterSchedulerError('E_COMMIT_ATTEMPT_NOT_CURRENT',`${attempt}`);
    const priorByJob=this.committedJobIds.get(state.job.job_id); if(priorByJob) throw new MultiClusterSchedulerError('E_JOB_ALREADY_COMMITTED',state.job.job_id,copy(priorByJob));
    const routed=this.router.markDispatchCommitted({idempotencyKey,attempt});
    const committed={schema:'die.factory-asset.generation-commit.v1',commit_id:sha({idempotency_key:idempotencyKey,attempt,route_id:routed.route_id,external_commit_key:externalCommitKey}),job_id:state.job.job_id,idempotency_key:idempotencyKey,attempt,route_id:routed.route_id,provider_id:routed.provider_id,cluster_id:routed.cluster_id,external_commit_key:externalCommitKey,committed_at_ms:this.now(),idempotent_replay:false};
    state.committed=committed;state.lease.state='COMMITTED';this.committedJobIds.set(state.job.job_id,copy(committed));return copy(committed);
  }

  complete({ idempotencyKey }) {
    const state=this.jobs.get(idempotencyKey);if(!state) throw new MultiClusterSchedulerError('E_JOB_NOT_SCHEDULED',idempotencyKey);
    if(!state.committed) throw new MultiClusterSchedulerError('E_COMPLETE_BEFORE_COMMIT',idempotencyKey);
    if(state.complete) return {schema:'die.factory-asset.cross-cluster-completion.v1',job_id:state.job.job_id,idempotency_key:idempotencyKey,released:true,idempotent_replay:true};
    state.complete=true;state.lease.state='RELEASED';this.activeJobIds.delete(state.job.job_id);this._recordSuccess(state.last_decision);
    return {schema:'die.factory-asset.cross-cluster-completion.v1',job_id:state.job.job_id,idempotency_key:idempotencyKey,released:true,idempotent_replay:false,commit_id:state.committed.commit_id};
  }

  reclaimExpiredQueueLeases() {
    const reclaimed=[];
    for(const state of this.jobs.values()) {
      if(state.complete || state.committed || state.lease.state!=='LEASED' || state.lease.expires_at_ms>this.now()) continue;
      state.lease.state='EXPIRED';this.activeJobIds.delete(state.job.job_id);
      reclaimed.push({lease_id:state.lease.lease_id,job_id:state.job.job_id,idempotency_key:state.job.idempotency_key,reason:'TTL_EXPIRED'});
    }
    return {schema:'die.factory-asset.cross-cluster-queue-lease-reclaim.v1',reclaimed};
  }

  circuitSnapshot() {
    const providers={};for(const key of [...this.providerCircuits.keys()].sort()) providers[key]=this._circuitState(this.providerCircuits,key);
    const clusters={};for(const key of [...this.clusterCircuits.keys()].sort()) clusters[key]=this._circuitState(this.clusterCircuits,key);
    return {schema:'die.factory-asset.multi-cluster-circuit-snapshot.v1',provider_cluster:providers,clusters};
  }
  snapshot() {
    const active=[];for(const state of this.jobs.values()) if(!state.complete) active.push({job_id:state.job.job_id,idempotency_key:state.job.idempotency_key,queue_lease:this._publicLease(state.lease),committed:copy(state.committed)});
    return {schema:'die.factory-asset.multi-cluster-scheduler-state.v1',active_queue_leases:active.length,active_jobs:active,committed_job_ids:[...this.committedJobIds.keys()].sort(),cluster_selection_counts:Object.fromEntries([...this.clusterSelections.entries()].sort()),circuits:this.circuitSnapshot(),provider_calls_performed:false,browser_owner_actions:0};
  }
}

export { ClusterRoutingError };