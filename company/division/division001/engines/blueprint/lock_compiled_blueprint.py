#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT=Path(__file__).resolve().parent
COMPILER_PATH=ROOT/'compile_blueprint.py'
LOCK_SCHEMA=ROOT/'die.division001.compiled-blueprint-lock.v1.schema.json'

class LockError(RuntimeError): pass

def _load_compiler():
    spec=importlib.util.spec_from_file_location('oe005e_compiler',COMPILER_PATH)
    if spec is None or spec.loader is None: raise LockError('E_COMPILER_LOAD')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def sha(payload:Any)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def artifact_sha(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()

def lock_compiled(
    compiled_path:Path,
    *,
    blueprint:dict[str,Any], governed_result:dict[str,Any], worth_making:dict[str,Any], worth_making_review:dict[str,Any], longtail_candidate:dict[str,Any], executive_blueprint_review:dict[str,Any], as_of:str, locked_at:str,
)->dict[str,Any]:
    compiler=_load_compiler()
    if not compiled_path.exists(): raise LockError('E_COMPILED_ARTIFACT_MISSING')
    raw=compiled_path.read_bytes()
    if not raw: raise LockError('E_COMPILED_ARTIFACT_EMPTY')
    try: compiled=json.loads(raw.decode('utf-8'))
    except Exception as exc: raise LockError('E_COMPILED_ARTIFACT_JSON:'+str(exc)) from exc
    expected=compiler.compile_blueprint(blueprint,governed_result=governed_result,worth_making=worth_making,worth_making_review=worth_making_review,longtail_candidate=longtail_candidate,executive_blueprint_review=executive_blueprint_review,as_of=as_of)
    canonical=compiler.canonical_bytes(expected)
    if raw!=canonical: raise LockError('E_COMPILED_ARTIFACT_NOT_CANONICAL_OR_TAMPERED')
    if compiled!=expected: raise LockError('E_COMPILED_ARTIFACT_REPLAY_MISMATCH')
    digest=artifact_sha(raw)
    lock_id='BPLOCK-'+digest[:20].upper()
    receipt={
      'schema_version':'die.division001.compiled-blueprint-lock.v1','lock_id':lock_id,'blueprint_id':compiled['blueprint_id'],'repository_sha':compiled['repository_sha'],'locked_at':locked_at,
      'compiled_artifact':{'schema_version':compiled['schema_version'],'sha256':digest,'bytes':len(raw),'canonical_json':True},
      'compiler':{'compiler_id':compiled['compiler']['compiler_id'],'version':compiled['compiler']['version'],'capability_profile_sha256':compiled['compiler']['capability_profile_sha256']},
      'provenance':{'author_artifact_sha256':compiled['author_artifact']['sha256'],'executive_review_sha256':compiled['executive_review']['sha256'],'governed_worth_making_sha256':compiled['governed_worth_making']['sha256'],'compile_boundary_sha256':compiled['compile_boundary']['sha256']},
      'semantic_hashes':compiled['semantic_hashes'],'capability_plan_sha256':sha(compiled['capability_plan']),'integrity_status':'LOCKED',
      'founder_gate':{'eligible_for_exact_hash_authorization':True,'exact_compiled_blueprint_sha256':digest,'authorization_granted':False},
      'production_authority_granted':False}
    schema=json.loads(LOCK_SCHEMA.read_text(encoding='utf-8'))
    errors=sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(receipt),key=lambda e:list(e.absolute_path))
    if errors: raise LockError('E_LOCK_SCHEMA:'+errors[0].message)
    return receipt

def verify_lock(compiled_path:Path, receipt:dict[str,Any])->list[str]:
    errors=[]
    schema=json.loads(LOCK_SCHEMA.read_text(encoding='utf-8'))
    for e in sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(receipt),key=lambda e:list(e.absolute_path)): errors.append('E_SCHEMA:'+e.message)
    if errors: return errors
    if not compiled_path.exists(): return ['E_COMPILED_ARTIFACT_MISSING']
    raw=compiled_path.read_bytes(); digest=artifact_sha(raw)
    if receipt['compiled_artifact']['sha256']!=digest: errors.append('E_HASH_LOCK:artifact_sha_mismatch')
    if receipt['compiled_artifact']['bytes']!=len(raw): errors.append('E_HASH_LOCK:byte_count_mismatch')
    if receipt['founder_gate']['exact_compiled_blueprint_sha256']!=digest: errors.append('E_HASH_LOCK:founder_hash_mismatch')
    expected_lock='BPLOCK-'+digest[:20].upper()
    if receipt['lock_id']!=expected_lock: errors.append('E_HASH_LOCK:lock_id_mismatch')
    try:
        parsed=json.loads(raw.decode('utf-8'))
        compiler=_load_compiler()
        if raw!=compiler.canonical_bytes(parsed): errors.append('E_HASH_LOCK:artifact_not_canonical')
        if receipt['capability_plan_sha256']!=sha(parsed['capability_plan']): errors.append('E_HASH_LOCK:capability_plan_mismatch')
        if receipt['semantic_hashes']!=parsed['semantic_hashes']: errors.append('E_HASH_LOCK:semantic_hashes_mismatch')
    except Exception as exc: errors.append('E_HASH_LOCK:artifact_parse:'+str(exc))
    return errors

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('compiled'); ap.add_argument('--blueprint',required=True); ap.add_argument('--governed-result',required=True); ap.add_argument('--worth-making',required=True); ap.add_argument('--worth-making-review',required=True); ap.add_argument('--longtail-candidate',required=True); ap.add_argument('--executive-blueprint-review',required=True); ap.add_argument('--as-of',required=True); ap.add_argument('--locked-at',required=True); ap.add_argument('--output',required=True); args=ap.parse_args()
    try:
        load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
        r=lock_compiled(Path(args.compiled),blueprint=load(args.blueprint),governed_result=load(args.governed_result),worth_making=load(args.worth_making),worth_making_review=load(args.worth_making_review),longtail_candidate=load(args.longtail_candidate),executive_blueprint_review=load(args.executive_blueprint_review),as_of=args.as_of,locked_at=args.locked_at)
        Path(args.output).write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n'); print(json.dumps({'status':'PASS','lock_id':r['lock_id'],'compiled_blueprint_sha256':r['compiled_artifact']['sha256'],'production_authority_granted':False},indent=2)); return 0
    except Exception as exc: print(json.dumps({'status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())