import importlib.util,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company/company-os/die-h01/engineering/h01_daily_selector.py'
S=importlib.util.spec_from_file_location('h01daily',MOD);M=importlib.util.module_from_spec(S);assert S and S.loader;sys.modules[S.name]=M;S.loader.exec_module(M)

def q(i,name):return {'schema':'die.h01.svg-production-queue.v1','queue_item_id':f'H01-SVGQ-CAND-{i:07d}','queue_position':i,'idempotency_key':f'key-{i}','dispatch_eligible':True,'gates':{'feasibility':'PASS','rights':'PASS'},'source':{'id':f'CAND-{i:07d}','canonical_name':name,'source_tier':'pass','suitability':'lexname=noun.artifact','wave3_status':'eligible'}}
def demand(qid,score):return {'queue_item_id':qid,'rank_state':'RANKED','rank_score':score,'confidence':'HIGH','evidence_refs':[{'evidence_id':'SIG-'+qid}],'discoveries':{'family_hypotheses':[]}}
def connector(qid,index):return {'queue_item_id':qid,'evidence_id':'COMP-'+qid,'freshness':'FRESH','normalized_metrics':{'competition_index':index}}

def test_no_evidence_falls_back_to_source_order():
 rows=[q(1,'cat'),q(2,'book'),q(3,'chair')]
 m=M.build_manifest(rows,produced=set(),demand={},connectors={},contexts={},limit=2,providers=('gemini','qwen'),day_key='2026-09-14')
 assert [x['canonical_name'] for x in m['items']]==['cat','book']
 assert all(x['selection_reason']=='SOURCE_ORDER_FALLBACK' for x in m['items'])
 assert m['evidence']['market_evidence_blocking'] is False

def test_ranked_market_evidence_precedes_unranked():
 rows=[q(1,'cat'),q(2,'book'),q(3,'chair')];qid=rows[2]['queue_item_id']
 m=M.build_manifest(rows,produced=set(),demand={qid:demand(qid,.9)},connectors={},contexts={},limit=2,providers=('gemini',),day_key='d')
 assert m['items'][0]['canonical_name']=='chair';assert m['items'][0]['selection_reason']=='EVIDENCE_RANKED'

def test_generation_complete_produced_ids_are_excluded_regardless_of_postproduction():
 rows=[q(1,'cat'),q(2,'book')]
 with tempfile.TemporaryDirectory() as td:
  w=Path(td)/'run-a';w.mkdir();(w/'generation-complete.receipt.json').write_text(json.dumps({'status':'GENERATION_COMPLETE','h01_103_status':'PASS','queue_item_id':rows[0]['queue_item_id']}))
  (w/'asset-receipt.json').write_text(json.dumps({'rights':'BLOCK','postproduction_classification':'BLOCKED_RIGHTS'}))
  produced=M.produced_ids(Path(td));assert produced=={rows[0]['queue_item_id']}
  m=M.build_manifest(rows,produced=produced,demand={},connectors={},contexts={},limit=1,providers=('qwen',),day_key='d')
  assert m['items'][0]['canonical_name']=='book'

def test_rights_only_receipt_does_not_mark_noun_produced():
 rows=[q(1,'cat')]
 with tempfile.TemporaryDirectory() as td:
  w=Path(td)/'run-a';w.mkdir();(w/'asset-receipt.json').write_text(json.dumps({'rights':'PASS','status':'ACCEPTED_SEMANTIC_MASTER'}))
  assert M.produced_ids(Path(td))==set()

def test_selector_is_deterministic_for_same_inputs():
 rows=[q(1,'cat'),q(2,'book'),q(3,'chair')];qid=rows[1]['queue_item_id'];d={qid:demand(qid,.7)};c={qid:[connector(qid,25)]}
 a=M.build_manifest(rows,produced=set(),demand=d,connectors=c,contexts={},limit=3,providers=('gemini','qwen'),day_key='2026-09-14')
 b=M.build_manifest(rows,produced=set(),demand=d,connectors=c,contexts={},limit=3,providers=('gemini','qwen'),day_key='2026-09-14')
 assert a==b

def test_human_context_is_annotation_not_rank_authority():
 rows=[q(1,'cat'),q(2,'shopping bag')];ctx={rows[1]['queue_item_id']:{'queue_item_id':rows[1]['queue_item_id'],'context':'packing'}}
 m=M.build_manifest(rows,produced=set(),demand={},connectors={},contexts=ctx,limit=2,providers=('gemini',),day_key='d')
 assert [x['canonical_name'] for x in m['items']]==['cat','shopping bag'];assert m['items'][1]['human_context']['context']=='packing'
