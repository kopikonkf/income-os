import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company/company-os/die-h01'
sys.path.insert(0,str(H01/'lib'))
from commercial_blueprint_v3 import sha256_value


def intent():
    return {
      'schema':'die.h01.phase0-production-intent.v1','intent_id':'H01-P0INT-'+'C'*24,'phase':'PHASE_0_STANDALONE_NOUN','day_key':'2026-09-14','cycle_id':'H01-DCYCLE-'+'D'*24,'selection_id':'H01-DAILY-'+'E'*24,
      'lineage':{'queue_row_sha256':'1'*64,'selector_item_sha256':'2'*64,'selector_manifest_sha256':'3'*64,'demand_record_sha256':'4'*64,'demand_materialization_id':'H01-DMAT-'+'F'*24,'demand_materialization_sha256':'5'*64},
      'queue_identity':{'queue_item_id':'H01-SVGQ-CAND-0000001','queue_position':1,'source_candidate_id':'CAND-0000001','canonical_name':'shopping bag','idempotency_key':'6'*64,'source_tier':'pass','suitability':'lexname=noun.artifact','dispatch_eligible':True,'gates':{'rights':'PASS','feasibility':'PASS'},'production':{'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'}},
      'selection':{'batch_position':1,'selection_reason':'SOURCE_ORDER_FALLBACK','priority_rank':None,'priority_score':None,'priority_components':{'demand':None,'confidence':None,'competition_opportunity':None,'evidence_ids':[],'weights':{'demand':0.6,'competition_opportunity':0.25,'confidence':0.15}}},
      'demand':{'signal_state':'NO_EVIDENCE','rank_state':'UNRANKED','rank_score':None,'confidence':'NONE','evidence_refs':[],'contributions':[]},
      'commercial_basis':{'basis_mode':'FALLBACK_NO_DEMAND_EVIDENCE','source_tiers':[],'demand_specific_claim_allowed':False,'buyer_scope':'No demand-evidence-specific buyer segment may be asserted for this fallback noun.','use_case_scope':'Use only baseline standalone editable-vector utility; do not claim evidence-specific commercial demand.'},
      'phase0_guard':{'standalone_noun_only':True,'human_context':None,'family_hypotheses':[],'longtail':None,'object_human_cross_join':False},
      'authority':{'production_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}
    }


def test_runtime_rejects_intent_changed_after_manifest_freeze():
    original=intent(); frozen_sha=sha256_value(original); changed=json.loads(json.dumps(original)); changed['commercial_basis']['buyer_scope']='changed after freeze'
    item={'batch_position':1,'queue_item_id':changed['queue_identity']['queue_item_id'],'source_candidate_id':changed['queue_identity']['source_candidate_id'],'canonical_name':changed['queue_identity']['canonical_name'],'suitability':changed['queue_identity']['suitability']}
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); ip=td/'intent.json'; ip.write_text(json.dumps(changed)); im=td/'intent-manifest.json'; im.write_text(json.dumps({'intents':[{'batch_position':1,'queue_item_id':item['queue_item_id'],'intent_id':changed['intent_id'],'intent_sha256':frozen_sha,'path':str(ip)}]})); dm=td/'daily.json'; dm.write_text(json.dumps({'items':[item]})); out=td/'out'
        cp=subprocess.run([sys.executable,str(H01/'engineering/h01_108_blueprint.py'),'--manifest',str(dm),'--position','1','--provider','gemini','--out-dir',str(out),'--intent-manifest',str(im)],capture_output=True,text=True)
        assert cp.returncode != 0
        assert 'E_PRODUCTION_INTENT_IDENTITY' in (cp.stdout+cp.stderr)


def test_generation_callers_forward_intent_manifest_flag():
    for name in ['h01_108_run_one.py','h01_108_generation_cycle.py','h01_108_autonomous_supervisor.py']:
        text=(H01/'engineering'/name).read_text()
        assert "--intent-manifest" in text
