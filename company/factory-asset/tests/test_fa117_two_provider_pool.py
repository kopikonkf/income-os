from pathlib import Path
import json

R=Path(__file__).resolve().parents[3]
FIX=R/'company/factory-asset/fixtures/provider-pool/FA-117-live-acceptance.json'
REC=R/'company/factory-asset/receipts/FA-117-two-provider-pool-acceptance.receipt.json'


def test_live_pool_exactly_two_bounded_provider_calls():
    v=json.loads(FIX.read_text())
    assert v['result']=='PASS'
    assert v['provider_generation_calls']=={'qwen':1,'chatgpt':1,'total':2}
    assert v['operator_actions_after_dispatch']=={'qwen':0,'chatgpt':0}
    assert v['providers']['qwen']['transport_class']=='BROWSER_CDP'
    assert v['providers']['qwen']['transport_role']=='FALLBACK'
    assert v['providers']['qwen']['primary_transport']=='SESSION_API'
    assert v['providers']['chatgpt']['transport_class']=='BROWSER_CDP'


def test_masters_dedupe_and_capacity_are_truthful():
    v=json.loads(FIX.read_text())
    assert v['providers']['qwen']['media']['decode_verified'] is True
    assert v['providers']['chatgpt']['media']['decode_verified'] is True
    assert v['providers']['qwen']['capacity_state']=='AVAILABLE'
    assert v['providers']['chatgpt']['capacity_state']=='AVAILABLE'
    assert v['master_staging']['attempt_count']==4
    assert v['master_staging']['unique_blob_count']==2
    assert v['master_staging']['qwen_duplicate_reused'] is True
    assert v['master_staging']['chatgpt_duplicate_reused'] is True
    assert v['master_staging']['canonical_truth'] is False


def test_shared_profile_and_tab_budget_fail_closed_boundary():
    v=json.loads(FIX.read_text())
    assert v['shared_profile']['live_intervals_non_overlapping'] is True
    assert v['shared_profile']['logical_contention_blocked'] is True
    assert v['shared_profile']['lease_released_after_each'] is True
    m=v['resource_tab_metrics']
    assert m['open_pages_before']>m['max_tabs']
    assert m['open_pages_after']==m['max_tabs']==8
    assert m['closed_by_budget']>0
    assert m['within_tab_ceiling_after'] is True


def test_receipt_preserves_authority_and_capacity_key_truth():
    r=json.loads(REC.read_text())
    t=r['truth_boundaries']
    assert r['status']=='DONE' and r['result']=='PASS'
    assert t['qwen_session_api_live_executor_claimed'] is False
    assert t['masters_canonical_truth'] is False
    assert t['submission_authorized'] is False
    assert t['publication_authorized'] is False
    assert t['spend_usd']==0
    assert 'provider+cluster' in t['capacity_keying_issue']
    assert '10 pages' in t['startup_tab_edge']