from pathlib import Path
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'
def test_supervisor_is_generation_only():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'postprocess' not in s.lower()
 assert 'rights' not in s.lower()
 assert "artifact-created.receipt.json" in s
def test_supervisor_gates_dispatch_by_scheduler_readiness():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "ready=set(sched.get('ready_provider_ids',[]))" in s
 assert 'provider in ready' in s
def test_supervisor_has_durable_100_completion_and_bounded_attempts():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "'generated_count':len(done)" in s
 assert "'remaining_count':len(remaining)" in s
 assert "'COMPLETE_PASS'" in s
 assert 'max-attempts-per-item' in s
 assert 'BLOCKED_MAX_ATTEMPTS' in s
def test_supervisor_never_authorizes_submission_or_publication():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "'submission_authorized':False" in s
 assert "'publication_authorized':False" in s

def test_supervisor_never_auto_resubmits_after_committed_dispatch():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def committed_pending' in s
 assert 'provider-dispatch.receipt.json' in s
 assert 'if committed_pending(root,item,provider):continue' in s
 assert "'duplicate_retry_policy':'NO_AUTO_RESUBMIT_AFTER_COMMIT'" in s

def test_supervisor_recovers_local_provider_output_before_new_dispatch():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def recover_local_output' in s
 assert "obs.get('status')!='SUCCEEDED'" in s
 assert "h01_108_capture.py" in s
 assert "provider_generation_dispatched':False" in s

def test_attempt_budget_counts_committed_dispatches_not_workspace_dirs():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def committed_attempt_count' in s
 assert "attempt_budget_policy':'COMMITTED_PROVIDER_DISPATCHES_ONLY'" in s
 assert 'next_attempt_id(root,item,provider)' in s

def test_workspace_is_created_only_after_scheduler_lease():
 s=(H/'h01_108_run_one.py').read_text()
 assert s.index("lease=jrun([SCHED,'acquire'") < s.index("w.mkdir(parents=True,exist_ok=False)")

def test_generation_acceptance_requires_artifact_created_only():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 start=s.index('def generated('); end=s.index('def next_attempt_id',start)
 block=s[start:end]
 assert "artifact-created.receipt.json" in block
 assert "browser-job-result.json" not in block
 assert "generation_acceptance_boundary':'ARTIFACT_CREATED_ONLY'" in s

def test_legacy_provider_success_is_recovery_pending_not_resubmitted():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 start=s.index('def committed_pending('); end=s.index('def atomic_json',start)
 block=s[start:end]
 assert "o.get('status')=='SUCCEEDED'" in block
 assert "legacy_commit_evidence" in block
