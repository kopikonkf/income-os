from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]

def load(name:str,rel:str):
    path=ROOT/rel;spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod

profiles=load('fa109_profiles','company/factory-asset/lib/provider_profile.py')
capacity=load('fa109_capacity','company/factory-asset/lib/capacity_ledger.py')
policy=load('fa109_policy','company/factory-asset/lib/policy_gate.py')
router=load('fa109_router','company/factory-asset/lib/provider_router.py')
queue_mod=load('fa109_queue','company/factory-asset/lib/factory_queue.py')
ingestion=load('fa109_ingestion','company/factory-asset/lib/master_ingestion.py')
observability=load('fa109_observability','company/factory-asset/lib/observability.py')


def run_synthetic_acceptance(staging_root:str|Path)->dict[str,Any]:
    root=Path(staging_root).resolve();root.mkdir(parents=True,exist_ok=True)
    registry=json.loads((ROOT/'company/factory-asset/registries/provider-policy.v1.json').read_text(encoding='utf-8'))
    policy_by={x['profile_id']:x for x in registry['profiles']}

    ledger=capacity.CapacityLedger()
    ledger.record({'profile_id':'qwen_a','provider_id':'qwen','event':'SUCCESS','observed_at':'2026-09-04T04:00:00Z','evidence_ref':'synthetic://fa109/qwen-success'})
    ledger.record({'profile_id':'chatgpt_a','provider_id':'chatgpt','event':'RATE_LIMITED','observed_at':'2026-09-04T04:00:00Z','evidence_ref':'synthetic://fa109/chatgpt-rate','retry_after_seconds':60})
    qcap=ledger.snapshot('qwen_a',now='2026-09-04T04:05:00Z');ccap=ledger.snapshot('chatgpt_a',now='2026-09-04T04:05:00Z')
    qpol=policy.evaluate_policy(policy_by['qwen_a'],today='2026-09-04');cpol=policy.evaluate_policy(policy_by['chatgpt_a'],today='2026-09-04')
    decision=router.route_provider(asset_type='PHOTO',candidates=[
      {'profile_id':'qwen_a','provider_id':'qwen','enabled':True,'policy_allowed':qpol['allowed'],'capacity_state':qcap.state,'asset_types':['PHOTO'],'quality_score':0.95,'unit_cost_micros':0,'priority':10},
      {'profile_id':'chatgpt_a','provider_id':'chatgpt','enabled':True,'policy_allowed':cpol['allowed'],'capacity_state':ccap.state,'asset_types':['PHOTO'],'quality_score':0.94,'unit_cost_micros':0,'priority':20},
    ])
    if decision.profile_id!='qwen_a': raise RuntimeError('ROUTER_EXPECTATION_FAILED')

    leases=profiles.ProviderLeaseRegistry();lease=leases.acquire(token='fa109-lease-token',principal_id='synthetic_principal',profile_id=decision.profile_id,owner='FA109-JOB-001')

    q=queue_mod.FactoryJobQueue();job=q.submit(job_id='FA109-JOB-001',idempotency_key='a'*64,intent={'blueprint_id':'FABP-FA109-SYNTH','semantic_asset_id':'FASA-FA109-SYNTH','provider_id':decision.provider_id,'label':'FA109 synthetic'})
    q.start(job.job_id,owner='factory-core-synthetic',lease_token='job-lease-1')
    q.fail(job.job_id,code='RATE_LIMITED',retryable=True)
    retry_state=q.get(job.job_id).state
    q.retry(job.job_id);q.start(job.job_id,owner='factory-core-synthetic',lease_token='job-lease-2')

    master=root/'synthetic-master.bin';master.write_bytes(b'factory-core-synthetic-master-v1')
    master_sha=ingestion.sha256_file(master)
    false_success_blocked=False
    try:q.succeed(job.job_id,artifact_sha256='bad')
    except queue_mod.QueueError:false_success_blocked=True
    if not false_success_blocked:raise RuntimeError('FALSE_SUCCESS_NOT_BLOCKED')
    q.succeed(job.job_id,artifact_sha256=master_sha)

    crash=q.submit(job_id='FA109-JOB-CRASH',idempotency_key='b'*64,intent={'blueprint_id':'FABP-FA109-CRASH','semantic_asset_id':'FASA-FA109-CRASH','provider_id':'qwen','label':'crash probe'})
    q.start(crash.job_id,owner='factory-core-synthetic',lease_token='crash-lease')
    restored=queue_mod.FactoryJobQueue.from_snapshot(q.snapshot());recovered=restored.get(crash.job_id)

    stage=root/'ingestion'
    r1=ingestion.stage_master(source_path=master,staging_root=stage,attempt_id='fa109-attempt-1',semantic_asset_id='FASA-FA109-SYNTH',blueprint_id='FABP-FA109-SYNTH',expected_sha256=master_sha)
    duplicate=root/'synthetic-master-copy.bin';duplicate.write_bytes(master.read_bytes())
    r2=ingestion.stage_master(source_path=duplicate,staging_root=stage,attempt_id='fa109-attempt-2',semantic_asset_id='FASA-FA109-SYNTH',blueprint_id='FABP-FA109-SYNTH',expected_sha256=master_sha)
    idx=ingestion.staged_index(stage)

    metrics=observability.MetricsLedger();metrics.record({'kind':'ATTEMPT','job_id':'FA109-JOB-001'});metrics.record({'kind':'FAILURE','job_id':'FA109-JOB-001','failure_code':'RATE_LIMITED','retryable':True});metrics.record({'kind':'ATTEMPT','job_id':'FA109-JOB-001'});metrics.record({'kind':'MASTER','artifact_sha256':master_sha});metrics.record({'kind':'RESOURCE','cpu_seconds':1.25,'memory_mb_seconds':64.0});metrics.record({'kind':'ECONOMICS','unit_cost_micros':0})
    secret_blocked=False
    try:observability.sanitize_event({'kind':'ATTEMPT','job_id':'x','session_token':'forbidden'})
    except observability.ObservabilityError:secret_blocked=True
    if not secret_blocked:raise RuntimeError('SECRET_OBSERVABILITY_NOT_BLOCKED')

    leases.release(token='fa109-lease-token',profile_id=decision.profile_id)
    out={
      'schema':'die.factory-asset.factory-core-synthetic-acceptance.v1','result':'PASS','provider_calls_performed':False,
      'routing':{'selected_profile_id':decision.profile_id,'selected_provider_id':decision.provider_id,'qwen_capacity':qcap.state,'chatgpt_capacity':ccap.state,'rejected':decision.rejected},
      'lease':{'profile_id':lease.profile_id,'released':leases.active(lease.profile_id) is None},
      'queue':{'retry_state':retry_state,'final_state':q.get(job.job_id).state,'retries':q.get(job.job_id).retries,'attempts':q.get(job.job_id).attempts,'artifact_sha256':q.get(job.job_id).artifact_sha256,'false_success_blocked':false_success_blocked},
      'crash_recovery':{'state_after_restore':recovered.state,'recovery_count':recovered.recovery_count,'owner_after_restore':recovered.owner},
      'ingestion':{'attempt_count':idx['attempt_count'],'unique_blob_count':idx['unique_blob_count'],'duplicate_blob_reused':r2['blob_reused'],'same_blob_path':r1['staged_blob_path']==r2['staged_blob_path'],'canonical_truth':r1['canonical_truth'],'state_manager_commit_required':r1['state_manager_commit_required']},
      'observability':metrics.snapshot(),
      'secret_observability_blocked':secret_blocked,
      'zero_false_success':false_success_blocked and recovered.state=='READY' and r1['canonical_truth'] is False,
    }
    return out