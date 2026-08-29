#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
SCHEMA=ROOT/'die.division001.worth-making-attempt.v1.schema.json'

class AttemptError(RuntimeError): pass

def sha(payload:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def validate(payload:dict[str,Any], *, precheck:dict[str,Any]|None=None, division:dict[str,Any]|None=None, review:dict[str,Any]|None=None, previous:dict[str,Any]|None=None)->list[str]:
    errors=[]
    schema=json.loads(SCHEMA.read_text(encoding='utf-8'))
    for e in sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(payload),key=lambda x:list(x.absolute_path)):
        errors.append('E_SCHEMA:'+e.message)
    if errors: return errors
    mapping={
      'NO_VETO':('CLOSED_NO_VETO','BLUEPRINT'),
      'REVISE':('RETURNED_TO_DIVISION','DIVISION01'),
      'VETO_PENDING_EVIDENCE':('WAITING_EVIDENCE','EVIDENCE_COLLECTION'),
      'ESCALATE_FOUNDER':('ESCALATED_FOUNDER','FOUNDER')}
    state,owner=mapping[payload['review_outcome']]
    if payload['state']!=state: errors.append('E_STATE:outcome_state_mismatch')
    if payload['next_owner']!=owner: errors.append('E_STATE:outcome_owner_mismatch')
    if payload['review_outcome'] in {'REVISE','VETO_PENDING_EVIDENCE'} and not payload['required_actions']:
        errors.append('E_ACTIONS:required_for_return')
    if payload['review_outcome'] in {'NO_VETO','ESCALATE_FOUNDER'} and payload['review_outcome']=='NO_VETO' and payload['required_actions']:
        errors.append('E_ACTIONS:NO_VETO_requires_empty')
    if precheck is not None:
        if payload['precheck']['id']!=precheck['precheck_id'] or payload['precheck']['sha256']!=sha(precheck): errors.append('E_PRECHECK:binding')
    if division is not None:
        if payload['division_artifact']['id']!=division['artifact_id'] or payload['division_artifact']['sha256']!=sha(division): errors.append('E_DIVISION:binding')
    if review is not None:
        if payload['executive_review']['id']!=review['review_id'] or payload['executive_review']['sha256']!=sha(review): errors.append('E_REVIEW:binding')
        if payload['review_outcome']!=review['outcome']: errors.append('E_REVIEW:outcome_mismatch')
        if payload['required_actions']!=review['required_actions']: errors.append('E_REVIEW:actions_mismatch')
    pref=payload['previous_attempt']
    if payload['attempt_number']==1:
        if pref is not None: errors.append('E_PREVIOUS:first_attempt_must_be_null')
        if previous is not None: errors.append('E_PREVIOUS:unexpected_previous')
    else:
        if pref is None: errors.append('E_PREVIOUS:required')
        elif previous is None: errors.append('E_PREVIOUS:payload_required_for_validation')
        else:
            if pref['attempt_id']!=previous['attempt_id'] or pref['sha256']!=sha(previous) or pref['attempt_number']!=previous['attempt_number'] or pref['review_outcome']!=previous['review_outcome']:
                errors.append('E_PREVIOUS:binding')
            if previous['chain_id']!=payload['chain_id']: errors.append('E_PREVIOUS:chain_mismatch')
            if payload['attempt_number']!=previous['attempt_number']+1: errors.append('E_PREVIOUS:number_not_sequential')
            if previous['review_outcome'] not in {'REVISE','VETO_PENDING_EVIDENCE'}: errors.append('E_PREVIOUS:not_returnable')
            if division is not None and previous['division_artifact']['sha256']==payload['division_artifact']['sha256']:
                errors.append('E_REVISION:division_hash_must_change')
            if division is not None and previous['division_artifact']['id']==payload['division_artifact']['id']:
                errors.append('E_REVISION:division_artifact_id_must_change')
    return errors

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('attempt'); args=ap.parse_args(); p=json.loads(Path(args.attempt).read_text()); e=validate(p); print(json.dumps({'status':'PASS' if not e else 'FAIL','errors':e},indent=2)); return 0 if not e else 2
if __name__=='__main__': raise SystemExit(main())