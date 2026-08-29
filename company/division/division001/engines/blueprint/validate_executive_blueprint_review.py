#!/usr/bin/env python3
from __future__ import annotations

import argparse, datetime as dt, hashlib, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
SCHEMA=ROOT/'die.executive.blueprint-review.v1.schema.json'
CHALLENGE_IDS={'worth_making_thesis_fidelity','family_strategy_coherence','constraint_contradiction_integrity','portfolio_overlap_differentiation','product_expression_fit','production_tests_worth_making_thesis'}

class ReviewError(RuntimeError): pass

def sha(payload:Any)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def parse_time(value:str)->dt.datetime:
    x=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if x.tzinfo is None: raise ReviewError('E_TIME_TZ')
    return x.astimezone(dt.timezone.utc)

def validate(review:dict[str,Any], *, blueprint:dict[str,Any]|None=None, compile_boundary:dict[str,Any]|None=None, governed_result:dict[str,Any]|None=None)->list[str]:
    schema=json.loads(SCHEMA.read_text(encoding='utf-8')); errors=[]
    for e in sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(review),key=lambda e:list(e.absolute_path)): errors.append('E_SCHEMA:'+e.message)
    if errors: return errors
    ids=[x['challenge_id'] for x in review['challenges']]
    if len(ids)!=len(set(ids)) or set(ids)!=CHALLENGE_IDS: errors.append('E_CHALLENGES:exact_six_required')
    assessments=[x['assessment'] for x in review['challenges']]; outcome=review['outcome']
    if outcome=='NO_VETO' and any(x in {'MATERIAL_CONCERN','UNKNOWN'} for x in assessments): errors.append('E_OUTCOME:NO_VETO_with_material_or_unknown')
    if outcome=='REVISE':
        if not any(x in {'CONCERN','MATERIAL_CONCERN'} for x in assessments): errors.append('E_OUTCOME:REVISE_requires_concern')
        if not review['required_actions']: errors.append('E_OUTCOME:REVISE_requires_actions')
    if outcome=='VETO_PENDING_EVIDENCE':
        if 'UNKNOWN' not in assessments: errors.append('E_OUTCOME:VETO_PENDING_EVIDENCE_requires_UNKNOWN')
        if not review['required_actions']: errors.append('E_OUTCOME:VETO_PENDING_EVIDENCE_requires_actions')
    if outcome=='ESCALATE_FOUNDER' and not review.get('escalation_reason'): errors.append('E_OUTCOME:ESCALATE_requires_reason')
    if outcome!='ESCALATE_FOUNDER' and review.get('escalation_reason') is not None: errors.append('E_OUTCOME:escalation_reason_only_for_escalation')
    if parse_time(review['reviewed_at'])>=parse_time(review['expires_at']): errors.append('E_TIME:review_expiry')
    if blueprint is not None:
        ref=review['blueprint_artifact']
        if ref['blueprint_id']!=blueprint.get('blueprint_id') or ref['sha256']!=sha(blueprint): errors.append('E_BLUEPRINT:binding')
        if ref['author_principal_id']!=blueprint.get('principal',{}).get('principal_id'): errors.append('E_BLUEPRINT:principal')
        if review['snapshot']['repository_sha']!=blueprint.get('snapshot',{}).get('repository_sha'): errors.append('E_REPOSITORY:blueprint_review_mismatch')
    if compile_boundary is not None:
        if review['compile_boundary']['sha256']!=sha(compile_boundary): errors.append('E_COMPILE_BOUNDARY:hash_mismatch')
        if compile_boundary.get('semantic_content_mutated') is not False: errors.append('E_COMPILE_BOUNDARY:semantic_mutation')
        if blueprint is not None and compile_boundary.get('author_artifact_sha256')!=sha(blueprint): errors.append('E_COMPILE_BOUNDARY:author_hash_mismatch')
    if governed_result is not None:
        ref=review['governed_worth_making']
        if ref['bundle_id']!=governed_result.get('bundle_id') or ref['sha256']!=sha(governed_result): errors.append('E_WORTH_MAKING:binding')
        if governed_result.get('status')!='PASS' or governed_result.get('decision')!='PROMOTABLE_TO_BLUEPRINT': errors.append('E_WORTH_MAKING:not_promotable')
    return errors

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('review'); args=ap.parse_args(); p=json.loads(Path(args.review).read_text()); e=validate(p); print(json.dumps({'schema':'die.executive.blueprint-review-validation.v1','status':'PASS' if not e else 'FAIL','review_sha256':sha(p),'errors':e},indent=2)); return 0 if not e else 2
if __name__=='__main__': raise SystemExit(main())