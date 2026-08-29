#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, importlib.util, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
BOUNDARY=ROOT/'BLUEPRINT_COMPILER_BOUNDARY_V1.json'
VALIDATOR=ROOT/'validate_blueprint_authoring.py'

class CompileBoundaryError(RuntimeError): pass

def _load_validator():
    spec=importlib.util.spec_from_file_location('oe005b_author_validator',VALIDATOR)
    if spec is None or spec.loader is None: raise CompileBoundaryError('E_VALIDATOR_LOAD')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def sha(payload:Any)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def prepare(artifact:dict[str,Any], *, governed_result:dict[str,Any], worth_making:dict[str,Any], executive_review:dict[str,Any], longtail_candidate:dict[str,Any], as_of:str) -> dict[str,Any]:
    validator=_load_validator(); errors=validator.validate(artifact,governed_result=governed_result,worth_making=worth_making,executive_review=executive_review,longtail_candidate=longtail_candidate,as_of=as_of)
    if errors: raise CompileBoundaryError('E_AUTHOR_ARTIFACT_INVALID:'+errors[0])
    boundary=json.loads(BOUNDARY.read_text(encoding='utf-8'))
    semantics={'family':artifact['family'],'buyer':artifact['buyer'],'product_expression':artifact['product_expression'],'visual_spec':artifact['visual_spec'],'master_prompt':artifact['production']['master_prompt'],'negative_constraints':artifact['production']['negative_constraints'],'semantic_variation_plan':artifact['production']['semantic_variation_plan'],'platform_strategy':artifact['platform_strategy'],'metadata_direction':artifact['metadata_direction'],'qa_falsification':artifact['qa_falsification'],'economics':artifact['economics']}
    return {'schema':'die.division001.blueprint-compile-input-boundary.v1','blueprint_id':artifact['blueprint_id'],'author_artifact_sha256':sha(artifact),'author_principal_id':artifact['principal']['principal_id'],'repository_sha':artifact['snapshot']['repository_sha'],'compiler_role':boundary['compiler_role'],'semantic_content_mutated':False,'semantic_field_hashes':{k:sha(v) for k,v in semantics.items()},'authored_semantics':semantics,'upstream':artifact['upstream'],'production_authority_granted':False,'final_compiler_task':'OE-005D'}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('artifact'); ap.add_argument('--governed-result',required=True); ap.add_argument('--worth-making',required=True); ap.add_argument('--executive-review',required=True); ap.add_argument('--longtail-candidate',required=True); ap.add_argument('--as-of',required=True); args=ap.parse_args()
    try:
        art=json.loads(Path(args.artifact).read_text()); out=prepare(art,governed_result=json.loads(Path(args.governed_result).read_text()),worth_making=json.loads(Path(args.worth_making).read_text()),executive_review=json.loads(Path(args.executive_review).read_text()),longtail_candidate=json.loads(Path(args.longtail_candidate).read_text()),as_of=args.as_of); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0
    except Exception as exc: print(json.dumps({'schema':'die.division001.blueprint-compile-input-boundary.v1','status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())