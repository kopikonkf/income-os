#!/usr/bin/env python3
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, re
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
SCHEMA=ROOT/'die.division001.blueprint-authoring.v1.schema.json'

class BlueprintError(RuntimeError): pass

def sha(payload:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def parse_time(value:str)->dt.datetime:
    x=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if x.tzinfo is None: raise BlueprintError('E_TIME_TZ')
    return x.astimezone(dt.timezone.utc)

def _schema_errors(payload:dict[str,Any])->list[str]:
    schema=json.loads(SCHEMA.read_text(encoding='utf-8'))
    return [e.message for e in sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(payload),key=lambda e:list(e.absolute_path))]

def validate(payload:dict[str,Any], *, governed_result:dict[str,Any]|None=None, worth_making:dict[str,Any]|None=None, executive_review:dict[str,Any]|None=None, longtail_candidate:dict[str,Any]|None=None, as_of:str|None=None)->list[str]:
    errors=['E_SCHEMA:'+x for x in _schema_errors(payload)]
    if errors: return errors
    now=parse_time(as_of or payload['snapshot']['as_of'])
    if parse_time(payload['snapshot']['as_of'])>now: errors.append('E_FRESHNESS:blueprint_from_future')
    if now>=parse_time(payload['snapshot']['expires_at']): errors.append('E_FRESHNESS:blueprint_stale')
    unresolved=re.compile(r'(?i)(\bTODO\b|\bTBD\b|\bFIXME\b|<[^>]+>|\{\{[^}]+\}\})')
    semantic_strings=[payload['family']['family_thesis'],payload['family']['commercial_use_hypothesis'],payload['family']['differentiation_thesis'],payload['buyer']['job_to_be_done'],payload['buyer']['buyer_utility'],payload['production']['master_prompt'],payload['qa_falsification']['falsification_test']]
    if any(unresolved.search(x) for x in semantic_strings): errors.append('E_SEMANTICS:unresolved_placeholder')
    variations=payload['production']['semantic_variation_plan']
    ids=[x['variation_id'] for x in variations]; instructions=[x['instruction'].strip().casefold() for x in variations]
    if len(ids)!=len(set(ids)): errors.append('E_VARIATION:duplicate_id')
    if len(instructions)!=len(set(instructions)): errors.append('E_VARIATION:duplicate_instruction')
    if len(variations)>payload['production']['batch_size']: errors.append('E_VARIATION:plan_exceeds_batch_size')
    neg=[x.strip().casefold() for x in payload['production']['negative_constraints']]
    if len(neg)!=len(set(neg)): errors.append('E_NEGATIVE:duplicate_constraint')
    if set(x.strip().casefold() for x in payload['metadata_direction']['primary_keywords']) & set(x.strip().casefold() for x in payload['metadata_direction']['secondary_keywords']): errors.append('E_METADATA:primary_secondary_overlap')
    evidence={(x['kind'],x['sha256']) for x in payload['evidence']}
    required_kinds={'WORTH_MAKING','EXECUTIVE_REVIEW','GOVERNED_WORTH_MAKING','LONGTAIL_CANDIDATE'}
    if not required_kinds.issubset({x[0] for x in evidence}): errors.append('E_EVIDENCE:required_lineage_kinds_missing')
    if governed_result is not None:
        ref=payload['upstream']['governed_worth_making_result']
        if ref['id']!=governed_result.get('bundle_id') or ref['sha256']!=sha(governed_result): errors.append('E_UPSTREAM:governed_result_binding')
        if governed_result.get('status')!='PASS' or governed_result.get('decision')!='PROMOTABLE_TO_BLUEPRINT': errors.append('E_UPSTREAM:worth_making_not_promotable')
        if governed_result.get('repository_sha')!=payload['snapshot']['repository_sha']: errors.append('E_REPOSITORY:governed_blueprint_mismatch')
    if worth_making is not None:
        ref=payload['upstream']['worth_making_artifact']
        if ref['id']!=worth_making.get('artifact_id') or ref['sha256']!=sha(worth_making): errors.append('E_UPSTREAM:worth_making_binding')
        if worth_making.get('recommendation')!='VALIDATE': errors.append('E_UPSTREAM:worth_making_not_VALIDATE')
        fam=payload['family']; cand=worth_making['candidate']
        if fam['candidate_id']!=cand['candidate_id'] or fam['candidate_phrase']!=cand['phrase']: errors.append('E_DRIFT:candidate')
        if cand.get('family_id') is not None and fam['family_id']!=cand['family_id']: errors.append('E_DRIFT:family_id')
        if fam['commercial_use_hypothesis']!=worth_making['commercial_use_hypothesis']: errors.append('E_DRIFT:commercial_use_hypothesis')
        if fam['differentiation_thesis']!=worth_making['differentiation_thesis']: errors.append('E_DRIFT:differentiation_thesis')
        if payload['buyer']['job_to_be_done']!=worth_making['buyer']['job_to_be_done']: errors.append('E_DRIFT:job_to_be_done')
        if payload['buyer']['buyer_utility']!=worth_making['buyer']['buyer_utility']: errors.append('E_DRIFT:buyer_utility')
        if payload['product_expression']!=worth_making['product_expression_recommendation']: errors.append('E_DRIFT:product_expression')
    if executive_review is not None:
        ref=payload['upstream']['executive_review']
        if ref['id']!=executive_review.get('review_id') or ref['sha256']!=sha(executive_review): errors.append('E_UPSTREAM:executive_review_binding')
        if executive_review.get('outcome')!='NO_VETO': errors.append('E_UPSTREAM:executive_review_not_NO_VETO')
    if longtail_candidate is not None:
        ref=payload['upstream']['longtail_candidate']
        if ref['id']!=longtail_candidate.get('candidate_id') or ref['sha256']!=sha(longtail_candidate): errors.append('E_UPSTREAM:longtail_binding')
        if payload['family']['candidate_id']!=longtail_candidate.get('candidate_id') or payload['family']['candidate_phrase']!=longtail_candidate.get('phrase'): errors.append('E_DRIFT:longtail_candidate')
    return errors

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('artifact'); args=ap.parse_args(); p=json.loads(Path(args.artifact).read_text()); e=validate(p); print(json.dumps({'schema':'die.division001.blueprint-authoring-validation.v1','status':'PASS' if not e else 'FAIL','artifact_sha256':sha(p),'errors':e},indent=2)); return 0 if not e else 2
if __name__=='__main__': raise SystemExit(main())