#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MultiClusterScheduler, MultiClusterSchedulerError, ClusterRoutingError } from '../../browser/linux/multi_cluster_scheduler.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,'../../..');
const OUT=path.join(ROOT,'company/factory-asset/fixtures/multi-cluster/FA-306-multi-cluster-scheduler-result.json');
const NOW0=Date.parse('2026-09-06T18:30:00Z');
let IDSEQ=0;const RID=()=>`lease-${String(++IDSEQ).padStart(4,'0')}`;
const OBS='2026-09-06T18:29:30Z';

function snapshot(cluster, active=0, leases=[], states={}){return {cluster_id:cluster,observed_at:OBS,snapshot:{schema:'die.muxia.cluster-tab-lease-snapshot.v1',max_tabs:8,active_leases:active,open_pages:active,provider_states:states,leases}};}
function candidate(provider,cluster,overrides={}){
 const base={provider_id:provider,cluster_id:cluster,transport:'BROWSER_CDP',enabled:true,policy_allowed:true,asset_types:['PHOTO','ISOLATED_OBJECT'],readiness:{provider_id:provider,state:'HEALTHY',observed_at:OBS},capacity:{provider_id:provider,cluster_id:cluster,state:'AVAILABLE',observed_at:OBS},queue:{depth:0,limit:64,observed_at:OBS},tab_capacity:snapshot(cluster),provider_tab_limit:1,cluster_browser_generation_limit:4,recent_failures:0,latency_ms:500,priority:100};
 const c={...base,...overrides};
 if(overrides.readiness)c.readiness={...base.readiness,...overrides.readiness};
 if(overrides.capacity)c.capacity={...base.capacity,...overrides.capacity};
 if(overrides.queue)c.queue={...base.queue,...overrides.queue};
 if(overrides.tab_capacity)c.tab_capacity={...base.tab_capacity,...overrides.tab_capacity};
 return c;
}
function q(depth=0){return {depth,limit:64,observed_at:OBS};}
function job(id,key=`idem-${id}`){return {job_id:id,idempotency_key:key,asset_type:'PHOTO',intent:{semantic_asset_id:`asset-${id}`}};}
function expectCode(fn,code){try{fn();}catch(e){if((e instanceof MultiClusterSchedulerError||e instanceof ClusterRoutingError)&&e.code===code)return {code,details:e.details||null};throw e;}throw new Error(`EXPECTED_${code}`);}
function commitComplete(s,j,d,key=`commit-${j.job_id}`){const c=s.markDispatchCommitted({idempotencyKey:j.idempotency_key,attempt:d.attempt,externalCommitKey:key});const done=s.complete({idempotencyKey:j.idempotency_key});return {commit:c,complete:done};}

const results={};

// 1. Fairness alternates otherwise-equivalent healthy clusters.
{
 const s=new MultiClusterScheduler({now:()=>NOW0,randomId:RID,config:{provider_cluster_failure_threshold:99,cluster_failure_threshold:99}});
 const picks=[];
 for(let i=1;i<=4;i++){
  const j=job(`fair-${i}`);const d=s.schedule({job:j,candidates:[candidate('gemini','cluster-a'),candidate('gemini','cluster-b')],queue:q()});picks.push(d.cluster_id);commitComplete(s,j,d);
 }
 if(JSON.stringify(picks)!==JSON.stringify(['cluster-a','cluster-b','cluster-a','cluster-b']))throw new Error(`E_FAIRNESS:${picks}`);
 results.fairness={picks,snapshot:s.snapshot()};
}

// 2. Same job/idempotency replays same cross-cluster queue lease; competing key is rejected.
{
 const s=new MultiClusterScheduler({now:()=>NOW0,randomId:RID});const j=job('lease-one');const c=[candidate('gemini','cluster-a'),candidate('gemini','cluster-b')];
 const first=s.schedule({job:j,candidates:c,queue:q()});const replay=s.schedule({job:j,candidates:c,queue:q()});
 if(first.queue_lease.lease_id!==replay.queue_lease.lease_id||first.route_id!==replay.route_id||replay.scheduler_idempotent_replay!==true)throw new Error('E_LEASE_REPLAY');
 const conflict=expectCode(()=>s.schedule({job:job('lease-one','idem-other'),candidates:c,queue:q()}),'E_JOB_QUEUE_LEASE_CONFLICT');
 results.queue_lease_isolation={first,replay,conflict,snapshot:s.snapshot()};
}

// 3. Provider@cluster breaker opens after bounded pre-dispatch failure and reroutes to sibling cluster.
{
 const s=new MultiClusterScheduler({now:()=>NOW0,randomId:RID,config:{provider_cluster_failure_threshold:1,cluster_failure_threshold:99}});const j=job('provider-circuit');const c=[candidate('gemini','cluster-a'),candidate('gemini','cluster-b')];
 const first=s.schedule({job:j,candidates:c,queue:q()});if(first.cluster_id!=='cluster-a')throw new Error('E_PROVIDER_CIRCUIT_FIRST');
 const second=s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'pc-1',failureCode:'PROVIDER_TIMEOUT',candidates:c,queue:q()});if(second.cluster_id!=='cluster-b')throw new Error('E_PROVIDER_CIRCUIT_REROUTE');
 const replay=s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'pc-1',failureCode:'PROVIDER_TIMEOUT',candidates:c,queue:q()});if(replay.route_id!==second.route_id||replay.scheduler_idempotent_replay!==true)throw new Error('E_PROVIDER_CIRCUIT_EVENT_REPLAY');
 if(s.circuitSnapshot().provider_cluster['gemini@cluster-a']?.state!=='OPEN')throw new Error('E_PROVIDER_CIRCUIT_NOT_OPEN');
 results.provider_cluster_circuit={first,second,replay,circuits:s.circuitSnapshot()};
}

// 4. Whole-cluster breaker aggregates failures across jobs/providers; cooldown recovers it.
{
 let now=NOW0;const s=new MultiClusterScheduler({now:()=>now,randomId:RID,config:{provider_cluster_failure_threshold:99,cluster_failure_threshold:2,cluster_cooldown_ms:5000}});
 const pair=(provider)=>[candidate(provider,'cluster-a'),candidate(provider,'cluster-b')];
 const j1=job('cluster-fail-1');const d1=s.schedule({job:j1,candidates:pair('gemini'),queue:q()});const r1=s.reportPreDispatchFailure({idempotencyKey:j1.idempotency_key,eventId:'cf-1',failureCode:'PROVIDER_TIMEOUT',candidates:pair('gemini'),queue:q()});commitComplete(s,j1,r1);
 const j2=job('cluster-fail-2');const d2=s.schedule({job:j2,candidates:pair('manus'),queue:q()});if(d2.cluster_id!=='cluster-a')throw new Error(`E_CLUSTER_CIRCUIT_SECOND_START:${d2.cluster_id}`);const r2=s.reportPreDispatchFailure({idempotencyKey:j2.idempotency_key,eventId:'cf-2',failureCode:'PROVIDER_ERROR',candidates:pair('manus'),queue:q()});if(r2.cluster_id!=='cluster-b')throw new Error('E_CLUSTER_CIRCUIT_SECOND_REROUTE');commitComplete(s,j2,r2);
 if(s.circuitSnapshot().clusters['cluster-a']?.state!=='OPEN')throw new Error('E_CLUSTER_CIRCUIT_NOT_OPEN');
 const j3=job('cluster-open-routes-away');const d3=s.schedule({job:j3,candidates:pair('duckai'),queue:q()});if(d3.cluster_id!=='cluster-b')throw new Error('E_CLUSTER_CIRCUIT_NOT_ISOLATED');commitComplete(s,j3,d3);
 now+=6000;const after=s.circuitSnapshot();if(after.clusters['cluster-a']?.state!=='CLOSED')throw new Error('E_CLUSTER_CIRCUIT_NOT_RECOVERED');
 const j4=job('cluster-recovered');const d4=s.schedule({job:j4,candidates:pair('qwen'),queue:q()});if(d4.cluster_id!=='cluster-a')throw new Error(`E_CLUSTER_RECOVERY_NOT_ELIGIBLE:${d4.cluster_id}`);commitComplete(s,j4,d4);
 results.cluster_circuit={d1,r1,d2,r2,d3,after,d4,final:s.snapshot()};
}

// 5. Retry budget is bounded to two retries.
{
 const s=new MultiClusterScheduler({now:()=>NOW0,randomId:RID,config:{provider_cluster_failure_threshold:99,cluster_failure_threshold:99,max_retries:2}});const j=job('retry-budget');const c=[candidate('gemini','cluster-a'),candidate('gemini','cluster-b'),candidate('manus','cluster-a',{latency_ms:700})];
 const a1=s.schedule({job:j,candidates:c,queue:q()});const a2=s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'rb-1',failureCode:'PROVIDER_TIMEOUT',candidates:c,queue:q()});const a3=s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'rb-2',failureCode:'PROVIDER_ERROR',candidates:c,queue:q()});
 const limit=expectCode(()=>s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'rb-3',failureCode:'PROVIDER_ERROR',candidates:c,queue:q()}),'E_RETRY_LIMIT');
 results.retry_budget={attempts:[a1,a2,a3].map(x=>({attempt:x.attempt,provider_id:x.provider_id,cluster_id:x.cluster_id})),limit,snapshot:s.snapshot()};
}

// 6. Commit is exactly once across routes and even across a new idempotency key for same job_id.
{
 const s=new MultiClusterScheduler({now:()=>NOW0,randomId:RID});const j=job('commit-once');const c=[candidate('gemini','cluster-a'),candidate('gemini','cluster-b')];const d=s.schedule({job:j,candidates:c,queue:q()});
 const commit=s.markDispatchCommitted({idempotencyKey:j.idempotency_key,attempt:d.attempt,externalCommitKey:'external-commit-1'});const replay=s.markDispatchCommitted({idempotencyKey:j.idempotency_key,attempt:d.attempt,externalCommitKey:'external-commit-1'});
 if(replay.commit_id!==commit.commit_id||replay.idempotent_replay!==true)throw new Error('E_COMMIT_REPLAY');
 const duplicate=expectCode(()=>s.markDispatchCommitted({idempotencyKey:j.idempotency_key,attempt:d.attempt,externalCommitKey:'external-commit-2'}),'E_DUPLICATE_GENERATION_COMMIT');
 const retryAfter=expectCode(()=>s.reportPreDispatchFailure({idempotencyKey:j.idempotency_key,eventId:'after-commit',failureCode:'PROVIDER_TIMEOUT',candidates:c,queue:q()}),'E_RETRY_AFTER_DISPATCH_COMMIT');
 const complete=s.complete({idempotencyKey:j.idempotency_key});const jobDuplicate=expectCode(()=>s.schedule({job:job('commit-once','new-idem-same-job'),candidates:c,queue:q()}),'E_JOB_ALREADY_COMMITTED');
 results.exactly_once_commit={decision:d,commit,replay,duplicate,retryAfter,complete,jobDuplicate,snapshot:s.snapshot()};
}

// 7. Expired uncommitted queue lease requires explicit reclaim and does not become a committed duplicate.
{
 let now=NOW0;const s=new MultiClusterScheduler({now:()=>now,randomId:RID,config:{queue_lease_ttl_ms:2000}});const j=job('lease-expiry');const c=[candidate('gemini','cluster-a')];const d=s.schedule({job:j,candidates:c,queue:q()});now+=2500;const expired=expectCode(()=>s.schedule({job:j,candidates:c,queue:q()}),'E_QUEUE_LEASE_EXPIRED');const reclaimed=s.reclaimExpiredQueueLeases();if(reclaimed.reclaimed.length!==1)throw new Error('E_QUEUE_LEASE_RECLAIM');results.lease_expiry={decision:d,expired,reclaimed,snapshot:s.snapshot()};
}

const assertions={
 fairness_balanced:JSON.stringify(results.fairness.picks)===JSON.stringify(['cluster-a','cluster-b','cluster-a','cluster-b']),
 cross_cluster_queue_lease_isolated:results.queue_lease_isolation.conflict.code==='E_JOB_QUEUE_LEASE_CONFLICT',
 provider_cluster_circuit_opened:results.provider_cluster_circuit.circuits.provider_cluster['gemini@cluster-a'].state==='OPEN',
 cluster_circuit_opened_and_recovered:results.cluster_circuit.after.clusters['cluster-a'].state==='CLOSED',
 retries_bounded:results.retry_budget.limit.code==='E_RETRY_LIMIT',
 duplicate_commit_blocked:results.exactly_once_commit.duplicate.code==='E_DUPLICATE_GENERATION_COMMIT'&&results.exactly_once_commit.jobDuplicate.code==='E_JOB_ALREADY_COMMITTED',
 post_dispatch_retry_blocked:results.exactly_once_commit.retryAfter.code==='E_RETRY_AFTER_DISPATCH_COMMIT',
 expired_lease_reclaim_explicit:results.lease_expiry.reclaimed.reclaimed.length===1,
};
if(!Object.values(assertions).every(Boolean))throw new Error('E_FA306_ASSERTIONS');
const out={schema:'die.factory-asset.fa306-multi-cluster-scheduler-acceptance.v1',task_id:'FA-306',result:'PASS',assertions,evidence:results,provider_calls_performed:false,browser_processes_spawned:0,live_broker_leases_acquired:0,secret_values_read:false,spend_usd:0,submission_authorized:false,publication_authorized:false};
fs.mkdirSync(path.dirname(OUT),{recursive:true});fs.writeFileSync(OUT,JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));