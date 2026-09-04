import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-134-cognition-router.receipt.json';POL=R/'company/factory-asset/registries/cognition-routing-policy.v1.json'
def test_fa134_receipt_seals_reuse_author_revision_and_challenge_routes():
 r=json.loads(REC.read_text());assert r['result']=='PASS';out={x['name']:x['route']['outcome'] for x in r['fixture_results']};assert out['reuse-valid-fixed-blueprint']=='REUSE_FIXED_BLUEPRINT';assert out['new-family-author-and-challenge']=='DIVISION01_AUTHOR_THEN_EXECUTIVE_CHALLENGE';assert out['stale-blueprint-revision-only']=='DIVISION01_REVISE';assert out['material-expression-revision-and-challenge']=='DIVISION01_REVISE_THEN_EXECUTIVE_CHALLENGE';assert out['executive-escalation-existing-blueprint']=='EXECUTIVE_CHALLENGE_EXISTING_BLUEPRINT'
def test_reuse_path_has_zero_cognition_calls():
 r=json.loads(REC.read_text());x=next(x['route'] for x in r['fixture_results'] if x['name']=='reuse-valid-fixed-blueprint');assert x['division01']['action']=='NONE' and x['executive']['action']=='NONE';assert [s['actor'] for s in x['sequence']]==['HERMES'];assert x['per_image_cognition_gate'] is False
def test_policy_denies_per_image_worker_and_provider_authority():
 p=json.loads(POL.read_text());i=p['invariants'];assert i['reuse_first'] is True;assert i['division01_per_image_gate'] is False and i['executive_per_image_gate'] is False;assert i['executive_authors_blueprint'] is False;assert i['division01_worker_authority'] is False and i['executive_worker_authority'] is False;assert i['provider_authority_granted'] is False
def test_fa134_zero_execution_authority():
 r=json.loads(REC.read_text());a=r['authority'];assert a['worker_dispatch_performed'] is False and a['provider_dispatch_performed'] is False and a['marketplace_upload'] is False and a['publication'] is False and a['spend_usd']==0