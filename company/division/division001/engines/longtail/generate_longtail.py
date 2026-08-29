#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema

ROOT=Path(__file__).resolve().parent
SCHEMA_PATH=ROOT/'die.division001.longtail-candidate.v1.schema.json'
ONTOLOGY_PATH=ROOT/'MODIFIER_ONTOLOGY_V1.json'

class GenerationError(RuntimeError): pass

def normalize_phrase(value:str)->str:
    text=unicodedata.normalize('NFKC',value).strip().lower()
    text=re.sub(r'\s+',' ',text)
    text=re.sub(r'\s+([,.;:!?])',r'\1',text)
    return text

def _hash_id(seed_id:str,context_id:str,phrase:str,expression:str)->str:
    raw='|'.join([seed_id,context_id,normalize_phrase(phrase),expression]).encode('utf-8')
    return 'LT-CAND-'+hashlib.sha256(raw).hexdigest()[:24].upper()

def _modifier(t:str,value:str,source:str='HUMAN_ATLAS')->dict[str,Any]:
    return {'type':t,'value':value.strip(),'source':source}

def _candidate(seed:dict[str,Any],obj_receipt:dict[str,Any],ctxrow:dict[str,Any],hctx_receipt:dict[str,Any],phrase:str,mods:list[dict[str,Any]],expression_level:str,budget:int,created_at:str)->dict[str,Any]:
    ctx=ctxrow['context']; phrase=normalize_phrase(phrase)
    expression_name={x['id']:x['name'] for x in json.loads(ONTOLOGY_PATH.read_text(encoding='utf-8'))['product_expression_levels']}[expression_level]
    cand={
      'schema_version':'die.division001.longtail-candidate.v1','candidate_id':_hash_id(seed['seed_id'],ctx['context_id'],phrase,expression_level),'phrase':phrase,'locale':'en-US',
      'parent_seed':{'seed_id':seed['seed_id'],'canonical_name':seed['canonical_name'],'object_class':seed.get('object_class'),'category_path':seed.get('category_path'),'source_db_sha256':obj_receipt['source_db']['sha256'],'retrieval_receipt_id':obj_receipt['receipt_id']},
      'human_context':{'context_id':ctx['context_id'],'registry_sha256':hctx_receipt['registry']['sha256'],'retrieval_receipt_id':hctx_receipt['receipt_id']},
      'modifiers':mods[:4],
      'product_expression':{'level':expression_level,'name':expression_name},
      'generation':{'generator_id':'division001-longtail-generator-v1','generator_version':'1.0.0','bounded_budget':budget,'legacy_expansion_dictionary_used_as_core':False},
      'evidence_state':'REQUIRES_PHRASE_LEVEL_OE001_OE002','parent_demand':{'parent_score_ref':None,'inherited_by_child':False},
      'created_at':created_at
    }
    jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding='utf-8')),format_checker=jsonschema.FormatChecker()).validate(cand)
    return cand

def generate(object_receipt:dict[str,Any], human_receipt:dict[str,Any], *, budget:int=20, expression_level:str='L0', created_at:str)->dict[str,Any]:
    if not isinstance(budget,int) or isinstance(budget,bool) or budget<1 or budget>50: raise GenerationError('E_GENERATION_BUDGET')
    if expression_level not in {'L0','L1','L2','L3','L4','L5','L6'}: raise GenerationError('E_EXPRESSION_LEVEL')
    if object_receipt.get('schema')!='die.object-atlas.seed-retrieval.v1': raise GenerationError('E_OBJECT_RECEIPT_SCHEMA')
    if human_receipt.get('schema')!='die.human-atlas.context-retrieval.v1': raise GenerationError('E_HCTX_RECEIPT_SCHEMA')
    if object_receipt.get('result_count',0)<1 or human_receipt.get('result_count',0)<1: return {'schema':'die.division001.longtail-generation.v1','status':'EMPTY','budget':budget,'generated_count':0,'candidates':[]}
    candidates=[]
    for seed in object_receipt['results']:
      for ctxrow in human_receipt['results']:
        ctx=ctxrow['context']; obj=seed['canonical_name']
        patterns=[
          (f"{obj} for {ctx['activity']}",[_modifier('use_case',ctx['activity'])]),
          (f"{obj} for {ctx['human']}",[_modifier('audience',ctx['human'])]),
          (f"{obj} for {ctx['place']}",[_modifier('place',ctx['place'])]),
          (f"{obj} for {ctx['activity']} in {ctx['place']}",[_modifier('use_case',ctx['activity']),_modifier('place',ctx['place'])]),
          (f"{obj} for {ctx['industry']}",[_modifier('industry',ctx['industry'])]),
          (f"{obj} for {ctx['problem']}",[_modifier('problem',ctx['problem'])]),
        ]
        for phrase,mods in patterns:
          candidates.append(_candidate(seed,object_receipt,ctxrow,human_receipt,phrase,mods,expression_level,budget,created_at))
          if len(candidates)>=budget: break
        if len(candidates)>=budget: break
      if len(candidates)>=budget: break
    return {'schema':'die.division001.longtail-generation.v1','status':'GENERATED','budget':budget,'generated_count':len(candidates),'object_receipt_id':object_receipt['receipt_id'],'human_context_receipt_id':human_receipt['receipt_id'],'candidates':candidates}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--objects',required=True); ap.add_argument('--contexts',required=True); ap.add_argument('--budget',type=int,default=20); ap.add_argument('--expression-level',default='L0'); ap.add_argument('--created-at',required=True)
    args=ap.parse_args()
    try: out=generate(json.loads(Path(args.objects).read_text()),json.loads(Path(args.contexts).read_text()),budget=args.budget,expression_level=args.expression_level,created_at=args.created_at); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0
    except (OSError,json.JSONDecodeError,GenerationError,jsonschema.ValidationError) as exc: print(json.dumps({'schema':'die.division001.longtail-generation-run.v1','status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
