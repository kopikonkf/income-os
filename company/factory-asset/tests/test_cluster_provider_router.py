from pathlib import Path
import json
import subprocess

R = Path(__file__).resolve().parents[3]
CORE = R / 'company/browser/linux/cluster_provider_router.mjs'
RUNNER = R / 'company/factory-asset/bin/run_fa304_cluster_router_synthetic.mjs'
CLUSTERS = R / 'company/factory-asset/registries/web-ai-clusters.v1.json'


def run_acceptance():
    r = subprocess.run(['node', str(RUNNER)], capture_output=True, text=True, check=True, timeout=60)
    return json.loads(r.stdout)


def test_fa304_synthetic_acceptance_passes_without_provider_calls():
    v = run_acceptance()
    assert v['task_id'] == 'FA-304'
    assert v['result'] == 'PASS'
    assert v['provider_calls_performed'] is False
    assert v['browser_processes_spawned'] == 0
    assert v['cluster_a_profile_mutated'] is False
    assert all(v['assertions'].values())


def test_qwen_session_api_is_canonical_primary_and_does_not_consume_tab_capacity():
    reg = json.loads(CLUSTERS.read_text())
    cluster = reg['clusters'][0]
    qwen = next(x for x in cluster['providers'] if x['provider_id'] == 'qwen')
    assert qwen['preferred_transport'] == 'SESSION_API'
    assert qwen['browser_fallback'] == 'BROWSER_CDP'
    v = run_acceptance()
    d = v['evidence']['qwen_session_preferred']
    assert d['provider_id'] == 'qwen'
    assert d['transport'] == 'SESSION_API'
    assert d['requires_tab_lease'] is False
    assert d['tab_capacity_consumed_by_router'] is False
    assert d['browser_owner_action'] == 'NONE'


def test_browser_routes_consume_fa302_snapshot_as_capacity_without_owning_browser():
    v = run_acceptance()
    d = v['evidence']['active_tab_load_cluster_choice']
    assert d['transport'] == 'BROWSER_CDP'
    assert d['requires_tab_lease'] is True
    assert d['tab_capacity_consumed_by_router'] is False
    assert d['browser_owner_action'] == 'NONE'
    assert d['factors']['active_tab_load'] == 0
    assert d['cluster_id'] == 'synthetic-cluster-b'


def test_checkpoint_stale_unknown_and_queue_pressure_fail_closed_per_route():
    v = run_acceptance()
    isolated = v['evidence']['provider_failure_isolation']
    assert isolated['provider_id'] == 'gemini'
    chatgpt = next(x for x in isolated['rejected'] if x['provider_id'] == 'chatgpt')
    assert 'READINESS_CHECKPOINT' in chatgpt['reasons']

    stale = v['evidence']['stale_readiness_capacity_failclosed']
    qwen = next(x for x in stale['rejected'] if x['provider_id'] == 'qwen')
    assert 'READINESS_STALE' in qwen['reasons']
    assert 'CAPACITY_STALE' in qwen['reasons']

    full = v['evidence']['queue_backpressure_failclosed']
    reasons = [reason for x in full['details']['rejected'] for reason in x['reasons']]
    assert 'QUEUE_BACKPRESSURE' in reasons


def test_fa117_capacity_keying_and_open_page_overbudget_edges_fail_closed():
    v = run_acceptance()['evidence']
    edge = v['fa117_open_pages_edge_failclosed']
    assert edge['provider_id'] == 'manus'
    rejected = next(x for x in edge['rejected'] if x['provider_id'] == 'gemini')
    assert 'CLUSTER_OPEN_PAGES_OVER_BUDGET' in rejected['reasons']
    keyed = v['provider_cluster_capacity_keying']
    qwen = next(x for x in keyed['rejected'] if x['provider_id'] == 'qwen')
    gemini = next(x for x in keyed['rejected'] if x['provider_id'] == 'gemini')
    assert 'CAPACITY_PROVIDER_KEY_MISMATCH' in qwen['reasons']
    assert 'CAPACITY_CLUSTER_KEY_MISMATCH' in gemini['reasons']


def test_retry_contract_is_bounded_idempotent_and_commit_safe():
    v = run_acceptance()['evidence']['retry_idempotency']
    assert v['first']['attempt'] == 1 and v['first']['provider_id'] == 'qwen'
    assert v['second']['attempt'] == 2 and v['second']['provider_id'] == 'gemini'
    assert v['secondReplay']['attempt'] == 2
    assert v['secondReplay']['route_id'] == v['second']['route_id']
    assert v['secondReplay']['idempotent_replay'] is True
    assert v['third']['attempt'] == 3 and v['third']['provider_id'] == 'manus'
    assert v['retryLimit']['code'] == 'E_RETRY_LIMIT'
    assert v['afterCommit']['code'] == 'E_RETRY_AFTER_DISPATCH_COMMIT'
    assert v['conflict']['code'] == 'E_IDEMPOTENCY_CONFLICT'
    assert v['state']['retries_used'] == 2
    assert v['state']['max_retries'] == 2


def test_router_has_no_browser_launch_provider_network_or_secret_access_surface():
    s = CORE.read_text().lower()
    forbidden = (
        'child_process',
        'spawn(',
        'exec(',
        'launchpersistentcontext',
        '--user-data-dir',
        'playwright',
        'fetch(',
        'axios',
        'requests',
        'context.cookies',
        'storagestate',
        'localstorage',
        'sessionstorage',
        'indexeddb',
        'document.cookie',
        'authorization',
    )
    for token in forbidden:
        assert token not in s
    assert 'die.muxia.cluster-tab-lease-snapshot.v1' in CORE.read_text()
    assert '${label}_stale' in s
    assert 'queue_backpressure' in s
