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
    assert '--continuity' in text
    assert '--workdir "$WORKDIR"' in text
    assert '--no-agent' not in text
    assert 'Start at most one new approved Object Atlas seed noun this tick.' in text
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
