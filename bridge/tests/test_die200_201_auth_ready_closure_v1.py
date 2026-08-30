from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
REG=ROOT/'company'/'component-registry-v1.json'
CLOSURE=ROOT/'company'/'muxia'/'receipts'/'DIE-200-201-auth-ready-closure.receipt.json'
EXEC=ROOT/'company'/'muxia'/'receipts'/'DIE-200-executive-linux.receipt.json'
DIV=ROOT/'company'/'muxia'/'receipts'/'DIE-201-division01-linux.receipt.json'


def test_die200_201_are_done_but_die204_still_waits_on_die202() -> None:
    g=json.loads(GRAPH.read_text(encoding='utf-8')); t={x['id']:x for x in g['tasks']}
    assert t['DIE-200']['status']=='DONE'
    assert t['DIE-201']['status']=='DONE'
    assert t['DIE-202']['status']=='WAITING_OPERATOR_CHANNEL_CANARY'
    assert t['DIE-203']['status']=='DONE'
    assert t['DIE-204']['status']=='BLOCKED'


def test_component_registry_marks_principals_ready_and_object_atlas_authoritative() -> None:
    d=json.loads(REG.read_text(encoding='utf-8'))['components']
    assert d['executive']['status']=='LINUX_READY_PRECUTOVER'
    assert d['division01']['status']=='LINUX_READY_PRECUTOVER'
    assert 'CUT-004A' in d['executive']['note']
    assert 'CUT-004B' in d['division01']['note']
    assert d['atlas_object_centric']['status']=='LINUX_AUTHORITATIVE_VERIFIED'
    assert '475,560' in d['atlas_object_centric']['note']


def test_die200_receipt_closes_manual_auth_gate_without_connector_cutover() -> None:
    d=json.loads(EXEC.read_text(encoding='utf-8'))
    assert d['status']=='DONE' and d['completion_blocker'] is None
    assert d['browser']['current_state']=='READY'
    assert d['browser']['browser_executable']=='/usr/bin/google-chrome-stable'
    assert d['browser']['launch_mode']=='DIRECT_SPAWN_LOOPBACK_CDP'
    assert d['browser']['login_ui_count']==0
    assert d['linux_runtime']['health_tools']==18
    assert d['connector_cutover']['performed_by_die200'] is False
    assert d['connector_cutover']['roadmap_task']=='CUT-004A'


def test_die201_receipt_closes_manual_auth_gate_without_connector_cutover() -> None:
    d=json.loads(DIV.read_text(encoding='utf-8'))
    assert d['status']=='DONE' and d['completion_blocker'] is None
    assert d['browser']['current_state']=='READY'
    assert d['browser']['browser_executable']=='/usr/bin/google-chrome-stable'
    assert d['browser']['launch_mode']=='DIRECT_SPAWN_LOOPBACK_CDP'
    assert d['browser']['login_ui_count']==0
    assert d['linux_runtime']['health_tools']==6
    assert d['connector_cutover']['performed_by_die201'] is False
    assert d['connector_cutover']['roadmap_task']=='CUT-004B'


def test_combined_closure_receipt_preserves_consumer_policy_and_windows_rollback() -> None:
    d=json.loads(CLOSURE.read_text(encoding='utf-8'))
    assert d['status']=='PASS'
    assert d['executive']['state']==d['division01']['state']=='READY'
    assert d['consumer_policy']['cookie_or_token_read'] is False
    assert d['consumer_policy']['private_backend_used'] is False
    assert d['consumer_policy']['cloudflare_or_auth_protection_bypass'] is False
    assert d['windows_rollback']['disabled'] is False
    assert d['chatgpt_connector_handoff']['performed'] is False
    assert d['chatgpt_connector_handoff']['executive_task']=='CUT-004A'
    assert d['chatgpt_connector_handoff']['division01_task']=='CUT-004B'