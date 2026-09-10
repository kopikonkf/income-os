from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import jsonschema

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'company/factory-asset'
CTX_SCHEMA=BASE/'schemas/human-demand-context.v1.schema.json'
CATALOG=BASE/'registries/human-demand-context-foundation.v1.json'
MAX_SCAN=256
MAX_RESULTS=12
TOKEN_RE=re.compile(r'[a-z0-9]+')

class DualAtlasBridgeError(ValueError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def _tokens(v:str)->set[str]: return {x for x in TOKEN_RE.findall(str(v).casefold()) if len(x)>1}
def _canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def load_catalog()->list[dict[str,Any]]: return json.loads(CATALOG.read_text(encoding='utf-8'))['contexts']

def validate_context(ctx:dict[str,Any])->None:
    schema=json.loads(CTX_SCHEMA.read_text(encoding='utf-8'))
    errors=sorted(jsonschema.Draft202012Validator(schema).iter_errors(ctx),key=lambda e:list(e.absolute_path))
    if errors:
        e=errors[0]; where='.'.join(map(str,e.absolute_path)) or '$'; raise DualAtlasBridgeError('CONTEXT_SCHEMA_INVALID',f'{where}: {e.message}')

def validate_object(obj:dict[str,Any])->None:
    for k in ('seed_id','noun','object_class','category_path'):
        if not str(obj.get(k,'')).strip(): raise DualAtlasBridgeError('OBJECT_FIELD_REQUIRED',k)
    refs=obj.get('evidence_refs')
    if not isinstance(refs,list) or not refs: raise DualAtlasBridgeError('OBJECT_EVIDENCE_REQUIRED',obj.get('seed_id','unknown'))

def _bounded(items:Iterable[dict[str,Any]],label:str)->list[dict[str,Any]]:
    rows=list(items)
    if len(rows)>MAX_SCAN: raise DualAtlasBridgeError('BOUNDED_SCAN_EXCEEDED',f'{label}:{len(rows)}>{MAX_SCAN}')
    return rows

def _object_ctx_score(obj:dict[str,Any],ctx:dict[str,Any])->tuple[float,list[str]]:
    noun=str(obj['noun']).casefold().strip(); hints=[str(x).casefold().strip() for x in ctx['object_hints']]
    noun_t=_tokens(noun); hint_t=set().union(*[_tokens(x) for x in hints])
    reasons=[]; score=0.0
    if noun in hints: score+=0.65; reasons.append('EXACT_OBJECT_HINT')
    else:
        overlap=len(noun_t & hint_t)/max(1,len(noun_t | hint_t))
        if overlap>0: score+=min(0.40,0.40*overlap); reasons.append('OBJECT_HINT_TOKEN_OVERLAP')
    context_text=' '.join(str(ctx[k]) for k in ('activity','place','problem','industry','commercial_intent','use_case')).casefold()
    class_tokens=_tokens(obj.get('object_class','')) | _tokens(obj.get('category_path',''))
    ctx_tokens=_tokens(context_text)
    if class_tokens & ctx_tokens: score+=0.15; reasons.append('CLASS_CONTEXT_COHERENCE')
    noun_overlap=noun_t & ctx_tokens
    if noun_overlap: score+=0.10; reasons.append('NOUN_CONTEXT_COHERENCE')
    if ctx['evidence']['label']=='OBSERVED_SIGNAL': score+=0.10; reasons.append('OBSERVED_SIGNAL_LABEL')
    return min(1.0,score),reasons

def _result(direction:str,anchor:dict[str,Any],candidates:list[dict[str,Any]],considered:int)->dict[str,Any]:
    return {
      'schema':'die.factory-asset.dual-atlas-context-bridge.v1','direction':direction,'anchor':anchor,
      'considered_count':considered,'result_count':len(candidates),'max_scan':MAX_SCAN,'max_results':MAX_RESULTS,
      'policy':{'cartesian_enumeration':False,'bounded_retrieval_required':True,'inherited_demand_allowed':False,'authority_effect':'NONE','production_authorized':False,'provider_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False},
      'candidates':candidates,
    }

def supply_first(obj:dict[str,Any],contexts:Iterable[dict[str,Any]],*,limit:int=8)->dict[str,Any]:
    validate_object(obj); rows=_bounded(contexts,'contexts')
    if not 1<=limit<=MAX_RESULTS: raise DualAtlasBridgeError('LIMIT_INVALID',str(limit))
    ranked=[]
    for ctx in rows:
        validate_context(ctx); score,reasons=_object_ctx_score(obj,ctx)
        if not reasons or score<=0: continue
        ranked.append({'context_id':ctx['context_id'],'coherence_score':round(score,6),'coherence_reasons':reasons,'human':ctx['human'],'activity':ctx['activity'],'problem':ctx['problem'],'industry':ctx['industry'],'commercial_intent':ctx['commercial_intent'],'use_case':ctx['use_case'],'evidence_label':ctx['evidence']['label'],'evidence_refs':ctx['evidence']['refs'],'hypothesis_only':True})
    ranked.sort(key=lambda x:(-x['coherence_score'],x['context_id']))
    anchor={'seed_id':obj['seed_id'],'noun':obj['noun'],'object_class':obj['object_class'],'category_path':obj['category_path'],'evidence_refs':obj['evidence_refs']}
    return _result('SUPPLY_FIRST',anchor,ranked[:limit],len(rows))

def demand_first(ctx:dict[str,Any],objects:Iterable[dict[str,Any]],*,limit:int=8)->dict[str,Any]:
    validate_context(ctx); rows=_bounded(objects,'objects')
    if not 1<=limit<=MAX_RESULTS: raise DualAtlasBridgeError('LIMIT_INVALID',str(limit))
    ranked=[]
    for obj in rows:
        validate_object(obj); score,reasons=_object_ctx_score(obj,ctx)
        if not reasons or score<=0: continue
        ranked.append({'seed_id':obj['seed_id'],'noun':obj['noun'],'object_class':obj['object_class'],'category_path':obj['category_path'],'coherence_score':round(score,6),'coherence_reasons':reasons,'object_evidence_refs':obj['evidence_refs'],'context_evidence_label':ctx['evidence']['label'],'context_evidence_refs':ctx['evidence']['refs'],'hypothesis_only':True})
    ranked.sort(key=lambda x:(-x['coherence_score'],x['seed_id']))
    anchor={k:ctx[k] for k in ('context_id','human','activity','problem','industry','commercial_intent','use_case')}
    anchor['evidence_label']=ctx['evidence']['label']; anchor['evidence_refs']=ctx['evidence']['refs']
    return _result('DEMAND_FIRST',anchor,ranked[:limit],len(rows))
