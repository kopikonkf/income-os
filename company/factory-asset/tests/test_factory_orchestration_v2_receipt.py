import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-139-hermes-orchestration-v2-wiring.receipt.json'
def test_fa139_acceptance_stops_without_rights_then_resumes_same_card():
 r=json.loads(REC.read_text());assert r['result']=='PASS';assert r['first_pass_without_detector_evidence']['status']=='RIGHTS_REVIEW_REQUIRED';assert r['second_pass_after_exact_hash_rights_observation']['status']=='WAITING_FOUNDER_QC';assert r['postproduction_final_state']['status']=='PARKED_HUMAN_GATE'
def test_fa139_listing_filename_and_submission_fields_are_human_friendly():
 r=json.loads(REC.read_text());f=r['final_artifact'];m=r['metadata'];assert f['listing_filename'].startswith('shopping-bag-isolated-object__');assert f['listing_filename']!='asset.png';assert f['seed_noun']=='shopping bag';assert m['listing_filename']==f['listing_filename'];assert m['submission_fields']['title'] and m['submission_fields']['description'] and m['submission_fields']['keywords'];assert m['binary_metadata_injected'] is False
def test_fa139_telegram_milestones_and_idempotency():
 r=json.loads(REC.read_text());k=r['telegram']['kinds'];assert {'PRODUCTION_STARTED','ARTIFACT_CREATED','QA_QC_UPDATE','WAITING_FOUNDER_QC'}.issubset(set(k));assert r['telegram']['duplicate_final_milestone_suppressed'] is True
def test_fa139_no_live_provider_or_publish_authority_in_acceptance():
 r=json.loads(REC.read_text());assert r['authority']=={'live_provider_call':False,'marketplace_upload':False,'publication':False,'founder_qc_completed':False,'human_rights_clearance':False,'spend_usd':0}