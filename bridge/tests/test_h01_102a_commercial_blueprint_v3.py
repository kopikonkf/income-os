import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company/company-os/die-h01'
sys.path.insert(0,str(H01/'lib')); sys.path.insert(0,str(H01/'engineering'))
from commercial_blueprint_v3 import build_blueprint_v3,sha256_value
import svg_prompt_composer_v2 as C


def intent(mode='MARKETPLACE_DEMAND_EVIDENCE', ranked=True):
    eid='H01-SIG-'+'A'*24
    evidence=[{'evidence_id':eid,'evidence_sha256':'b'*64,'signal_class':'TREND','freshness':'FRESH'}] if ranked else []
    tiers=['MARKETPLACE_POPULAR_QUERY'] if ranked else []
    return {
      'schema':'die.h01.phase0-production-intent.v1','intent_id':'H01-P0INT-'+'C'*24,'phase':'PHASE_0_STANDALONE_NOUN','day_key':'2026-09-14','cycle_id':'H01-DCYCLE-'+'D'*24,'selection_id':'H01-DAILY-'+'E'*24,
      'lineage':{'queue_row_sha256':'1'*64,'selector_item_sha256':'2'*64,'selector_manifest_sha256':'3'*64,'demand_record_sha256':'4'*64,'demand_materialization_id':'H01-DMAT-'+'F'*24,'demand_materialization_sha256':'5'*64},
      'queue_identity':{'queue_item_id':'H01-SVGQ-CAND-0000001','queue_position':1,'source_candidate_id':'CAND-0000001','canonical_name':'shopping bag','idempotency_key':'6'*64,'source_tier':'pass','suitability':'lexname=noun.artifact','dispatch_eligible':True,'gates':{'rights':'PASS','feasibility':'PASS'},'production':{'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'}},
      'selection':{'batch_position':1,'selection_reason':'EVIDENCE_RANKED' if ranked else 'SOURCE_ORDER_FALLBACK','priority_rank':1 if ranked else None,'priority_score':0.525 if ranked else None,'priority_components':{'demand':0.50625 if ranked else None,'confidence':0.6 if ranked else None,'competition_opportunity':None,'evidence_ids':[eid] if ranked else [],'weights':{'demand':0.6,'competition_opportunity':0.25,'confidence':0.15}}},
      'demand':{'signal_state':'PARTIAL' if ranked else 'NO_EVIDENCE','rank_state':'RANKED' if ranked else 'UNRANKED','rank_score':0.50625 if ranked else None,'confidence':'MEDIUM' if ranked else 'NONE','evidence_refs':evidence,'contributions':[{'connector_id':'123rf_trending_search_v1','evidence_id':eid,'tier':'MARKETPLACE_POPULAR_QUERY','match_type':'TERM_EXACT','freshness':'FRESH','source_confidence':'MEDIUM','contribution':0.50625}] if ranked else []},
      'commercial_basis':{'basis_mode':mode,'source_tiers':tiers,'demand_specific_claim_allowed':ranked,'buyer_scope':'Generic stock-marketplace asset buyer demand is supported; no industry, demographic, or named buyer segment is asserted.' if ranked else 'No demand-evidence-specific buyer segment may be asserted for this fallback noun.','use_case_scope':'Prioritize a reusable standalone editable vector of the exact noun for marketplace stock composition and downstream layout reuse.' if ranked else 'Use only baseline standalone editable-vector utility; do not claim evidence-specific commercial demand.'},
      'phase0_guard':{'standalone_noun_only':True,'human_context':None,'family_hypotheses':[],'longtail':None,'object_human_cross_join':False},
      'authority':{'production_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}
    }


def test_marketplace_intent_compiles_to_valid_v3_with_hash_bound_evidence():
    i=intent(); bp=build_blueprint_v3(i); C.validate_blueprint(bp)
    assert bp['schema']=='die.h01.svg-blueprint.v3'
    assert bp['commercial_evidence']['intent_id']==i['intent_id']
    assert bp['commercial_evidence']['production_intent_sha256']==sha256_value(i)
    assert bp['commercial_evidence']['basis_mode']=='MARKETPLACE_DEMAND_EVIDENCE'
    assert 'shopping bag' in bp['commercial']['primary_use_case']
    assert 'marketplace demand evidence' in bp['commercial']['stock_suitability']
    assert bp['commercial_evidence']['source_tiers']==['MARKETPLACE_POPULAR_QUERY']


def test_fallback_blueprint_is_explicitly_non_demand_specific():
    i=intent(mode='FALLBACK_NO_DEMAND_EVIDENCE',ranked=False); bp=build_blueprint_v3(i); C.validate_blueprint(bp)
    assert bp['commercial_evidence']['evidence_refs']==[]
    assert bp['commercial_evidence']['demand_rank_state']=='UNRANKED'
    assert 'no market-demand claim is made' in bp['commercial']['stock_suitability']
    assert 'no demand-evidence-specific buyer segment' in bp['commercial']['buyer_value']


def test_same_intent_yields_byte_stable_blueprint_and_master():
    i=intent(); a=build_blueprint_v3(i); b=build_blueprint_v3(json.loads(json.dumps(i)))
    assert a==b and sha256_value(a)==sha256_value(b)
    ma=C.compile_master_instruction(a); mb=C.compile_master_instruction(b)
    assert ma==mb and ma['master_instruction_sha256']==mb['master_instruction_sha256']


def test_evidence_hash_change_changes_blueprint_hash_but_not_noun_identity():
    a=intent(); b=json.loads(json.dumps(a)); b['demand']['evidence_refs'][0]['evidence_sha256']='9'*64
    ba=build_blueprint_v3(a); bb=build_blueprint_v3(b)
    assert ba['subject']['canonical_name']==bb['subject']['canonical_name']=='shopping bag'
    assert sha256_value(ba)!=sha256_value(bb)
    assert ba['commercial_evidence']['production_intent_sha256']!=bb['commercial_evidence']['production_intent_sha256']


def test_master_and_provider_prompt_keep_lineage_bound_but_do_not_leak_evidence_ids():
    i=intent(); bp=build_blueprint_v3(i); master=C.compile_master_instruction(bp); prompt=C.compile_provider_prompt(blueprint=bp,master=master,provider_profile='GEMINI_WEB')
    eid=i['demand']['evidence_refs'][0]['evidence_id']
    assert master['blueprint_sha256']==sha256_value(bp)
    assert eid not in prompt['prompt']
    assert 'shopping bag' in prompt['prompt'].casefold()
    assert prompt['semantic_omission_count']==0


def test_phase0_guard_and_queue_gates_fail_closed():
    i=intent(); i['phase0_guard']['human_context']={'id':'HCTX-X'}
    try: build_blueprint_v3(i)
    except Exception as exc: assert 'E_PHASE0_GUARD' in str(exc)
    else: raise AssertionError('context leak accepted')
    j=intent(); j['queue_identity']['gates']['rights']='FAIL'
    try: build_blueprint_v3(j)
    except Exception as exc: assert 'E_QUEUE_GATES' in str(exc)
    else: raise AssertionError('failed rights accepted')


def test_h01_108_blueprint_runtime_accepts_explicit_intent_manifest_and_emits_v3():
    i=intent(); item={'batch_position':1,'queue_item_id':i['queue_identity']['queue_item_id'],'source_candidate_id':i['queue_identity']['source_candidate_id'],'canonical_name':i['queue_identity']['canonical_name'],'suitability':i['queue_identity']['suitability']}
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); ip=td/'intent.json'; ip.write_text(json.dumps(i)); im=td/'intent-manifest.json'; im.write_text(json.dumps({'intents':[{'batch_position':1,'queue_item_id':item['queue_item_id'],'intent_id':i['intent_id'],'path':str(ip)}]})); dm=td/'daily.json'; dm.write_text(json.dumps({'items':[item]})); out=td/'out'
        subprocess.run([sys.executable,str(H01/'engineering/h01_108_blueprint.py'),'--manifest',str(dm),'--position','1','--provider','gemini','--out-dir',str(out),'--intent-manifest',str(im)],check=True,capture_output=True,text=True)
        bp=json.loads((out/'blueprint.json').read_text()); saved=json.loads((out/'production-intent.json').read_text())
        assert bp['schema']=='die.h01.svg-blueprint.v3'
        assert saved['intent_id']==i['intent_id']
        assert (out/'master-instruction.json').is_file() and (out/'provider-prompt.json').is_file()
