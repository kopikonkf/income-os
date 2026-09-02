from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
PLAYBOOK=ROOT/'company/operations/PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md'
INSTALLER=ROOT/'company/die-agents/hermes/linux/install-production-cycle-v1.sh'
RUNTIME=ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py'

def test_playbook_defines_result_first_chain_and_parked_founder_gate():
 t=PLAYBOOK.read_text()
 for n in ['Generate per seed noun. Manage and scale per family.','Hermes may start at most ONE new seed production cycle every 3 hours.','Division01 is NOT called for every artifact','Executive is a second-line reviewer, not a per-image gate.','WAITING_FOUNDER_QC','PARKED_HUMAN_GATE','Only an **actionable unfinished card** takes precedence over new work.','remains the canonical engineering journey and milestone map']:
  assert n in t
 assert 'bounded upscale/recovery -> WAITING_FOUNDER_QC (parked)' in t

def test_playbook_keeps_telegram_milestones_and_qc_optional_downstream():
 t=PLAYBOOK.read_text()
 for n in ['PRODUCTION_STARTED','ARTIFACT_CREATED','WAITING_FOUNDER_QC','hermes send --to telegram']:assert n in t
 assert 'not production-throughput blockers' in t

def test_production_cron_is_three_hour_deterministic_no_agent_job():
 t=INSTALLER.read_text()
 assert 'JOB_NAME="die-production-cycle-v1"' in t
 assert "SCHEDULE='0 */3 * * *'" in t
 assert '--deliver telegram' in t and '--no-continuity' in t and '--no-agent' in t
 assert "SCRIPT_REL='production-runtime/production_runtime_tick.sh'" in t
 assert '--provider' not in t and 'gemini-3.7-flash' not in t
 assert 'die-muxia-dispatch.service' in t and 'NOPASSWD' not in t and 'visudo -cf' not in t

def test_human_gate_does_not_serialize_independent_seed_production():
 p=PLAYBOOK.read_text();r=RUNTIME.read_text()
 assert 'MUST NOT block selection of an independent eligible seed' in p
 assert 'parked human-gated cards (`WAITING_FOUNDER_QC`, `READY_FOR_MANUAL_PUBLISH`) are excluded from this blocking set' in p
 assert "'State: WAITING_FOUNDER_QC'" in r
 assert 'select_seed(DB,WORKSPACES)' in r

def test_runtime_has_no_conversational_continuity_or_llm_provider_dependency():
 i=INSTALLER.read_text();r=RUNTIME.read_text();p=PLAYBOOK.read_text()
 assert '--no-continuity' in i and '--no-agent' in i
 assert 'conversational run-to-run continuity is disabled' in p
 assert 'gemini' not in r.lower() and 'nvidia' not in r.lower()

def test_division01_cognition_remains_separate_async_execution_surface():
 resolver=(ROOT/'company/die-agents/hermes/production_active_card_resolver.py').read_text();p=PLAYBOOK.read_text()
 assert 'PRODUCTION_COGNITION_LINE_V1' in resolver
 assert 'ASYNC_DELEGATED' in resolver
 assert 'PRODUCTION_COGNITION_LINE_V1' in p

def test_all_four_runtime_roles_are_wired_to_one_playbook():
 for path in [ROOT/'company/die-agents/hermes/AGENTS.md',ROOT/'company/workers/contract/WORKER_CONTRACT_V0.md',ROOT/'company/division/division001/IDENTITY.md',ROOT/'company/executive/IDENTITY.md']:
  assert 'PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md' in path.read_text()

def test_runtime_canon_projects_playbook_to_cognitive_principals():
 m=json.loads((ROOT/'company/runtime-canon-context-v1.json').read_text());docs={x['doc_id']:x for x in m['source_documents']}
 assert docs['production_playbook']['classification']=='CANON'
 for profile in m['principal_profiles'].values():assert 'production_playbook' in profile['required_doc_ids']
