#!/usr/bin/env python3
from __future__ import annotations

import argparse, copy, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BUILDER=ROOT/'fixtures'/'build_governed_fixture.py'
VALIDATOR=ROOT/'validate_governed_bundle.py'
DEFAULT_CASES=ROOT/'fixtures'/'governed-canary-cases-v1.json'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
B=load('oe004f_builder_runner',BUILDER); V=load('oe004f_bundle_runner',VALIDATOR)

def build_case(mutation:str):
    if mutation=='OUTCOME_REVISE': return B.build(outcome='REVISE')
    if mutation=='OUTCOME_VETO_PENDING_EVIDENCE': return B.build(outcome='VETO_PENDING_EVIDENCE')
    bundle=B.build()
    if mutation=='NONE': return bundle
    if mutation=='STALE_DEMAND_SCORE_AT_VALIDATION': bundle['validated_at']='2026-08-31T12:40:00Z'; return bundle
    if mutation=='REMOVE_DIVISION_PRINCIPAL': bundle['division_artifact'].pop('principal',None); return bundle
    if mutation=='FORGE_DIVISION_HASH_IN_REVIEW': bundle['executive_review']['division_artifact']['sha256']='0'*64; return bundle
    if mutation=='DROP_GOVERNED_RECEIPTS_KEEP_WORKFLOW_METADATA':
        return {'bundle_id':bundle['bundle_id'],'validated_at':bundle['validated_at'],'repository_sha':bundle['repository_sha'],'workflow_metadata':{'kanban_status':'done'}}
    raise ValueError('unknown mutation:'+mutation)

def run(cases_path:Path=DEFAULT_CASES):
    spec=json.loads(cases_path.read_text(encoding='utf-8')); results=[]; ok=True
    for case in spec['cases']:
        result=V.validate_bundle(build_case(case['mutation']))
        matched=result['status']==case['expected_status'] and result['decision']==case['expected_decision']
        ok=ok and matched
        results.append({'case_id':case['id'],'matched':matched,'status':result['status'],'decision':result['decision'],'errors':result['errors']})
    return {'schema':'die.division001.worth-making-governed-canary-run.v1','status':'PASS' if ok else 'FAIL','cases':results,'production_authority_granted':False,'live_cognition_performed':False}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cases',default=str(DEFAULT_CASES)); args=ap.parse_args(); out=run(Path(args.cases)); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0 if out['status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())