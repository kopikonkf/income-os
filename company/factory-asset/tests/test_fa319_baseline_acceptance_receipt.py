import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REC=ROOT/'company/factory-asset/receipts/FA-319-baseline-package-acceptance.receipt.json'

def test_fa319_real_canary_reaches_founder_qc_ready_package_without_publication_authority():
    d=json.loads(REC.read_text(encoding='utf-8'))
    assert d['status']=='DONE' and d['result']=='PASS'
    c=d['canary']; sm=d['state_machine']; rights=d['rights']; inv=d['baseline_invariants']
    assert c['seed_id']=='SEED-000028' and c['seed_noun']=='gift box'
    assert c['prompt_authority']=='TYPED_VISUAL_CONTRACT_V1'
    assert c['provider_prompt_sha256']=='9b5a18efad70e2ead88826cdc13fafba78b85d25f79bf5bddfe8c5a323a1ab00'
    assert c['provider_id']=='qwen' and c['cluster_id']=='cluster-a' and c['provider_attempt']==1
    assert sm['required_sequence'][0]=='ARTIFACT_CREATED'
    assert sm['durable_advance_sequence']==sm['required_sequence'][1:]
    assert sm['package_result']=='PACKAGE_READY' and c['final_state']=='WAITING_FOUNDER_QC'
    assert c['final_status']=='PARKED_HUMAN_GATE' and c['founder_qc']=='PENDING'
    assert rights['cpu_only'] is True and rights['self_test']=='PASS'
    assert [rights[k] for k in ('logo','watermark','safety','source_ip')]==['CLEAR']*4
    assert rights['ocr_detected_strings']==[]
    assert rights['source_ip_applicable_risk_indices']==[1,2]
    assert inv['production_schedule']=='0 */3 * * *' and inv['scale_100_per_day'] is False
    assert inv['fa125_status']=='WAITING_FOUNDER' and inv['fa126_status']=='DEFERRED'
    assert inv['submission_authorized'] is False and inv['publication_authorized'] is False and inv['marketplace_upload_performed'] is False
    assert inv['cluster_a_active_leases_after_canary']==0 and inv['cluster_b_active_leases_after_canary']==0
