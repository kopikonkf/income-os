import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / 'company/factory-asset/lib/console_operations.py'
CONSOLE = ROOT / 'company/factory-asset/console-prototype'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fixture_state():
    queue = {
        'schema': 'die.factory-asset.console-queue-state.v1',
        'provider_dispatch_performed': False,
        'reconciliation_required_job_ids': [],
        'events': [
            {'job_id': 'J1', 'label': 'ready', 'blueprint_id': 'BP1', 'semantic_asset_id': 'SA1', 'state': 'READY', 'attempts': 0, 'retries': 0, 'recovery_count': 0, 'failure_code': None},
            {'job_id': 'J2', 'label': 'retry', 'blueprint_id': 'BP2', 'semantic_asset_id': 'SA2', 'state': 'RETRY_WAIT', 'attempts': 1, 'retries': 1, 'recovery_count': 0, 'failure_code': 'RATE_LIMITED'},
            {'job_id': 'J3', 'label': 'running', 'blueprint_id': 'BP3', 'semantic_asset_id': 'SA3', 'state': 'RUNNING', 'attempts': 1, 'retries': 0, 'recovery_count': 0, 'failure_code': None},
        ],
    }
    topology = {
        'schema': 'die.factory-asset.console-cluster-topology.v1',
        'evidence_mode': 'LIVE_BROKER_SANITIZED',
        'observed_at': '2026-09-10T03:00:00Z',
        'clusters': [
            {
                'cluster_id': 'cluster-a', 'health': 'HEALTHY', 'broker_state': 'READY',
                'tab_occupancy': {'open_pages': 1, 'max_tabs': 8, 'active_leases': 0, 'generation_slots_available': 5},
                'provider_sessions': [
                    {'provider_id': 'qwen', 'membership': 'ACTIVE', 'preferred_transport': 'SESSION_API', 'readiness': 'HEALTHY', 'capacity': 'AVAILABLE'},
                    {'provider_id': 'duckai', 'membership': 'ACTIVE', 'preferred_transport': 'BROWSER_CDP', 'readiness': 'DEGRADED', 'capacity': 'UNAVAILABLE'},
                ],
            },
            {
                'cluster_id': 'cluster-b', 'health': 'HEALTHY', 'broker_state': 'READY',
                'tab_occupancy': {'open_pages': 1, 'max_tabs': 8, 'active_leases': 0, 'generation_slots_available': 4},
                'provider_sessions': [
                    {'provider_id': 'chatgpt', 'membership': 'ACTIVE', 'preferred_transport': 'BROWSER_CDP', 'readiness': 'HEALTHY', 'capacity': 'AVAILABLE'},
                ],
            },
        ],
    }
    providers = {
        'schema': 'die.factory-asset.provider-dashboard.v1',
        'evidence_mode': 'LIVE_BROKER_SANITIZED',
        'observed_at': '2026-09-10T03:00:00Z',
        'providers': [
            {'provider_id': 'qwen', 'cluster_id': 'cluster-a', 'eligibility': 'ELIGIBLE', 'health': 'HEALTHY', 'capacity': 'AVAILABLE', 'transport': 'BROWSER_CDP'},
            {'provider_id': 'chatgpt', 'cluster_id': 'cluster-b', 'eligibility': 'ELIGIBLE', 'health': 'HEALTHY', 'capacity': 'AVAILABLE', 'transport': 'BROWSER_CDP'},
            {'provider_id': 'duckai', 'cluster_id': 'cluster-a', 'eligibility': 'COOLDOWN_OR_DEGRADED', 'health': 'DEGRADED', 'capacity': 'UNAVAILABLE', 'transport': 'BROWSER_CDP'},
        ],
    }
    return queue, topology, providers


def test_operations_composes_queue_route_retry_backpressure_without_dispatch():
    module = load('c016_operations', LIB)
    queue, topology, providers = fixture_state()
    data = module.build_operations_state(queue_state=queue, cluster_topology=topology, provider_dashboard=providers)
    assert data['schema'] == 'die.factory-asset.console-operations.v1'
    assert data['queue']['depth'] == 3 and data['queue']['retry_wait'] == 1 and data['queue']['retries_used'] == 1
    assert data['backpressure']['state'] == 'CLEAR' and data['backpressure']['browser_generation_slots_available'] == 9
    selected = data['routing']['selected_route']
    assert selected['provider_id'] == 'qwen' and selected['cluster_id'] == 'cluster-a' and selected['transport'] == 'SESSION_API'
    assert selected['dispatch_committed'] is False and data['routing']['provider_dispatch_performed'] is False
    duck = next(x for x in data['routing']['routes'] if x['provider_id'] == 'duckai')
    assert duck['schedulable'] is False and any('DEGRADED' in reason for reason in duck['reasons'])
    assert data['controls']['allowed_actions'] == ['START', 'PAUSE', 'RESUME', 'CANCEL', 'RETRY']


def test_operations_payload_is_allowlisted_and_secret_free():
    module = load('c016_operations_secret', LIB)
    queue, topology, providers = fixture_state()
    topology['clusters'][0]['profile_dir'] = '/secret/profile'
    topology['clusters'][0]['debug_port'] = 39221
    topology['clusters'][0]['provider_sessions'][0]['active_jobs'] = [{'lease_id': 'SECRET', 'claim_url': 'about:blank#secret'}]
    providers['providers'][0]['session_token'] = 'SECRET'
    text = json.dumps(module.build_operations_state(queue_state=queue, cluster_topology=topology, provider_dashboard=providers)).lower()
    for forbidden in ('profile_dir', 'debug_port', 'control_port', 'claim_url', 'lease_id', 'cookie', 'credential', 'token', 'oauth', 'private_key'):
        assert forbidden not in text


def test_operations_fails_closed_when_no_route_is_schedulable():
    module = load('c016_operations_blocked', LIB)
    queue, topology, providers = fixture_state()
    for provider in providers['providers']:
        provider['capacity'] = 'UNAVAILABLE'
    for cluster in topology['clusters']:
        for session in cluster['provider_sessions']:
            session['capacity'] = 'UNAVAILABLE'
    data = module.build_operations_state(queue_state=queue, cluster_topology=topology, provider_dashboard=providers)
    assert data['routing']['selected_route'] is None
    assert data['backpressure']['state'] == 'BLOCKED'


def test_http_operations_endpoint_is_read_only_composite():
    server = load('c016_server', CONSOLE / 'server.py')
    sample = {'schema': 'die.factory-asset.console-operations.v1', 'routing': {'provider_dispatch_performed': False}, 'queue': {'jobs': []}}
    server.operations_state = lambda: sample
    httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/operations', timeout=5) as response:
            assert json.loads(response.read()) == sample
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join(timeout=5)


def test_console_has_unified_operations_surface_and_bounded_controls():
    html = (CONSOLE / 'index.html').read_text()
    js = (CONSOLE / 'app.js').read_text()
    assert 'data-view="operations"' in html and 'view-operations' in html
    for marker in ("getLocal('/api/operations')", 'Blueprint / Batch Intent', 'Selected Provider + Cluster', 'Queue / Retry / Backpressure', 'Unified Batch Queue Operations', 'START', 'PAUSE', 'RESUME', 'CANCEL', 'RETRY', 'Live Dispatch Locked'):
        assert marker in js
    for forbidden in ('profile_dir', 'debug_port', 'control_port', 'claim_url', 'lease_id', 'session_token', 'private_key'):
        assert forbidden not in js
