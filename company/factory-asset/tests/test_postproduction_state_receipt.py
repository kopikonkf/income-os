import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-138-postproduction-state-machine.receipt.json'
def test_fa138_actual_sequence_is_exact_and_parked():
 r=json.loads(REC.read_text());p=r['positive'];assert p['state_sequence']==['ARTIFACT_CREATED','MASTER_VALIDATED','UPSCALE_DECIDED','DERIVATIVES_READY','TECHNICAL_QA_PASS','RIGHTS_SIGNAL_PASS_OR_REVIEW','METADATA_READY','PACKAGE_READY','WAITING_FOUNDER_QC'];assert p['final_status']=='PARKED_HUMAN_GATE' and p['revision']==8
def test_fa138_hash_lineage_and_active_master_transition():
 r=json.loads(REC.read_text());u=r['upscale_lineage_transition'];assert u['result']=='PASS' and u['source_master_sha256']!=u['active_master_sha256'];assert u['old_master_derivative_rejected']=='DERIVATIVE_MASTER_HASH_MISMATCH';assert r['positive']['source_master_sha256']==r['positive']['active_master_sha256']
def test_fa138_negative_controls_all_fail_closed():
 r=json.loads(REC.read_text());assert all(v['result']=='BLOCKED' for v in r['negative_controls'].values());codes={v['code'] for v in r['negative_controls'].values()};assert {'STATE_TRANSITION_INVALID','STALE_REVISION','EVENT_ID_CONFLICT','RIGHTS_REVIEW_UNRESOLVED','STATE_BLOCKED_BY_FAILURE','FAILURE_NOT_RETRYABLE','MASTER_VALIDATION_INVALID'}.issubset(codes)
def test_fa138_rights_review_requires_resolution_before_package():
 r=json.loads(REC.read_text());assert r['rights_review_resolution']=={'result':'PASS','state_after_resolution':'PACKAGE_READY','rights_disposition':'PASS'}
def test_fa138_founder_gate_is_not_qc_completion_or_rights_clearance():
 r=json.loads(REC.read_text());assert r['authority']=={'founder_qc_completed':False,'human_rights_clearance':False,'marketplace_upload':False,'publication':False,'spend_usd':0}