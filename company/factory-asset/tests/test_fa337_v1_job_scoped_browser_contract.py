import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CONTRACT=ROOT/'company/factory-asset/contracts/fa337-v1-job-scoped-browser-lifecycle.v1.json'
DOC=ROOT/'company/factory-asset/docs/V1_JOB_SCOPED_BROWSER_LIFECYCLE_V1.md'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'

def load(): return json.loads(CONTRACT.read_text(encoding='utf-8'))

def test_contract_keeps_v1_v2_engines_separate():
    c=load(); assert c['task_id']=='FA-337'; assert c['scope']['engine_merge'] is False
    assert c['scope']['implementation_task']=='FA-338'
    assert c['hard_invariants']['v2_identity_separation'].startswith('FA-337 does not reuse')

def test_idle_means_zero_browser_owners_not_zero_control_daemons():
    c=load(); idle=c['idle_acceptance']['queue_empty_expected']
    assert idle['active_job_leases']==0 and idle['governed_browser_roots']==0 and idle['governed_cdp_listeners']==0 and idle['active_browser_contexts']==0
    assert c['idle_acceptance']['persistent_disk_profiles_may_exist'] is True
    assert c['idle_acceptance']['control_daemons_may_exist'] is True

def test_terminal_or_reconciliation_precedes_close_and_exactly_once_survives():
    c=load(); states={x['state']:x for x in c['state_machine']}
    assert states['DURABLE_TERMINAL']['durable_receipt_required'] is True
    assert states['COMMITTED_UNRESOLVED']['automatic_redispatch_forbidden'] is True
    assert states['CLOSING']['browser_close_required'] is True
    assert 'never be automatically repeated' in c['hard_invariants']['exactly_once_preserved']

def test_protection_repair_is_same_profile_no_cdp_exclusive_founder_path():
    c=load(); r=c['protection_challenge_policy']; fr={x['state']:x for x in c['state_machine']}['FOUNDER_REPAIR']
    assert 'same persistent profile' in r['founder_repair']
    assert fr['cdp_listener'] is False and fr['exclusive_profile_repair_lease'] is True and fr['founder_interactive'] is True
    assert 'never automated bypass' in r['founder_repair']

def test_graph_closes_337_and_opens_only_implementation_frontier():
    g=json.loads(GRAPH.read_text(encoding='utf-8')); by={t['id']:t for t in g['tasks']}
    assert by['FA-337']['status']=='DONE'; assert by['FA-338']['status']=='READY'
    assert by['FA-339']['status']=='BLOCKED' and by['FA-340']['status']=='BLOCKED'
    assert by['FA-338']['depends_on']==['FA-337']

def test_document_names_required_lifecycle_and_current_owner_migration():
    s=DOC.read_text(encoding='utf-8')
    for token in ['COLD','SPAWN_HEADFUL','DURABLE_TERMINAL','Browser.close','COMMITTED_UNRESOLVED','no CDP','external_chrome_owner.sh','FA-338']:
        assert token in s
