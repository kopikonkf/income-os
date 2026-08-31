from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'MCP-LNX-004-restart-session-isolation-stability.acceptance.receipt.json'

def test_mcp_lnx004_done_and_lnx005_released() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['MCP-LNX-004']['status']=='DONE'
    assert tasks['MCP-LNX-005']['status']=='DONE'

def test_services_tunnel_and_browser_sessions_survive_controlled_restart() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['status']=='DONE'
    for role in ('executive','division01'):
        service=d['service_restart'][role]
        assert service['active'] is True and service['enabled'] is False
        assert service['post_dcr_restart_pid'] != service['pre_pid']
        assert service['control_policy']=='staging-read-only'
        browser=d['browser_restart'][role]
        assert browser['browser_post_pid'] != browser['browser_pre_pid']
        assert browser['state']=='READY' and browser['login_ui_count']==0
        assert browser['debug_host']=='127.0.0.1'
        assert browser['wake_focus']=='PASS'
        assert browser['thread_generation_pre']==browser['thread_generation_post']
    assert d['browser_restart']['cross_browser_restart_interference'] is False

def test_oauth_is_restart_stable_and_cross_principal_fail_closed() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))['oauth_restart_stability']
    assert d['unauthenticated_post_mcp']=={'executive_http':401,'division01_http':401}
    assert d['static_client_authorize_after_restart']=={'executive_http':200,'division01_http':200}
    assert d['same_principal_dcr_after_restart']=={'executive_http':200,'division01_http':200}
    assert d['cross_principal_dcr_after_restart']=={'executive_client_on_division_http':401,'division_client_on_executive_http':401}
    assert d['transient_edge_origin_reconnect']['recovered_on_next_health_probe'] is True
    assert d['transient_edge_origin_reconnect']['persistent_data_loss'] is False

def test_stability_logs_rollback_and_soak_isolation_are_clean() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    stable=d['stability_window']; assert stable['samples']==6 and stable['all_samples_passed'] is True
    logs=d['sanitized_logging']; assert logs['executive_high_risk_secret_hits']==0 and logs['division01_high_risk_secret_hits']==0 and logs['cloudflared_high_risk_secret_hits']==0
    assert d['public_endpoints']['windows_executive_rollback']['health']=='PASS'
    assert d['public_endpoints']['windows_division01_rollback']['health']=='PASS'
    isolation=d['isolation_guards']; assert isolation['production_source_mutated'] is False and isolation['mx062_mutated'] is False
    assert isolation['mx062_pid']==200975
