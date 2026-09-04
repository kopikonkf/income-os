from pathlib import Path
R=Path(__file__).resolve().parents[3]
COG=R/'company/die-agents/hermes/production-cognition/production_cognition_tick.py'
INSTALL=R/'company/die-agents/hermes/linux/install-production-cycle-v1.sh'
def test_cognition_allows_bounded_sealed_context_fallback_without_relaxing_mismatch_guards():
 s=COG.read_text();assert 'SEALED_CONTEXT_FALLBACK' in s;assert 'do not assert any newer canon state' in s;assert 'tool-observed mismatch' in s;assert 'E_CONTEXT_CONVERGENCE' in s
def test_context_convergence_review_uses_new_request_attempt_not_delivered_r00_overwrite():
 s=COG.read_text();assert 'MAX_CONTEXT_RETRIES=3' in s;assert "review_attempt=int(state.get('review_attempt',0))" in s;assert "request_id(task,'BP_REVIEW',revision*10+review_attempt)" in s;assert "'CONTEXT_RETRY_RECOVERED'" in s;assert "'next_review_attempt':review_attempt" in s
def test_production_cron_snapshot_is_stable_repo_shim_not_python_snapshot_entrypoint():
 s=INSTALL.read_text();assert 'exec "$DIE_HOME/company/die-agents/hermes/production-runtime/production_runtime_tick.sh"' in s;assert 'E_RUNTIME_CRON_SHIM' in s

def test_author_context_block_retries_author_not_review_without_artifact():
 src=(R/'company/die-agents/hermes/production-cognition/production_cognition_tick.py').read_text()
 assert "'_BP_AUTHOR_' in rid or '_BP_REVISION_' in rid" in src
 assert "stage=='NEED_REVIEW' and not author_artifact_exists" in src
 assert "'CONTEXT_RECOVERY_STAGE_REPAIRED'" in src
 assert "'next_author_attempt':attempt" in src
 assert "state['stage']=stage" in src

def test_review_context_recovery_remains_separate_from_author_recovery():
 src=(R/'company/die-agents/hermes/production-cognition/production_cognition_tick.py').read_text()
 assert "'_BP_REVIEW_' in rid and stage=='WAITING_FOUNDER'" in src
 assert "state['review_attempt']=n;state['stage']='NEED_REVIEW'" in src
