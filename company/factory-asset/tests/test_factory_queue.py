import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('fq',R/'company/factory-asset/lib/factory_queue.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def qjob(q,j='j1',k='k1',intent=None):return q.submit(job_id=j,idempotency_key=k,intent=intent or {'blueprint_id':'B','semantic_asset_id':'S'})
def test_submit_idempotent_and_conflict_safe():
 q=m.FactoryJobQueue();a=qjob(q);b=qjob(q);assert a is b
 with pytest.raises(m.QueueError) as e:q.submit(job_id='j2',idempotency_key='k1',intent={'x':2})
 assert e.value.code=='IDEMPOTENCY_CONFLICT'
def test_duplicate_running_owner_rejected_but_same_owner_idempotent():
 q=m.FactoryJobQueue();qjob(q);a=q.start('j1',owner='w1',lease_token='t1');assert q.start('j1',owner='w1',lease_token='t1') is a
 with pytest.raises(m.QueueError) as e:q.start('j1',owner='w2',lease_token='t2')
 assert e.value.code=='DUPLICATE_OWNERSHIP'
def test_pause_resume_cancel_state_machine():
 q=m.FactoryJobQueue();qjob(q);q.start('j1',owner='w',lease_token='t');assert q.pause('j1').state=='PAUSED';assert q.resume('j1').state=='READY';assert q.cancel('j1').state=='CANCELLED'
def test_retryable_failures_retry_at_most_twice():
 q=m.FactoryJobQueue();qjob(q)
 for expected_retry in (0,1):
  q.start('j1',owner='w',lease_token=f't{expected_retry}');assert q.fail('j1',code='RATE_LIMITED',retryable=True).state=='RETRY_WAIT';assert q.retry('j1').retries==expected_retry+1
 q.start('j1',owner='w',lease_token='t3');assert q.fail('j1',code='RATE_LIMITED',retryable=True).state=='FAILED';assert q.get('j1').retries==2
def test_nonretryable_failure_is_terminal():
 q=m.FactoryJobQueue();qjob(q);q.start('j1',owner='w',lease_token='t');assert q.fail('j1',code='POLICY_BLOCKED',retryable=False).state=='FAILED'
def test_success_requires_exact_hash_and_clears_owner():
 q=m.FactoryJobQueue();qjob(q);q.start('j1',owner='w',lease_token='t')
 with pytest.raises(m.QueueError):q.succeed('j1',artifact_sha256='bad')
 j=q.succeed('j1',artifact_sha256='a'*64);assert j.state=='SUCCEEDED' and j.owner is None
def test_crash_reconciliation_never_creates_success_or_duplicate_owner():
 q=m.FactoryJobQueue();qjob(q);q.start('j1',owner='w',lease_token='t');snap=q.snapshot();restored=m.FactoryJobQueue.from_snapshot(snap);j=restored.get('j1');assert j.state=='READY';assert j.owner is None;assert j.artifact_sha256 is None;assert j.recovery_count==1
def test_false_success_snapshot_rejected():
 q=m.FactoryJobQueue();qjob(q);snap=q.snapshot();snap['jobs'][0]['state']='SUCCEEDED';snap['jobs'][0]['artifact_sha256']=None
 with pytest.raises(m.QueueError) as e:m.FactoryJobQueue.from_snapshot(snap)
 assert e.value.code=='FALSE_SUCCESS_IN_SNAPSHOT'