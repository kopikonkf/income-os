import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-136-rights-signal-gate.receipt.json'
def test_fa136_receipt_seals_all_expected_routes():
 r=json.loads(REC.read_text());assert r['result']=='PASS';assert all(x['expected']==x['result']['result'] for x in r['cases']);assert r['acceptance']['unknown_never_promoted_to_pass'] is True
def test_even_signal_pass_never_grants_human_rights_clearance():
 r=json.loads(REC.read_text());clean=next(x['result'] for x in r['cases'] if x['name']=='clean-complete');assert clean['result']=='PASS';assert clean['human_rights_clearance'] is False and clean['founder_qc_required'] is True and clean['submission_eligible'] is False
def test_fa136_authority_is_zero_for_clearance_submission_publication():
 a=json.loads(REC.read_text())['authority'];assert a=={'human_rights_clearance':False,'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'spend_usd':0}