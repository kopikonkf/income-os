#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,hashlib,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
FACTORY_PY='/opt/die/factory-asset/venv/bin/python';RIGHTS_PY='/opt/die/factory-asset-rights/venv/bin/python'

def run(cmd,**kw):
 r=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if r.returncode:raise RuntimeError(f"E_CMD:{cmd[0]}:{r.returncode}:{(r.stderr or r.stdout)[-1600:]}")
 return r

def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();w=Path(ns.workspace)
 existing=load(w/'asset-receipt.json')
 if existing.get('postproduction_classification') in {'PASS','REVIEW_REQUIRED','BLOCKED_RIGHTS'}:
  print(json.dumps({'status':'REPLAY_TERMINAL_POSTPRODUCTION','workspace':str(w),'classification':existing['postproduction_classification']}));return 0
 generation=load(w/'generation-complete.receipt.json');validation=load(w/'final/h01-103-validation.json')
 if generation.get('status')!='GENERATION_COMPLETE' or validation.get('status')!='PASS':raise SystemExit('E_GENERATION_COMPLETE_REQUIRED')
 original=w/'final/provider-original.svg'
 if not original.is_file() or sha_file(original)!=generation.get('provider_original_sha256'):raise SystemExit('E_GENERATION_LINEAGE_MISMATCH')
 state={'schema':'die.h01.h01-115-postproduction-state.v1','task_id':'H01-115','status':'RUNNING','workspace':str(w),'job_id':generation['job_id'],'provider_id':generation['provider_id'],'provider_original_sha256':generation['provider_original_sha256'],'generation_status':'GENERATION_COMPLETE','generation_validity_effect':'NONE','stage':'DERIVATIVES_METADATA','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())};dump(w/'postproduction-state.json',state)
 try:
  run([FACTORY_PY,str(H01/'engineering/h01_108_finalize.py'),'--workspace',str(w)],timeout=300)
  state.update({'stage':'RIGHTS_QA','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state)
  img=w/'postproduction/preview.jpg';det=w/'visual-rights-detector.json';selftest=w/'visual-rights-self-test.json';scratch=w/'rights-scratch'
  run([RIGHTS_PY,str(ROOT/'company/factory-asset/bin/run_visual_rights_detector.py'),'--master',str(img),'--expected-sha256',sha_file(img),'--output',str(det),'--self-test-output',str(selftest),'--scratch',str(scratch),'--asset-type','ISOLATED_OBJECT'],timeout=600)
  out=json.loads(run([FACTORY_PY,str(H01/'engineering/h01_108_rights_finalize.py'),'--workspace',str(w)],timeout=60).stdout)
  classification={'PASS':'PASS','REVIEW_REQUIRED':'REVIEW_REQUIRED','BLOCK':'BLOCKED_RIGHTS'}[out['rights']]
  rec=load(w/'asset-receipt.json');rec['postproduction_classification']=classification;rec['generation_status']='GENERATION_COMPLETE';rec['generation_validity_effect']='NONE';dump(w/'asset-receipt.json',rec)
  state.update({'status':'PARKED_FOUNDER_QC' if classification in {'PASS','REVIEW_REQUIRED'} else 'PARKED_RIGHTS_BLOCK','stage':'POSTPRODUCTION_TERMINAL','postproduction_classification':classification,'rights':out['rights'],'generation_validity_effect':'NONE','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state);print(json.dumps(state));return 0
 except Exception as e:
  state.update({'status':'PARKED_POSTPRODUCTION_RETRY','error':type(e).__name__,'detail':str(e)[:2000],'generation_validity_effect':'NONE','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state);dump(w/'postproduction-failure.json',state);print(json.dumps(state));return 3

if __name__=='__main__':raise SystemExit(main())
