#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FIXTURE=ROOT/'fixtures'/'build_blueprint_fixture.py'
COMPILER=ROOT/'compile_blueprint.py'
LOCKER=ROOT/'lock_compiled_blueprint.py'
EXPECTED=ROOT/'fixtures'/'compiler-canary-expected-v1.json'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
F=load('oe005f_canary_fixture',FIXTURE); C=load('oe005f_canary_compiler',COMPILER); L=load('oe005f_canary_locker',LOCKER)

def run(work_dir:Path)->dict:
    work_dir.mkdir(parents=True,exist_ok=True)
    review,bp,boundary,governed,wm,wreview,candidate=F.build_review()
    a=C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of='2026-08-29T13:00:00Z')
    b=C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of='2026-08-29T13:00:00Z')
    if C.canonical_bytes(a)!=C.canonical_bytes(b): raise RuntimeError('E_CANARY_NONDETERMINISTIC_COMPILE')
    path=work_dir/'compiled-blueprint.json'; digest=C.write_compiled(path,a)
    receipt=L.lock_compiled(path,blueprint=bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of='2026-08-29T13:00:00Z',locked_at='2026-08-29T13:01:00Z')
    if L.verify_lock(path,receipt): raise RuntimeError('E_CANARY_LOCK_VERIFY')
    expected=json.loads(EXPECTED.read_text(encoding='utf-8')) if EXPECTED.exists() else None
    out={'schema':'die.division001.blueprint-compiler-canary.v1','status':'PASS','compiled_blueprint_sha256':digest,'compiled_bytes':path.stat().st_size,'lock_id':receipt['lock_id'],'provider_id':a['capability_plan']['provider_id'],'required_capability':a['capability_plan']['required_capability'],'runtime_availability_claimed':a['capability_plan']['runtime_availability_claimed'],'production_authority_granted':False,'deterministic_replay':True,'lock_verify':True}
    if expected is not None:
        for k in ['compiled_blueprint_sha256','lock_id','provider_id','required_capability']:
            if out[k]!=expected[k]: raise RuntimeError('E_CANARY_EXPECTED_MISMATCH:'+k)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--work-dir',required=True); args=ap.parse_args();
    try: out=run(Path(args.work_dir)); print(json.dumps(out,indent=2)); return 0
    except Exception as exc: print(json.dumps({'schema':'die.division001.blueprint-compiler-canary.v1','status':'FAIL','error':str(exc)},indent=2)); return 2
if __name__=='__main__': raise SystemExit(main())