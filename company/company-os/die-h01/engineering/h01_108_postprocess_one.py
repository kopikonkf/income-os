#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,hashlib,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
FACTORY_PY='/opt/die/factory-asset/venv/bin/python';RIGHTS_PY='/opt/die/factory-asset-rights/venv/bin/python'
def run(cmd,**kw):
 r=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if r.returncode: raise RuntimeError(f"E_CMD:{cmd[0]}:{r.returncode}:{(r.stderr or r.stdout)[-1600:]}")
 return r
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def load_json(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();w=Path(ns.workspace)
 existing=load_json(w/'asset-receipt.json') if (w/'asset-receipt.json').exists() else {}
 if existing.get('status') in {'ACCEPTED_SEMANTIC_MASTER','BLOCKED_RIGHTS'}:
  print(json.dumps({'status':'REPLAY_TERMINAL_POSTPRODUCTION','workspace':str(w),'asset_status':existing['status'],'rights':existing.get('rights')}));return 0
 created=json.loads((w/'artifact-created.receipt.json').read_text()) if (w/'artifact-created.receipt.json').exists() else None
 if not created:
  # Backfill pre-split successful generation workspaces from durable browser result + provider original.
  br=json.loads((w/'browser-job-result.json').read_text()); final=w/'final/provider-original.svg'
  if br.get('terminal_state')!='SUCCEEDED' or not final.exists(): raise SystemExit('E_ARTIFACT_CREATED_NOT_PROVEN')
  created={'schema':'die.h01.h01-108-artifact-created.v1','task_id':'H01-108','status':'ARTIFACT_CREATED','job_id':br['job_id'],'batch_position':json.loads((w/'batch-item.json').read_text())['batch_position'],'noun':json.loads((w/'batch-item.json').read_text())['canonical_name'],'provider_id':br['provider_id'],'profile_id':br['profile_id'],'udd_id':br['udd_id'],'provider_original_path':str(final),'provider_original_sha256':sha_file(final),'provider_original_bytes':final.stat().st_size,'classification':br.get('classification'),'semantic_asset_id':br.get('semantic_asset_id'),'created_at':br.get('completed_at'),'postproduction_state':'PENDING','submission_authorized':False,'publication_authorized':False};dump(w/'artifact-created.receipt.json',created)
 kind='PROVIDER_ORIGINAL';src=Path(created['provider_original_path'])
 if src.resolve()!=(w/'final/provider-original.svg').resolve():raise SystemExit('E_PROVIDER_ORIGINAL_HANDOFF_PATH')
 state={'schema':'die.h01.h01-108-postproduction-state.v1','status':'RUNNING','workspace':str(w),'job_id':created['job_id'],'provider_id':created['provider_id'],'provider_original_sha256':created['provider_original_sha256'],'stage':'TECHNICAL_POSTPRODUCTION','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())};dump(w/'postproduction-state.json',state)
 try:
  run([FACTORY_PY,str(H01/'engineering/h01_108_finalize.py'),'--workspace',str(w),'--provider',created['provider_id'],'--source-kind',kind,'--source',str(src),'--job-id',created['job_id'],'--profile-id',created['profile_id'],'--udd-id',created['udd_id']],timeout=300)
  state.update({'stage':'RIGHTS_QA','updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state)
  img=w/'postproduction/preview.jpg';det=w/'visual-rights-detector.json';selftest=w/'visual-rights-self-test.json';scratch=w/'rights-scratch'
  run([RIGHTS_PY,str(ROOT/'company/factory-asset/bin/run_visual_rights_detector.py'),'--master',str(img),'--expected-sha256',sha_file(img),'--output',str(det),'--self-test-output',str(selftest),'--scratch',str(scratch),'--asset-type','ISOLATED_OBJECT'],timeout=600)
  out=json.loads(run([FACTORY_PY,str(H01/'engineering/h01_108_rights_finalize.py'),'--workspace',str(w)],timeout=60).stdout)
  state.update({'status':'PARKED_FOUNDER_QC' if out['status']=='ACCEPTED_SEMANTIC_MASTER' else 'PARKED_RIGHTS_BLOCK','stage':'POSTPRODUCTION_TERMINAL','rights':out['rights'],'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state);print(json.dumps(state))
 except Exception as e:
  state.update({'status':'PARKED_POSTPRODUCTION_RETRY','stage':state['stage'],'error':type(e).__name__,'detail':str(e)[:2000],'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())});dump(w/'postproduction-state.json',state);dump(w/'postproduction-failure.json',state);print(json.dumps(state));return 3
 return 0
if __name__=='__main__':raise SystemExit(main())
