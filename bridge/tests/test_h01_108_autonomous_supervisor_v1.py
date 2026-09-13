from pathlib import Path
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'
def test_supervisor_is_generation_only():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'postprocess' not in s.lower()
 assert 'rights' not in s.lower()
 assert "artifact-created.receipt.json" in s
 assert "browser-job-result.json" in s
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
