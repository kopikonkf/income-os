from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = ROOT / 'company/operations/PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md'
INSTALLER = ROOT / 'company/die-agents/hermes/linux/install-production-cycle-v1.sh'


def test_playbook_defines_result_first_seed_to_publish_chain():
    text = PLAYBOOK.read_text(encoding='utf-8')
    for needle in [
        'Generate per seed noun. Manage and scale per family.',
        'Hermes may start at most ONE new seed production cycle every 3 hours.',
        'Division01 is NOT called for every artifact',
        'Executive is a second-line reviewer, not a per-image gate.',
        'WAITING_FOUNDER_QC',
        'READY_FOR_MANUAL_PUBLISH',
        'PARKED_HUMAN_GATE',
        'Only an **actionable unfinished card** takes precedence over new work.',
        'No silent production failure is allowed.',
        'remains the canonical engineering journey and milestone map',
    ]:
        assert needle in text


def test_playbook_requires_telegram_per_artifact_cycle():
    text = PLAYBOOK.read_text(encoding='utf-8')
    for milestone in [
        'PRODUCTION_STARTED',
        'ARTIFACT_CREATED',
        'QA_QC_UPDATE',
        'WAITING_FOUNDER_QC',
        'READY_FOR_MANUAL_PUBLISH',
    ]:
        assert milestone in text
    assert 'hermes send --to telegram' in text


def test_production_cron_is_three_hour_continuous_agent_job():
    text = INSTALLER.read_text(encoding='utf-8')
    assert "JOB_NAME=\"die-production-cycle-v1\"" in text
    assert "SCHEDULE='0 */3 * * *'" in text
    assert '--deliver telegram' in text
    assert '--no-continuity' in text
    assert '--continuity' not in text
    assert '--script production_tick_preflight.py' in text
    assert 'SELECTOR_SRC=' in text
    assert 'PREFLIGHT_SCRIPT=' in text
    assert '--workdir "$WORKDIR"' in text
    assert '--no-agent' not in text
    assert 'Start at most one new approved Object Atlas seed noun this tick.' in text
    assert 'PARKED_HUMAN_GATE' in text
    assert 'you MUST start one new eligible seed this tick' in text
    assert 'production_seed_selector.py' in text
    assert 'production_active_card_resolver.py' in text
    assert 'do not rediscover card/seed mechanics' in text
    assert 'do not let them block an independent eligible seed' in text
    assert 'PRODUCTION_TICK_NO_PROGRESS' in text
    assert '[SILENT] is forbidden for production ticks' in text
    assert 'Silent failure is forbidden.' in text


def test_all_four_runtime_roles_are_wired_to_one_playbook():
    files = [
        ROOT / 'company/die-agents/hermes/AGENTS.md',
        ROOT / 'company/workers/contract/WORKER_CONTRACT_V0.md',
        ROOT / 'company/division/division001/IDENTITY.md',
        ROOT / 'company/executive/IDENTITY.md',
    ]
    for path in files:
        assert 'PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md' in path.read_text(encoding='utf-8')


def test_runtime_canon_projects_playbook_to_cognitive_principals():
    manifest = json.loads((ROOT / 'company/runtime-canon-context-v1.json').read_text(encoding='utf-8'))
    docs = {x['doc_id']: x for x in manifest['source_documents']}
    assert docs['production_playbook']['classification'] == 'CANON'
    facts = {x['fact_id'] for x in manifest['common_facts']}
    assert {'PRODUCTION-OPS-CADENCE','PRODUCTION-OPS-GRANULARITY','PRODUCTION-OPS-ROLES','PRODUCTION-OPS-TELEGRAM','PRODUCTION-OPS-ATOMIC-GRAPH'} <= facts
    for profile in manifest['principal_profiles'].values():
        assert 'production_playbook' in profile['required_doc_ids']


def test_human_gate_does_not_serialize_independent_seed_production():
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    installer = INSTALLER.read_text(encoding='utf-8')
    for gate in ['WAITING_FOUNDER_QC', 'READY_FOR_MANUAL_PUBLISH']:
        assert gate in playbook
        assert gate in installer
    assert 'MUST NOT block selection of an independent eligible seed' in playbook
    assert 'parked human-gated cards (`WAITING_FOUNDER_QC`, `READY_FOR_MANUAL_PUBLISH`) are excluded from this blocking set' in playbook
    assert 're-reading an unchanged parked human-gated card is **not** material progress' in playbook
    assert 're-reading an unchanged parked human gate is not success' in installer


def test_production_cron_does_not_replay_stale_previous_response():
    installer = INSTALLER.read_text(encoding='utf-8')
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    assert '--no-continuity' in installer
    assert 'CONTINUITY=false' in installer
    assert 'conversational run-to-run continuity is disabled' in playbook
    assert 'Hermes MUST start one new seed in the available cadence slot' in playbook


def test_playbook_uses_deterministic_phase0_seed_selector():
    text = PLAYBOOK.read_text(encoding='utf-8')
    assert 'python3 company/die-agents/hermes/production_seed_selector.py' in text
    assert 'ranks approved `U1-raster` seeds by validated demand' in text
    assert 'MUST consume the injected preflight mode before any ad-hoc repository/database discovery' in text


def test_production_cron_injects_selector_before_agent_reasoning():
    installer = INSTALLER.read_text(encoding='utf-8')
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    assert '--script production_tick_preflight.py' in installer
    assert 'deterministic production tick preflight JSON is injected before this prompt' in installer
    assert 'single agent-mode preflight script' in playbook
    assert 'JSON stdout is injected before Hermes reasoning begins' in playbook


def test_selector_preflight_cannot_revoke_existing_production_authority():
    installer = INSTALLER.read_text(encoding='utf-8')
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    assert 'preflight and its child resolvers have no authority effect' in installer
    assert 'MUST NOT be interpreted as granting or revoking existing authority' in installer
    assert 'neither grant nor revoke existing authority' in playbook
    assert 'Existing zero-spend automated production authority remains governed by this playbook' in playbook


def test_active_card_preflight_is_attached_before_llm_reasoning():
    installer = INSTALLER.read_text(encoding='utf-8')
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    assert '--script production_tick_preflight.py --no-continuity' in installer
    assert 'CONTINUE_ACTIVE_CARD' in installer and 'required_actor' in installer and 'next_action_type' in installer
    assert 'production_active_card_resolver.py' in installer
    assert 'Deterministic active-card orientation' in playbook
    assert 'Unknown explicit production states fail closed' in playbook


def test_unwired_division01_execution_surface_fails_closed_without_discovery():
    installer = INSTALLER.read_text(encoding='utf-8')
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    assert 'execution_ready=false' in installer
    assert 'do not search the repository, load skills, call `execute_code`' in installer
    assert 'E_DIVISION01_AUTONOMOUS_COGNITION_TRANSPORT_UNWIRED' in playbook
    assert 'MUST NOT search for, synthesize or improvise an alternate invocation route' in playbook
