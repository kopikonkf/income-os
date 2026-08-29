#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
DIVISION=ROOT.parent
SIGNALS=DIVISION/'opportunity-signals'
ADAPTERS=SIGNALS/'adapters'
DEMAND=DIVISION/'demand-score'
CANDIDATE_SCHEMA=ROOT/'die.division001.longtail-candidate.v1.schema.json'

class PhraseScoreError(RuntimeError): pass

def _load(name:str,path:Path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise PhraseScoreError('E_MODULE_LOAD:'+str(path))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def _mods():
    return {
      'signal_validator':_load('oe003_signal_validator',SIGNALS/'validate_signal_receipt.py'),
      'signal_registry':_load('oe003_signal_registry',SIGNALS/'signal_registry.py'),
      'demand_score':_load('oe003_demand_score',DEMAND/'score_demand.py'),
      'api':_load('oe003_api_fixture',ADAPTERS/'official_api_fixture.py'),
      'supply':_load('oe003_supply_fixture',ADAPTERS/'public_search_ui_fixture.py'),
      'buyer':_load('oe003_buyer_fixture',ADAPTERS/'buyer_intent_fixture.py'),
    }

def _validate_candidate(candidate:dict[str,Any])->None:
    import jsonschema
    schema=json.loads(CANDIDATE_SCHEMA.read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(candidate)

def _check_guard(candidate:dict[str,Any],guard_outcome:dict[str,Any])->None:
    if guard_outcome.get('candidate_id')!=candidate.get('candidate_id'): raise PhraseScoreError('E_GUARD_CANDIDATE_MISMATCH')
    if guard_outcome.get('canonical_phrase')!=candidate.get('phrase'): raise PhraseScoreError('E_GUARD_PHRASE_MISMATCH')
    if guard_outcome.get('status')!='ACCEPTED': raise PhraseScoreError('E_GUARD_NOT_ACCEPTED')

def score_from_receipts(candidate:dict[str,Any],guard_outcome:dict[str,Any],receipts:list[dict[str,Any]],hard_veto:dict[str,Any],*,registry_db:Path,evaluated_at:str)->dict[str,Any]:
    _validate_candidate(candidate); _check_guard(candidate,guard_outcome)
    m=_mods(); signal_schema=json.loads((SIGNALS/'die.division001.opportunity-signals.v1.schema.json').read_text(encoding='utf-8')); as_of=m['signal_validator'].parse_time(evaluated_at)
    if not receipts: raise PhraseScoreError('E_NO_SIGNAL_RECEIPTS')
    ids=[]
    conn=m['signal_registry'].connect(registry_db)
    try:
      for receipt in receipts:
        errors=m['signal_validator'].validate(receipt,signal_schema,as_of=as_of)
        if errors: raise PhraseScoreError('E_SIGNAL_INVALID:'+'|'.join(errors))
        subject=receipt['subject']
        if subject['kind']!='PHRASE' or subject['id']!=candidate['phrase']: raise PhraseScoreError('E_SIGNAL_SUBJECT_MISMATCH')
        if subject.get('parent_seed_id')!=candidate['parent_seed']['seed_id']: raise PhraseScoreError('E_SIGNAL_PARENT_SEED_MISMATCH')
        if subject.get('parent_candidate_id')!=candidate['candidate_id']: raise PhraseScoreError('E_SIGNAL_PARENT_CANDIDATE_MISMATCH')
        result=m['signal_registry'].ingest(conn,receipt,as_of=as_of)
        if result['status'] not in {'INSERTED','DUPLICATE'}: raise PhraseScoreError('E_SIGNAL_REGISTRY:'+result['status'])
        ids.append(receipt['signal_id'])
      queried=m['signal_registry'].query(conn,subject_id=candidate['phrase'],parent_candidate_id=candidate['candidate_id'],as_of=as_of,include_stale=False)
      accepted=[]
      for payload in queried:
        clean=dict(payload); clean.pop('registry_freshness',None); accepted.append(clean)
    finally: conn.close()
    score_input={
      'schema_version':'die.division001.demand-score-input.v1',
      'score_id':'DSCORE-'+candidate['candidate_id'].replace('LT-CAND-','LT-'),
      'subject':{'kind':'PHRASE','id':candidate['phrase'],'parent_seed_id':candidate['parent_seed']['seed_id'],'parent_candidate_id':candidate['candidate_id']},
      'evaluated_at':evaluated_at,
      'hard_veto':hard_veto,
      'evidence':[{'evidence_kind':'OPPORTUNITY_SIGNAL','receipt':x} for x in accepted],
    }
    score=m['demand_score'].score(score_input)
    return {
      'schema':'die.division001.longtail-phrase-score.v1','candidate_id':candidate['candidate_id'],'phrase':candidate['phrase'],
      'signal_registry_db_ref':str(registry_db),'signal_ids':sorted(set(ids)),'fresh_signal_count':len(accepted),'hard_veto_status':hard_veto['status'],'demand_score':score,
      'parent_score_inherited':False,
    }

def synthetic_receipts(candidate:dict[str,Any],plan:dict[str,Any])->list[dict[str,Any]]:
    required={'search_interest_index','visible_result_count','buyer_term_presence','observed_at','freshness_window_seconds'}
    missing=sorted(required-plan.keys())
    if missing: raise PhraseScoreError('E_SYNTHETIC_PLAN_MISSING:'+','.join(missing))
    m=_mods(); common={'query':candidate['phrase'],'parent_seed_id':candidate['parent_seed']['seed_id'],'parent_candidate_id':candidate['candidate_id'],'market_locale':plan.get('market_locale','en-US'),'language':plan.get('language','en'),'observed_at':plan['observed_at'],'freshness_window_seconds':plan['freshness_window_seconds']}
    demand=m['api'].adapt({**common,'source_id':'OTHER_APPROVED','source_name':'Longtail synthetic search-interest fixture','search_interest_index':plan['search_interest_index']})
    supply=m['supply'].adapt({**common,'source_id':'ADOBE_STOCK','source_name':'Longtail synthetic public-search fixture','visible_result_count':plan['visible_result_count']})
    buyer=m['buyer'].adapt({**common,'source_id':'SYNTHETIC_FIXTURE','source_name':'Longtail synthetic buyer-intent fixture','buyer_term_presence':plan['buyer_term_presence']})
    return [demand,supply,buyer]

def synthetic_canary(candidate:dict[str,Any],guard_outcome:dict[str,Any],plan:dict[str,Any],hard_veto:dict[str,Any],*,registry_db:Path,evaluated_at:str)->dict[str,Any]:
    return score_from_receipts(candidate,guard_outcome,synthetic_receipts(candidate,plan),hard_veto,registry_db=registry_db,evaluated_at=evaluated_at)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--candidate',required=True); ap.add_argument('--guard',required=True); ap.add_argument('--plan',required=True); ap.add_argument('--hard-veto',required=True); ap.add_argument('--registry-db',required=True); ap.add_argument('--evaluated-at',required=True)
    args=ap.parse_args()
    try:
      candidate=json.loads(Path(args.candidate).read_text()); guard=json.loads(Path(args.guard).read_text()); plan=json.loads(Path(args.plan).read_text()); veto=json.loads(Path(args.hard_veto).read_text())
      print(json.dumps(synthetic_canary(candidate,guard,plan,veto,registry_db=Path(args.registry_db),evaluated_at=args.evaluated_at),indent=2,ensure_ascii=False)); return 0
    except Exception as exc:
      print(json.dumps({'schema':'die.division001.longtail-phrase-score-run.v1','status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())
