from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPTS=ROOT/'company'/'muxia'/'receipts'
MODULE=ROOT/'company'/'browser'/'linux'/'cognition_acceptance.py'
CONV_SHA='7cdace09ba4fa80b55be5c1d74de9bb72977d7df'

def load_module():
    spec=importlib.util.spec_from_file_location('final_cognition_acceptance',MODULE); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_final_identity_chain_is_done_and_stability_lane_released() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['WAKE-LNX-002']['status']=='DONE'
    assert tasks['ID-LNX-003']['status']=='DONE'
    assert tasks['ID-LNX-004']['status']=='DONE'
    assert tasks['ID-LNX-005']['status']=='DONE'
    assert tasks['MCP-LNX-004']['status']=='DONE'
    assert tasks['MCP-LNX-005']['status']=='DONE'

def test_real_chatgpt_convergence_and_role_assimilation_validate() -> None:
    m=load_module()
    executive=json.loads((RECEIPTS/'ID-LNX-003-executive-cognition.acceptance.receipt.json').read_text(encoding='utf-8'))
    division=json.loads((RECEIPTS/'ID-LNX-004-division01-cognition.acceptance.receipt.json').read_text(encoding='utf-8'))
    operator=json.loads((RECEIPTS/'ID-LNX-002-operator-v2-linux.acceptance.receipt.json').read_text(encoding='utf-8'))
    assert m.validate_assimilation('executive',executive,CONV_SHA)==[]
    assert m.validate_assimilation('division01',division,CONV_SHA)==[]
    assert m.validate_society(executive,division,operator,CONV_SHA)==[]
    assert executive['acknowledgement_basis']['principal_bootstrap_status']=='PASS'
    assert division['acknowledgement_basis']['principal_bootstrap_status']=='PASS'
    assert executive['acknowledgement_basis']['verbatim_responsibility_list_from_principal'] is False
    assert division['acknowledgement_basis']['verbatim_responsibility_list_from_principal'] is False

def test_wake_convergence_preserves_degraded_truth_and_executive_rollover() -> None:
    wake=json.loads((RECEIPTS/'WAKE-LNX-002-state-convergence.acceptance.receipt.json').read_text(encoding='utf-8'))
    assert wake['status']=='DONE'
    assert wake['executive']['thread_generation']==2
    assert wake['executive']['previous_generation_lifecycle']=='superseded'
    assert wake['division01']['thread_generation']==1
    for role in ('executive','division01'):
        assert wake[role]['freshness_status']=='fresh'
        assert wake[role]['canon_load_status']=='VERIFIED'
        assert wake[role]['source_trust']=='DEGRADED'
        assert wake[role]['completeness']=='degraded'
    assert wake['boundary']['account_or_thread_memory_authority'] is False
    assert wake['boundary']['private_backend_used'] is False

def test_society_receipt_proves_hermes_middleware_and_scheduler_recovery() -> None:
    d=json.loads((RECEIPTS/'ID-LNX-005-principal-society.acceptance.receipt.json').read_text(encoding='utf-8'))
    assert d['status']=='DONE'
    loop=d['governed_review_middleware']
    assert loop['direct_executive_division_chat_operational_authority'] is False
    assert loop['REVISE']=='return_to_division01_new_artifact_hash'
    assert loop['VETO_PENDING_EVIDENCE']=='block_and_request_evidence'
    assert loop['old_lineage_requires_superseded'] is True
    assert loop['linux_division_target']=='die-lnx-division-001'
    runtime=d['operator_runtime_health']
    assert runtime['cron_active_after_recovery'] is True
    assert runtime['recovered_local_outbox_claim_sequences']==[2,3]
    assert runtime['journal_history_deleted'] is False
    assert runtime['external_side_effect_performed_by_recovery'] is False
    authority=d['authority_invariants']
    assert authority['state_manager_is_canonical_writer'] is True
    assert authority['founder_retains_irreversible_authority'] is True
    assert authority['executive_commands_workers'] is False
    assert authority['division01_commands_workers'] is False
    assert authority['muxia_makes_strategy_decisions'] is False
