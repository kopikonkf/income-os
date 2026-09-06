from pathlib import Path
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parents[3]
CONTRACT = R / 'company/factory-asset/contracts/fa121-stability-canary.v1.json'
RUNNER = R / 'company/factory-asset/bin/run_fa121_stability_canary.mjs'
WORKER = R / 'company/factory-asset/lib/fa121_provider_worker.mjs'
TICK = R / 'company/factory-asset/bin/fa121-systemd-tick.sh'
INSTALL = R / 'company/factory-asset/bin/install_fa121_stability_systemd.sh'
START = R / 'company/factory-asset/bin/start_fa121_stability.sh'
SYSTEMD = R / 'company/factory-asset/systemd'


def contract():
    return json.loads(CONTRACT.read_text())


def test_contract_is_exact_24h_bounded_safe_load_before_dispatch():
    c = contract()
    assert c['task_id'] == 'FA-121'
    assert c['duration_seconds'] == 86400
    assert c['scheduler_tick_seconds'] == 300
    assert c['dispatch_interval_seconds'] == 7200
    assert c['max_provider_generations'] == 12
    assert c['max_provider_generations_per_provider'] == 6
    assert c['max_pre_dispatch_retries'] == 2
    assert c['queue']['limit'] == 1
    assert c['queue']['catch_up_burst_allowed'] is False
    assert c['cluster']['cluster_id'] == 'cluster-a'
    assert c['cluster']['max_tabs'] == 8
    assert c['authority']['production_seed_selection_allowed'] is False
    assert c['authority']['packaging_derivatives_count_as_provider_generation'] is False
    assert c['authority']['spend_authorized'] is False
    assert c['authority']['cookie_token_oauth_secret_read_allowed'] is False


def test_qwen_transport_truth_is_browser_fallback_not_fake_session_api():
    q = contract()['providers']['qwen']
    assert q['primary_transport_contract'] == 'SESSION_API'
    assert q['actual_live_transport'] == 'BROWSER_CDP'
    assert q['transport_role'] == 'FALLBACK'
    assert q['session_api_live_capacity'] == 'UNKNOWN'
    assert q['session_api_live_executor_claimed'] is False


def test_worker_uses_broker_tab_leases_and_never_spawns_or_reads_profile_secrets():
    s = WORKER.read_text().lower()
    for required in ('acquireclustertab', 'connectleasedclustertab', 'releaseclustertab', 'markclustertab'):
        assert required in s
    for forbidden in (
        'child_process', 'spawn(', '--user-data-dir', 'playwrightchromiumdriver', 'launchpersistentcontext',
        'context.cookies', 'storagestate', 'localstorage', 'sessionstorage', 'indexeddb', 'document.cookie',
        '/var/lib/muxia/profiles/chatgpt-linux-a/browser',
    ):
        assert forbidden not in s
    assert "actual_transport: 'browser_cdp'" in s
    assert 'qwen_session_api_live_executor_claimed' in s
    assert 'dispatch_committed' in s
    assert 'journalpath' in s


def test_runner_consumes_router_queue_readiness_capacity_and_restart_journal():
    s = RUNNER.read_text().lower()
    assert 'clusterawareproviderrouter' in s
    assert 'probefa121provider' in s
    assert 'fetchclusterleases' in s
    assert 'queue: { depth: 0, limit: 1' in s
    assert 'reconcileinterrupted' in s
    assert 'unknown_after_dispatch_restart' in s
    assert 'e_fa121_duplicate_committed_generation' in s
    assert 'heartbeatcoverage' in s
    assert 'e_fa121_24h_not_elapsed' in s
    assert 'profileintegrity' in s
    assert 'content_read: false' in s
    assert 'secret_value_hashing: false' in s


def test_systemd_lane_is_dedicated_and_does_not_replace_production_cycle():
    broker = (SYSTEMD / 'die-fa121-cluster-broker.service').read_text()
    tick_service = (SYSTEMD / 'die-fa121-stability-tick.service').read_text()
    timer = (SYSTEMD / 'die-fa121-stability.timer').read_text()
    wrapper = TICK.read_text()
    install = INSTALL.read_text()
    start = START.read_text()
    combined = '\n'.join((broker, tick_service, timer, wrapper, install, start)).lower()
    assert 'die-fa121' in combined
    assert 'onunitinactivesec=5min' in timer.lower()
    assert 'requires=die-fa121-cluster-broker.service' in tick_service.lower()
    assert 'muxia-cluster-broker.mjs' in broker
    assert '--control-port 39121' in broker
    assert 'die-production-cycle-v1' not in combined
    assert 'crontab' not in combined
    assert 'production_runtime_tick' not in combined
    assert 'systemctl disable --now die-fa121-stability.timer' in wrapper
    assert 'systemctl stop die-fa121-cluster-broker.service' in wrapper


def test_selftest_proves_sibling_isolation_retry_idempotency_and_real_time_gate_without_live_provider():
    with tempfile.TemporaryDirectory() as td:
        cp = subprocess.run(
            ['node', str(RUNNER), 'selftest', '--repo-root', str(R), '--state-root', td],
            check=True, text=True, capture_output=True, timeout=30,
        )
        v = json.loads(cp.stdout)
    assert v['result'] == 'PASS'
    a = v['assertions']
    assert a['checkpoint_sibling_routes_chatgpt'] is True
    assert a['actual_transport_browser_cdp'] is True
    assert a['duplicate_committed_generation_blocked'] is True
    assert a['early_24h_finalize_blocked'] is True
    assert a['restart_pre_dispatch_does_not_count_generation'] is True
    assert a['restart_post_dispatch_counts_once_without_retry'] is True
    assert a['max_retries_at_most_two'] is True
    assert a['qwen_session_api_not_claimed_live'] is True
