import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RUNTIME=ROOT/'company/browser/linux/job_scoped_cluster_runtime.mjs'
PRINCIPAL=ROOT/'company/browser/linux/principal_job_browser_runtime.mjs'
COGNITION=ROOT/'company/browser/linux/cognition_roundtrip.mjs'
REPAIR=ROOT/'company/browser/linux/founder_no_cdp_repair.sh'
HOLD=ROOT/'company/browser/linux/auth_repair_hold.mjs'
DISPATCH=ROOT/'company/factory-asset/bin/production_multi_cluster_dispatch.mjs'
REG=ROOT/'company/factory-asset/registries/web-ai-clusters.v1.json'
INSTALL=ROOT/'company/factory-asset/bin/install_fa338_job_scoped_lifecycle.sh'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'


def test_cluster_runtime_is_headful_job_scoped_and_proves_close():
    s=RUNTIME.read_text(encoding='utf-8')
    for token in ["spawn('/usr/bin/Xvfb'", "'--headless','false'", 'E_LIFECYCLE_TERMINAL_EVIDENCE_REQUIRED', 'debug_endpoint_closed', 'profile_process_gone', 'lease_released']:
        assert token in s
    assert '127.0.0.1' in s


def test_production_dispatch_owns_runtime_around_provider_attempt():
    s=DISPATCH.read_text(encoding='utf-8')
    assert 'startJobScopedClusterRuntime' in s
    assert 'runtimeIdleSnapshot' in s
    assert 'await runtime.stop({terminalEvidencePath:finalReceipt' in s
    assert "await runtime.stop({terminalEvidencePath:journal,reason:'PRE_DISPATCH_FAILURE'})" in s
    assert 'FA338_LIVE_PROBE_REQUIRED_AFTER_SPAWN' in s
    assert 'writeAuthRepairHold' in s and "['CHECKPOINT','AUTH_REQUIRED']" in s
    assert "schema:'die.muxia.cluster-tab-lease-snapshot.v1'" in s
    assert 'leases:[]' in s and 'max_tabs:Number(c.max_tabs||8)' in s
    assert "owner_model:'JOB_SCOPED_HEADFUL_BROWSER_CDP'" in s


def test_registry_supersedes_external_persistent_owner_model():
    r=json.loads(REG.read_text(encoding='utf-8'))
    assert r['revision'].startswith('1.5.0-fa338')
    assert 'JOB_SCOPED_HEADFUL_CHROME' in r['rules']['browser_owner_model']
    for c in r['clusters'][:2]:
        assert c['browser_owner_model']=='JOB_SCOPED_HEADFUL_BROWSER_CDP'
        assert c['lifecycle_state']=='COLD_WHEN_IDLE'
        assert c['browser_lifecycle_service'] is None
        assert c['broker_service'] is None
        assert c['browser_debug_port'] is None


def test_cognition_is_wrapped_in_bounded_principal_browser():
    s=PRINCIPAL.read_text(encoding='utf-8')
    c=COGNITION.read_text(encoding='utf-8')
    assert 'withPrincipalJobBrowser' in c and 'withPrincipalJobBrowser' in s
    assert 'E_AUTH_REPAIR_REQUIRED' in s
    assert 'profile_process_gone' in s
    assert '/cognition-receipts' in s and 'job-browser-receipts' not in s
    assert 'browser-lifecycle-${safeJob}' in s
    assert 'readRepairHold' in s and 'writeAuthRepairHold' in s
    assert "spawn('/usr/bin/Xvfb'" in s


def test_founder_repair_is_same_profile_headful_and_no_cdp():
    r=REPAIR.read_text(encoding='utf-8')
    assert '--remote-debugging' not in r
    assert 'E_REPAIR_PROFILE_BUSY' in r
    assert 'DISPLAY="${DISPLAY:-:12.0}"' in r
    for name in ['executive','division01','cluster-a','cluster-b']:
        assert name in r
    assert 'FOUNDER_NO_CDP_REPAIR' in r and "'state':'CLOSED'" in r
    h=HOLD.read_text(encoding='utf-8'); assert 'requires_founder_release' in h and 'automated_cdp_allowed:false' in h


def test_cutover_disables_legacy_owner_services_but_retains_rollback_files():
    s=INSTALL.read_text(encoding='utf-8')
    for unit in ['die-fa121-cluster-broker.service','die-muxia-cluster-a-browser.service','die-muxia-cluster-b.service','die-muxia-cluster-b-browser.service']:
        assert unit in s
    assert 'disable --now' in s
    assert 'die-muxia-dispatch.service' in s
    assert (ROOT/'company/factory-asset/systemd/die-muxia-cluster-a-browser.service').exists()
    assert (ROOT/'company/factory-asset/systemd/die-muxia-cluster-b-browser.service').exists()


def test_historical_installers_require_explicit_rollback_gate():
    for rel in ['company/factory-asset/bin/install_fa121_stability_systemd.sh','company/factory-asset/bin/install_cluster_b_broker_systemd.sh']:
        assert 'FA338_LEGACY_ROLLBACK' in (ROOT/rel).read_text(encoding='utf-8')


def test_graph_dependency_is_still_fa337_until_live_acceptance_updates_status():
    g=json.loads(GRAPH.read_text(encoding='utf-8'));by={t['id']:t for t in g['tasks']}
    assert by['FA-338']['depends_on']==['FA-337']
    assert by['FA-337']['status']=='DONE'
