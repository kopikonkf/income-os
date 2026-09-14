import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company/company-os/die-h01'
LIB=H01/'lib/phase0_production_intent.py'
spec=importlib.util.spec_from_file_location('h01_132a',LIB)
M=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name]=M; spec.loader.exec_module(M)


def qrow(name='food',qid='H01-SVGQ-CAND-0000001',pos=1):
    return {'schema':'die.h01.svg-production-queue.v1','queue_item_id':qid,'queue_position':pos,'idempotency_key':'a'*64,'dispatch_eligible':True,'gates':{'rights':'PASS','feasibility':'PASS'},'production':{'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'},'source':{'id':'CAND-0000001','canonical_name':name,'raw_noun_id':1,'source_tier':'pass','suitability':'lexname=noun.artifact','ip_risk':'none','wave3_status':'eligible'}}


def selected(name='food',reason='EVIDENCE_RANKED',score=0.525,eids=None):
    return {'batch_position':1,'queue_item_id':'H01-SVGQ-CAND-0000001','queue_position':1,'source_candidate_id':'CAND-0000001','canonical_name':name,'idempotency_key':'a'*64,'source_tier':'pass','suitability':'lexname=noun.artifact','selection_reason':reason,'priority_rank':1 if reason=='EVIDENCE_RANKED' else None,'priority_score':score if reason=='EVIDENCE_RANKED' else None,'priority_components':{'demand':0.50625 if reason=='EVIDENCE_RANKED' else None,'confidence':0.6 if reason=='EVIDENCE_RANKED' else None,'competition_opportunity':None,'evidence_ids':list(eids or []),'weights':{'demand':0.6,'competition_opportunity':0.25,'confidence':0.15}},'human_context':None,'family_hypotheses':[],'planned_provider':'gemini','adaptive_provider_redistribution_allowed':True}


def selector(item):
    return {'schema':'die.h01.daily-production-selector.v1','status':'FROZEN','day_key':'2026-09-14','selection_id':'H01-DAILY-'+'A'*24,'items':[item],'authority':{'production_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}


def demand(reason='ranked'):
    eid='H01-SIG-'+'B'*24
    rec={'schema':'die.h01.demand-signal-ranking.v1','queue_item_id':'H01-SVGQ-CAND-0000001','signal_state':'PARTIAL' if reason=='ranked' else 'NO_EVIDENCE','rank_state':'RANKED' if reason=='ranked' else 'UNRANKED','rank_score':0.50625 if reason=='ranked' else None,'confidence':'MEDIUM' if reason=='ranked' else 'NONE','evidence_refs':[{'evidence_id':eid,'evidence_sha256':'c'*64,'signal_class':'TREND','freshness':'FRESH'}] if reason=='ranked' else [],'discoveries':{'buyers':[],'use_cases':[],'family_hypotheses':[]},'effects':{},'authority':{}}
    ex={'queue_item_id':'H01-SVGQ-CAND-0000001','rank_state':rec['rank_state'],'rank_score':rec['rank_score'],'canonical_name':'food','contributions':[{'connector_id':'123rf_trending_search_v1','evidence_id':eid,'tier':'MARKETPLACE_POPULAR_QUERY','match_type':'TERM_EXACT','freshness':'FRESH','source_confidence':'MEDIUM','contribution':0.50625}] if reason=='ranked' else []}
    return {'schema':'die.h01.demand-signal-materialization.v1','materialization_id':'H01-DMAT-'+'D'*24,'records':[rec],'explanations':[ex]}, eid


def build(sel,mat,queue=None):
    return M.build_intents(selector=sel,materialization=mat,queue_rows=queue or [qrow()],cycle_id='H01-DCYCLE-'+'E'*24,selector_manifest_sha256='1'*64,demand_materialization_sha256='2'*64)


def test_ranked_selection_binds_exact_queue_and_evidence_lineage():
    mat,eid=demand('ranked'); intents=build(selector(selected(eids=[eid])),mat)
    x=intents[0]
    assert x['queue_identity']['canonical_name']=='food'
    assert x['queue_identity']['queue_item_id']=='H01-SVGQ-CAND-0000001'
    assert x['selection']['selection_reason']=='EVIDENCE_RANKED'
    assert x['demand']['evidence_refs'][0]['evidence_id']==eid
    assert x['commercial_basis']['basis_mode']=='MARKETPLACE_DEMAND_EVIDENCE'
    assert x['commercial_basis']['source_tiers']==['MARKETPLACE_POPULAR_QUERY']
    assert x['phase0_guard']=={'standalone_noun_only':True,'human_context':None,'family_hypotheses':[],'longtail':None,'object_human_cross_join':False}
    assert all(v is False for v in x['authority'].values())
    assert 'planned_provider' not in json.dumps(x)


def test_fallback_selection_preserves_no_evidence_truth_without_buyer_claim():
    mat,_=demand('fallback'); x=build(selector(selected(reason='SOURCE_ORDER_FALLBACK')),mat)[0]
    assert x['demand']['rank_state']=='UNRANKED'
    assert x['commercial_basis']['basis_mode']=='FALLBACK_NO_DEMAND_EVIDENCE'
    assert x['commercial_basis']['demand_specific_claim_allowed'] is False
    assert x['commercial_basis']['source_tiers']==[]
    assert 'No demand-evidence-specific buyer segment' in x['commercial_basis']['buyer_scope']


def test_identity_drift_fails_closed():
    mat,eid=demand('ranked'); item=selected(eids=[eid]); item['canonical_name']='foods'
    try: build(selector(item),mat)
    except M.Phase0IntentError as exc: assert 'E_IDENTITY_DRIFT' in str(exc)
    else: raise AssertionError('identity drift accepted')


def test_ranked_selector_evidence_must_equal_demand_record_evidence():
    mat,_=demand('ranked')
    try: build(selector(selected(eids=['H01-SIG-'+'F'*24])),mat)
    except M.Phase0IntentError as exc: assert 'E_RANKED_BINDING' in str(exc)
    else: raise AssertionError('evidence drift accepted')


def test_phase0_rejects_human_context_or_family_hypotheses():
    mat,eid=demand('ranked'); item=selected(eids=[eid]); item['human_context']={'id':'HCTX-X'}
    try: build(selector(item),mat)
    except M.Phase0IntentError as exc: assert 'E_PHASE0_CONTEXT_LEAK' in str(exc)
    else: raise AssertionError('human context accepted')


def test_same_frozen_inputs_are_byte_stable():
    mat,eid=demand('ranked'); kwargs=(selector(selected(eids=[eid])),mat)
    a=build(*kwargs); b=build(*kwargs)
    assert a==b
    assert M.canonical_bytes(a)==M.canonical_bytes(b)
    assert a[0]['intent_id']==b[0]['intent_id']


def test_persist_manifest_is_immutable_and_counts_ranked_fallback():
    ranked,eid=demand('ranked'); first=build(selector(selected(eids=[eid])),ranked)[0]
    fallback,_=demand('fallback'); second=build(selector(selected(reason='SOURCE_ORDER_FALLBACK')),fallback)[0]
    second['intent_id']='H01-P0INT-'+'9'*24; second['queue_identity']['queue_item_id']='H01-SVGQ-CAND-0000002'; second['selection']['batch_position']=2
    with tempfile.TemporaryDirectory() as td:
        result=M.persist_intents(intents=[first,second],output_root=Path(td),queue_sha256='4'*64)
        m=result['manifest']
        assert m['status']=='FROZEN' and m['selected_count']==2
        assert m['evidence_ranked_count']==1 and m['fallback_count']==1
        assert m['phase0_policy']['human_atlas_join'] is False
        again=M.persist_intents(intents=[first,second],output_root=Path(td),queue_sha256='4'*64)
        assert again['manifest_id'] if 'manifest_id' in again else again['manifest']['manifest_id']==m['manifest_id']


def test_non_frozen_selector_rejected():
    mat,eid=demand('ranked'); s=selector(selected(eids=[eid])); s['status']='DRAFT'
    try: build(s,mat)
    except M.Phase0IntentError as exc: assert 'E_SELECTOR_NOT_FROZEN' in str(exc)
    else: raise AssertionError('draft accepted')
