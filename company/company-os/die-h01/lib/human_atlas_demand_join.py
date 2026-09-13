from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any
HERE=Path(__file__).resolve(); REPO=HERE.parents[3]
HCTX_PATH=REPO/'division/division001/engines/longtail/retrieve_human_contexts.py'
SPEC=importlib.util.spec_from_file_location('h01_human_context_retrieval',HCTX_PATH); HCTX=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; sys.modules[SPEC.name]=HCTX; SPEC.loader.exec_module(HCTX)
MAX_CONTEXTS=12
class HumanAtlasJoinError(ValueError): pass
def _canon(obj:Any)->bytes: return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def _sha(obj:Any)->str: return hashlib.sha256(_canon(obj)).hexdigest()
def join(queue_item_id:str,canonical_name:str,*,source_candidate_id:str|None=None,limit:int=5,registry_path:Path|None=None)->dict[str,Any]:
    queue_item_id=' '.join(str(queue_item_id).split()); canonical_name=' '.join(str(canonical_name).split())
    if not queue_item_id.startswith('H01-SVGQ-'): raise HumanAtlasJoinError('E_QUEUE_ITEM_ID')
    if not canonical_name: raise HumanAtlasJoinError('E_CANONICAL_NAME')
    if not isinstance(limit,int) or isinstance(limit,bool) or limit<1 or limit>MAX_CONTEXTS: raise HumanAtlasJoinError('E_CONTEXT_LIMIT')
    kwargs={}
    if registry_path is not None: kwargs['registry_path']=Path(registry_path)
    receipt=HCTX.retrieve({'object_name':canonical_name,'limit':limit},**kwargs)
    contexts=[]
    for row in receipt['results'][:limit]:
        ctx=row['context']
        contexts.append({'context_id':ctx['context_id'],'compatibility_score':float(row['compatibility_score']),'context_sha256':_sha(ctx),'human':ctx['human'],'activity':ctx['activity'],'problem':ctx['problem'],'industry':ctx['industry'],'commercial_intent':ctx['commercial_intent'],'target_buyers':list(ctx['target_buyers']),'buyer_jobs':list(ctx['buyer_jobs']),'product_expression_hints':list(ctx['product_expression_hints'])})
    seed={'queue_item_id':queue_item_id,'canonical_name':canonical_name,'source_candidate_id':source_candidate_id,'retrieval_receipt_id':receipt['receipt_id'],'context_ids':[x['context_id'] for x in contexts]}
    return {'schema':'die.h01.human-atlas-demand-context.v1','join_id':'H01-HCTXJ-'+hashlib.sha256(_canon(seed)).hexdigest()[:24].upper(),'queue_item_id':queue_item_id,'canonical_name':canonical_name,'source_candidate_id':source_candidate_id,'join_state':'CONTEXT_AVAILABLE' if contexts else 'NO_CONTEXT','retrieval':{'receipt_id':receipt['receipt_id'],'registry_sha256':receipt['registry']['sha256'],'registry_version':receipt['registry']['version'],'query':receipt['query'],'result_count':len(contexts)},'contexts':contexts,'policy':{'max_contexts':MAX_CONTEXTS,'exhaustive_cartesian':False,'market_evidence':False,'supply_first_independent':True,'rank_authority':'NONE'},'effects':{'queue_identity_effect':'NONE','object_atlas_validity_effect':'NONE','rights_effect':'NONE','feasibility_effect':'NONE','standalone_production_blocking_effect':'NONE'},'authority':{'production_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}
