#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,hashlib,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
FACTORY_PY='/opt/die/factory-asset/venv/bin/python';RIGHTS_PY='/opt/die/factory-asset-rights/venv/bin/python'
TERMINAL_RIGHTS={'PASS':'PASS','REVIEW_REQUIRED':'REVIEW_REQUIRED','BLOCK':'BLOCKED_RIGHTS'}

def run(cmd,**kw):
 r=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if r.returncode:raise RuntimeError(f"E_CMD:{cmd[0]}:{r.returncode}:{(r.stderr or r.stdout)[-1600:]}")
 return r

def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ts():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def terminalize(w:Path,state:dict,classification:str,rights:str,*,reason:str='',detail:str='',legacy_reused:bool=False):
 rec=load(w/'asset-receipt.json')
 rec.update({'rights':rights,'rights_signal_gate':rights,'postproduction_classification':classification,'generation_status':'GENERATION_COMPLETE','generation_validity_effect':'NONE','submission_eligible':False})
 rec['status']='POSTPRODUCTION_REVIEW_REQUIRED' if classification=='REVIEW_REQUIRED' else ('BLOCKED_RIGHTS' if classification=='BLOCKED_RIGHTS' else 'POSTPRODUCTION_PASS_FOUNDER_QC_PENDING')
 dump(w/'asset-receipt.json',rec)
 if reason:
  rights_signal={'schema':'die.h01.h01-115-rights-review.v1','result':rights,'signal_gate_pass':rights=='PASS','blocking_signals':[],'review_signals':[],'generation_validity_effect':'NONE','submission_eligible':False,'reason':reason,'detail':detail[:2000],'completed_at':ts()}
  if classification=='REVIEW_REQUIRED':rights_signal['review_signals'].append({'signal':'VISUAL_RIGHTS_DETECTOR_UNAVAILABLE_OR_FAILED','detail':detail[:800]})
  dump(w/'rights-signal.json',rights_signal)
  dump(w/'rights-review-required.receipt.json',{'schema':'die.h01.h01-115-rights-review-required.v1','status':'REVIEW_REQUIRED','reason':reason,'detail':detail[:2000],'provider_generation_dispatched':False,'generation_validity_effect':'NONE','submission_eligible':False,'completed_at':ts()})
 state.update({'status':'PARKED_FOUNDER_QC' if classification in {'PASS','REVIEW_REQUIRED'} else 'PARKED_RIGHTS_BLOCK','stage':'POSTPRODUCTION_TERMINAL','postproduction_classification':classification,'rights':rights,'generation_validity_effect':'NONE','legacy_rights_reused':legacy_reused,'updated_at':ts()})
 dump(w/'postproduction-state.json',state)
 return state

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();w=Path(ns.workspace)
 existing=load(w/'asset-receipt.json')
 if existing.get('postproduction_classification') in {'PASS','REVIEW_REQUIRED','BLOCKED_RIGHTS'}:
  print(json.dumps({'status':'REPLAY_TERMINAL_POSTPRODUCTION','workspace':str(w),'classification':existing['postproduction_classification']}));return 0
 generation=load(w/'generation-complete.receipt.json');validation=load(w/'final/h01-103-validation.json')
 if generation.get('status')!='GENERATION_COMPLETE' or validation.get('status')!='PASS':raise SystemExit('E_GENERATION_COMPLETE_REQUIRED')
 original=w/'final/provider-original.svg'
 if not original.is_file() or sha_file(original)!=generation.get('provider_original_sha256'):raise SystemExit('E_GENERATION_LINEAGE_MISMATCH')
 state={'schema':'die.h01.h01-115-postproduction-state.v1','task_id':'H01-115','status':'RUNNING','workspace':str(w),'job_id':generation['job_id'],'provider_id':generation['provider_id'],'provider_original_sha256':generation['provider_original_sha256'],'generation_status':'GENERATION_COMPLETE','generation_validity_effect':'NONE','stage':'DERIVATIVES_METADATA','updated_at':ts()};dump(w/'postproduction-state.json',state)
 # Reuse a prior terminal rights decision only when it is tied to this exact canonical master and the old detector self-test passed.
 if existing.get('canonical_svg_sha256')==validation.get('canonical_svg_sha256') and existing.get('rights') in TERMINAL_RIGHTS and existing.get('visual_rights_self_test')=='PASS':
  classification=TERMINAL_RIGHTS[existing['rights']];terminalize(w,state,classification,existing['rights'],legacy_reused=True);print(json.dumps(state));return 0
 try:
  run([FACTORY_PY,str(H01/'engineering/h01_108_finalize.py'),'--workspace',str(w)],timeout=300)
  state.update({'stage':'RIGHTS_QA','updated_at':ts()});dump(w/'postproduction-state.json',state)
  img=w/'postproduction/preview.jpg';det=w/'visual-rights-detector.json';selftest=w/'visual-rights-self-test.json';scratch=w/'rights-scratch'
  run([RIGHTS_PY,str(ROOT/'company/factory-asset/bin/run_visual_rights_detector.py'),'--master',str(img),'--expected-sha256',sha_file(img),'--output',str(det),'--self-test-output',str(selftest),'--scratch',str(scratch),'--asset-type','ISOLATED_OBJECT'],timeout=600)
  out=json.loads(run([FACTORY_PY,str(H01/'engineering/h01_108_rights_finalize.py'),'--workspace',str(w)],timeout=60).stdout)
  classification=TERMINAL_RIGHTS[out['rights']]
  terminalize(w,state,classification,out['rights']);print(json.dumps(state));return 0
 except Exception as e:
  detail=str(e)[:2000]
  if state.get('stage')=='RIGHTS_QA':
   terminalize(w,state,'REVIEW_REQUIRED','REVIEW_REQUIRED',reason='RIGHTS_QA_FAILED_FAIL_CLOSED',detail=detail)
   dump(w/'postproduction-failure.json',{'schema':'die.h01.h01-115-postproduction-failure.v1','status':'TERMINAL_REVIEW_REQUIRED','stage':'RIGHTS_QA','error':type(e).__name__,'detail':detail,'provider_generation_dispatched':False,'generation_validity_effect':'NONE','updated_at':ts()})
   print(json.dumps(state));return 0
  state.update({'status':'PARKED_POSTPRODUCTION_RETRY','error':type(e).__name__,'detail':detail,'generation_validity_effect':'NONE','updated_at':ts()});dump(w/'postproduction-state.json',state);dump(w/'postproduction-failure.json',state);print(json.dumps(state));return 3

if __name__=='__main__':raise SystemExit(main())
