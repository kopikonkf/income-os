import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REC=R/'company/factory-asset/receipts/FA-137-metadata-package-readiness.receipt.json'
def test_fa137_positive_actual_package_ready_and_hash_bound():
 r=json.loads(REC.read_text());assert r['result']=='PASS';assert r['readiness']['result']=='PACKAGE_READY';assert r['readiness']['metadata']['master_sha256']==r['master']['sha256'];assert r['dry_run_package']['result']=='PASS';assert r['dry_run_package']['semantic_asset_count']==1;assert r['readiness']['package_plan']['publication_action']=='NONE' and r['readiness']['package_plan']['upload_action']=='NONE'
def test_fa137_derivatives_are_exact_qa_verified_hashes():
 r=json.loads(REC.read_text());assert len(r['derivatives'])==2
 for d in r['derivatives']:
  assert d['qa_result']=='PASS' and d['sha256_verified'] is True and d['qa_sha256']==d['sha256'] and d['master_sha256']==r['master']['sha256']
def test_fa137_ai_disclosure_and_metadata_are_present():
 r=json.loads(REC.read_text());m=r['metadata'];assert m['ai_generated'] is True and m['ai_disclosure']=='GENERATIVE_AI';assert m['title'] and m['description'] and len(m['keywords'])>=3;assert len(m['metadata_sha256'])==64
def test_fa137_negative_controls_all_block():
 r=json.loads(REC.read_text());n=r['negative_controls'];assert all(v['result']=='PACKAGE_BLOCKED' for v in n.values());assert 'RIGHTS_REVIEW_REQUIRED' in n['rights_review']['blockers'];assert any(x.startswith('DERIVATIVE_MISSING:') for x in n['missing_derivative']['blockers']);assert any(x.startswith('DERIVATIVE_QA_HASH_MISMATCH:') for x in n['derivative_hash_mismatch']['blockers']);assert 'DERIVATIVE_PLAN_BLOCKED' in n['unknown_marketplace']['blockers'];assert 'AI_DISCLOSURE_REQUIRED' in n['missing_ai_disclosure']['blockers']
def test_fa137_does_not_grant_rights_or_publish_authority():
 r=json.loads(REC.read_text());assert r['acceptance']['human_rights_clearance_granted'] is False;assert r['authority']=={'marketplace_upload':False,'publication':False,'submission_authority':'FOUNDER_CONTROLLED','spend_usd':0}