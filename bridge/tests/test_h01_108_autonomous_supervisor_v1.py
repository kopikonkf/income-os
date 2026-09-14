from pathlib import Path
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'

def test_supervisor_is_generation_only():
 s=(H/'h01_108_autonomous_supervisor.py').read_text().lower()
 assert 'postprocess' not in s
 assert 'rights' not in s
 assert 'generation-complete.receipt.json' in s
 assert 'h01-103-validation.json' in s

def test_supervisor_gates_dispatch_by_scheduler_readiness():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "ready=set(ready_order)" in s
 assert 'provider in ready' in s

def test_supervisor_has_durable_completion_and_bounded_attempts():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "'generated_count':len(done)" in s
 assert "'remaining_count':len(remaining)" in s
 assert "'COMPLETE_PASS'" in s
 assert 'max-attempts-per-item' in s
 assert 'BLOCKED_MAX_ATTEMPTS' in s
 assert "'postproduction_dependency':'NONE'" in s

def test_supervisor_never_authorizes_submission_or_publication():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "'submission_authorized':False" in s
 assert "'publication_authorized':False" in s

def test_supervisor_never_auto_resubmits_after_committed_dispatch():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def committed_pending' in s
 assert 'provider-dispatch.receipt.json' in s
 assert 'committed_pending(root,item,planned)' in s
 assert "'duplicate_retry_policy':'NO_AUTO_RESUBMIT_AFTER_COMMIT'" in s

def test_supervisor_recovers_local_output_through_technical_finalize():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def recover_local_output' in s
 assert "obs.get('status')!='SUCCEEDED'" in s
 assert 'h01_108_capture.py' in s
 assert 'h01_108_technical_finalize.py' in s
 assert "provider_generation_dispatched':False" in s

def test_attempt_budget_counts_committed_dispatches_not_workspace_dirs():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert 'def committed_attempt_count' in s
 assert "attempt_budget_policy':'COMMITTED_PROVIDER_DISPATCHES_ONLY'" in s
 assert 'next_attempt_id(root,item,provider)' in s

def test_workspace_is_created_only_after_scheduler_lease():
 s=(H/'h01_108_run_one.py').read_text()
 assert s.index("lease=jrun([SCHED,'acquire'") < s.index("w.mkdir(parents=True,exist_ok=False)")

def test_generation_acceptance_requires_generation_receipt_and_h01_103_pass():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 start=s.index('def semantic_master_valid(');end=s.index('def generated',start);block=s[start:end]
 assert 'generation-complete.receipt.json' in block
 assert 'final/h01-103-validation.json' in block
 assert "g.get('status')=='GENERATION_COMPLETE'" in block
 assert "v.get('status')=='PASS'" in block
 assert "generation_acceptance_boundary':'H01_103_PASS_SEMANTIC_MASTER'" in s

def test_wrong_modality_is_generation_taxonomy_with_one_bounded_redistribution():
 s=(H/'h01_108_autonomous_supervisor.py').read_text()
 assert "TERMINAL_OUTPUT_MISMATCH={'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER'}" in s
 assert 'do_not_acquire_other_turn_svg' in s
 assert 'max-provider-redistributions-per-item' in s
 assert 'ADAPTIVE_REDISTRIBUTION_AFTER_TERMINAL_MODALITY_MISMATCH' in s

def test_qwen_committed_pending_uses_read_only_recovery_before_resubmit():
 s=(H/'h01_108_autonomous_supervisor.py').read_text();r=(H/'h01_108_recover_committed.py').read_text()
 assert "h01_108_recover_committed.py" in s
 assert "provider_generation_dispatched':False" in r
 assert '--recheck-url' in r
 assert 'h01_108_technical_finalize.py' in r
