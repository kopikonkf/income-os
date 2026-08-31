from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'MCP-LNX-005-non-architect-cutover-readiness.acceptance.receipt.json'

def test_mcp_lnx005_done_without_premature_cut004_release() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['MCP-LNX-005']['status']=='DONE'
    assert tasks['CUT-004A']['status']=='BLOCKED'
    assert tasks['CUT-004B']['status']=='BLOCKED'
    assert tasks['CUT-004A']['depends_on']==['CUT-003','MCP-LNX-005']
    assert tasks['CUT-004B']['depends_on']==['CUT-003','MCP-LNX-005']

def test_cutover_readiness_aggregates_cloud_wake_society_and_restart_proofs() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['status']=='DONE'
    assert d['decision']=='CUTOVER_READY_NOT_HANDED_OFF'
    for dep in ('MCP-LNX-003','WAKE-LNX-002','ID-LNX-005','MCP-LNX-004'):
        assert d['dependencies'][dep]['status']=='DONE'
        assert d['dependencies'][dep]['receipt'].startswith('company/muxia/receipts/')
    assert d['linux_live_snapshot']['executive']['principal_id']=='die-lnx-executive-001'
    assert d['linux_live_snapshot']['executive']['tools']==18
    assert d['linux_live_snapshot']['executive']['browser_state']=='READY'
    assert d['linux_live_snapshot']['executive']['thread_generation']==2
    assert d['linux_live_snapshot']['division01']['principal_id']=='die-lnx-division-001'
    assert d['linux_live_snapshot']['division01']['tools']==6
    assert d['linux_live_snapshot']['division01']['browser_state']=='READY'
    assert d['linux_live_snapshot']['division01']['thread_generation']==1
    assert d['linux_live_snapshot']['hermes']['cron_active'] is True

def test_readiness_never_implies_cutover_authority_or_windows_retirement() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    a=d['authority_and_cutover_boundaries']
    assert a['linux_non_architect_stack_cutover_ready'] is True
    assert a['founder_connector_handoff_authorized'] is False
    assert a['windows_writer_freeze_authorized'] is False
    assert a['windows_service_retirement_authorized'] is False
    assert a['architect_linux_handoff_authorized'] is False
    assert a['cut004a_cut004b_still_require_cut003'] is True
    assert a['mx062_or_founder_promote_bypassed'] is False
    assert d['windows_rollback_snapshot']['executive']['health']=='PASS'
    assert d['windows_rollback_snapshot']['division01']['health']=='PASS'
    assert d['windows_rollback_snapshot']['must_remain_available_until']=='CUT-005'

def test_acceptance_preserves_soak_and_semantic_quality_truth() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['isolation_guards']['mx062_pid']==200975
    assert d['isolation_guards']['production_source_mutated'] is False
    assert d['isolation_guards']['mx062_mutated'] is False
    assert d['semantic_quality']['source_trust']=='DEGRADED'
    assert d['semantic_quality']['completeness']=='degraded'
    assert d['semantic_quality']['treated_as_transport_or_identity_failure'] is False
