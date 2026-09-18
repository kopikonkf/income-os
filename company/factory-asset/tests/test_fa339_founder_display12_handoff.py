import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DISPLAY=ROOT/'company/browser/linux/founder_display12.mjs'
HANDOFF=ROOT/'company/browser/linux/founder_browser_handoff.sh'
REPAIR=ROOT/'company/browser/linux/founder_no_cdp_repair.sh'
CLUSTER=ROOT/'company/browser/linux/job_scoped_cluster_runtime.mjs'
PRINCIPAL=ROOT/'company/browser/linux/principal_browser_broker.mjs'
PRINCIPAL_UNIT=ROOT/'company/browser/linux/die-principal-browser-broker.service'
MUXIA_UNIT=ROOT/'company/muxia/scripts/linux/die-muxia-dispatch.service'
XSESSION=ROOT/'company/muxia/config/linux/xrdp/xsession'
INSTALL=ROOT/'company/factory-asset/bin/install_fa339_founder_display12.sh'
REG=ROOT/'company/factory-asset/registries/web-ai-clusters.v1.json'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'


def test_display12_workspace_mapping_is_canonical_and_five_way():
    s=DISPLAY.read_text(encoding='utf-8')
    assert "FOUNDER_DISPLAY=':12.0'" in s
    assert 'WORKSPACE_COUNT=5' in s
    for token in ["'die-lnx-executive-001':1", "'die-lnx-division-001':2", "'cluster-a':3", "'cluster-b':4"]:
        assert token in s
    assert "wmctrl" in s and "placePidOnFounderWorkspace" in s


def test_production_and_cognition_share_founder_display_not_hidden_xvfb():
    c=CLUSTER.read_text(encoding='utf-8')
    p=PRINCIPAL.read_text(encoding='utf-8')
    assert "spawn('/usr/bin/Xvfb'" not in c and "spawn('/usr/bin/Xvfb'" not in p
    assert 'DISPLAY:FOUNDER_DISPLAY' in c and 'DISPLAY:FOUNDER_DISPLAY' in p
    assert 'placePidOnFounderWorkspace' in c and 'placePidOnFounderWorkspace' in p
    assert 'founder_visible:true' in c and 'founder_visible:true' in p


def test_browser_owning_services_can_see_host_x11_socket_without_public_control_surface():
    principal=PRINCIPAL_UNIT.read_text(encoding='utf-8')
    muxia=MUXIA_UNIT.read_text(encoding='utf-8')
    assert 'Environment=DISPLAY=:12.0' in principal and 'Environment=DISPLAY=:12.0' in muxia
    assert 'PrivateTmp=true' not in principal and 'PrivateTmp=true' not in muxia
    assert ' /tmp' in principal and ' /tmp' in muxia
    assert 'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6' in principal
    assert 'RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX' in muxia
    assert '0.0.0.0' not in principal and '0.0.0.0' not in muxia


def test_handoff_is_durable_safe_preemption_and_no_cdp():
    s=HANDOFF.read_text(encoding='utf-8')
    assert 'FOUNDER_INTERACTIVE_HANDOFF' in s
    assert 'FOUNDER_PREEMPT_REQUEST' in s
    assert "requires_founder_release':state=='ACTIVE'" in s
    assert 'while pid="$(proc_for_profile || true)"' in s
    assert 'E_FOUNDER_HANDOFF_DRAIN_TIMEOUT' in s
    assert '--remote-debugging' not in s
    assert 'die-founder-display12' not in s  # handoff uses canonical Node placer directly
    assert 'founder_display12.mjs place' in s
    assert 'E_FOUNDER_BROWSER_STILL_ACTIVE' in s


def test_auth_repair_is_visible_on_same_dedicated_workspace_and_still_no_cdp():
    s=REPAIR.read_text(encoding='utf-8')
    assert 'DISPLAY=:12.0' in s
    assert 'founder_display12.mjs place' in s
    assert '--remote-debugging' not in s
    for target in ['executive','division01','cluster-a','cluster-b']:
        assert target in s


def test_xrdp_session_bootstraps_localuser_x_access_and_five_workspaces():
    x=XSESSION.read_text(encoding='utf-8')
    assert 'die-founder-display12-init' in x
    init=(ROOT/'company/browser/linux/founder_display12_session_init.sh').read_text(encoding='utf-8')
    assert 'xhost +SI:localuser:kopiko' in init
    assert 'wmctrl -n 5' in init


def test_registry_and_installer_describe_current_founder_surface():
    r=json.loads(REG.read_text(encoding='utf-8'))
    assert r['revision'].startswith('1.6.0-fa339')
    assert 'PRIMARY_DISPLAY_:12.0_XFCE' in r['rules']['founder_operating_surface']
    assert 'SAFE_PREEMPT' in r['rules']['founder_handoff_policy']
    by={c['cluster_id']:c for c in r['clusters']}
    assert by['cluster-a']['primary_display']==':12.0' and by['cluster-a']['founder_workspace_number']==4
    assert by['cluster-b']['primary_display']==':12.0' and by['cluster-b']['founder_workspace_number']==5
    i=INSTALL.read_text(encoding='utf-8')
    assert 'die-founder-browser-handoff' in i and 'die-founder-display12-init' in i
    assert 'die-principal-browser-broker.service die-muxia-dispatch.service' in i


def test_graph_seals_fa339_then_fa340():
    g=json.loads(GRAPH.read_text(encoding='utf-8')); by={t['id']:t for t in g['tasks']}
    assert by['FA-339']['depends_on']==['FA-338'] and by['FA-338']['status']=='DONE'
    assert by['FA-339']['status']=='DONE' and by['FA-340']['status']=='DONE'
    assert 'FA-339-founder-visible-display12-handoff.receipt.json' in by['FA-339']['artifact']
