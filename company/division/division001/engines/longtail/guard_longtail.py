#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import jsonschema

ROOT=Path(__file__).resolve().parent
IP_PATH=ROOT/'guardrails'/'IP_GUARDRAIL_V1.json'
SCHEMA_PATH=ROOT/'die.division001.longtail-candidate.v1.schema.json'
NEAR_DUP_REJECT=0.90
NEAR_DUP_REVIEW=0.75
MAX_PER_SEED=50

class GuardError(RuntimeError): pass

def normalize(value:str)->str:
    text=unicodedata.normalize('NFKC',value).casefold().strip()
    text=re.sub(r'[\t\r\n]+',' ',text)
    text=re.sub(r'\s+',' ',text)
    text=re.sub(r'\s+([,.;:!?])',r'\1',text)
    return text

def tokens(value:str)->set[str]: return set(re.findall(r"[a-z0-9]+",normalize(value)))
def jaccard(a:str,b:str)->float:
    sa,sb=tokens(a),tokens(b)
    if not sa or not sb: return 0.0
    return len(sa&sb)/len(sa|sb)
def _sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _ip_hits(phrase:str,policy:dict[str,Any])->list[str]:
    norm=normalize(phrase); hits=[]
    for term in policy['terms']:
        if re.search(r'(?<![a-z0-9])'+re.escape(term.casefold())+r'(?![a-z0-9])',norm): hits.append(term)
    for sym in policy['symbols']:
        if sym in phrase: hits.append(sym)
    return sorted(set(hits))

def apply(generation:dict[str,Any], *, max_per_seed:int=MAX_PER_SEED)->dict[str,Any]:
    if generation.get('schema')!='die.division001.longtail-generation.v1': raise GuardError('E_GENERATION_SCHEMA')
    if not isinstance(max_per_seed,int) or isinstance(max_per_seed,bool) or max_per_seed<1 or max_per_seed>50: raise GuardError('E_QUOTA')
    policy=json.loads(IP_PATH.read_text(encoding='utf-8'))
    kept_by_seed:dict[str,list[str]]=defaultdict(list); exact_by_seed:dict[str,set[str]]=defaultdict(set); counts=defaultdict(int); outcomes=[]
    schema=json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    for cand in generation.get('candidates',[]):
        jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(cand)
        seed_id=cand['parent_seed']['seed_id']; parent=normalize(cand['parent_seed']['canonical_name']); phrase=normalize(cand['phrase']); reasons=[]; status='ACCEPTED'
        expression=cand['product_expression']['level'] if cand.get('product_expression') else ''
        raw='|'.join([seed_id,cand['human_context']['context_id'],phrase,expression]).encode('utf-8')
        expected_id='LT-CAND-'+hashlib.sha256(raw).hexdigest()[:24].upper()
        if cand['candidate_id']!=expected_id:
            raise GuardError('E_CANDIDATE_ID_MISMATCH')
        if not cand.get('modifiers'):
            status='REJECTED'; reasons.append('NO_TYPED_MODIFIER')
        elif phrase==parent or tokens(phrase)==tokens(parent):
            status='REJECTED'; reasons.append('PARENT_REDUNDANCY')
        elif phrase in exact_by_seed[seed_id]:
            status='REJECTED'; reasons.append('EXACT_DUPLICATE')
        elif counts[seed_id]>=max_per_seed:
            status='REJECTED'; reasons.append('SEED_QUOTA_EXCEEDED')
        else:
            similarities=[(jaccard(phrase,prior),prior) for prior in kept_by_seed[seed_id]]
            best=max(similarities,default=(0.0,None),key=lambda x:x[0])
            if best[0]>=NEAR_DUP_REJECT:
                status='REJECTED'; reasons.append(f'NEAR_DUPLICATE_GE_{NEAR_DUP_REJECT:.2f}')
            elif best[0]>=NEAR_DUP_REVIEW:
                status='REVIEW'; reasons.append(f'NEAR_DUPLICATE_{NEAR_DUP_REVIEW:.2f}_{NEAR_DUP_REJECT:.2f}')
            hits=_ip_hits(phrase,policy)
            if hits and status!='REJECTED':
                status='REVIEW'; reasons.append('IP_TERM_REVIEW:'+','.join(hits))
        exact_by_seed[seed_id].add(phrase)
        if status in {'ACCEPTED','REVIEW'}:
            kept_by_seed[seed_id].append(phrase); counts[seed_id]+=1
        outcomes.append({'candidate_id':cand['candidate_id'],'seed_id':seed_id,'canonical_phrase':phrase,'status':status,'reasons':reasons or ['PASS'],'candidate':cand})
    digest=hashlib.sha256(json.dumps([(x['candidate_id'],x['status'],x['canonical_phrase'],x['reasons']) for x in outcomes],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {
      'schema':'die.division001.longtail-guard.v1','guard_receipt_id':'LTGUARD-'+digest[:24].upper(),
      'policy':{'max_per_seed':max_per_seed,'near_duplicate_reject':NEAR_DUP_REJECT,'near_duplicate_review':NEAR_DUP_REVIEW,'ip_guardrail_sha256':_sha(IP_PATH),'ip_terms_are_complete_legal_clearance':False},
      'counts':{k:sum(1 for x in outcomes if x['status']==k) for k in ['ACCEPTED','REVIEW','REJECTED']},'outcomes':outcomes
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('generation'); ap.add_argument('--max-per-seed',type=int,default=50)
    args=ap.parse_args()
    try: print(json.dumps(apply(json.loads(Path(args.generation).read_text()),max_per_seed=args.max_per_seed),indent=2,ensure_ascii=False)); return 0
    except (OSError,json.JSONDecodeError,GuardError) as exc: print(json.dumps({'schema':'die.division001.longtail-guard-run.v1','status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
