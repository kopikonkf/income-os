#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path
TASK_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$')
SHA_RE=re.compile(r'^[0-9a-f]{64}$')
DEFAULT_STATE=Path('/var/lib/die/state/muxia-dispatch')
DEFAULT_WORKSPACES=Path('/var/lib/die/workspaces')
DEFAULT_DISPATCH=Path('/opt/die/bin/die-muxia-image-dispatch')
SCHEMA='die.muxia-dispatch-request.v1'; RESULT_SCHEMA='die.muxia-dispatch-result.v1'
def csha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def atomic_json(path:Path,value:dict):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(value,indent=2)+'\n');os.chmod(tmp,0o640);os.replace(tmp,path)
def load_request(path:Path,workspaces:Path)->dict:
 v=json.loads(path.read_text())
 if set(v)!={'schema','task_id','blueprint_sha256'} or v.get('schema')!=SCHEMA:raise RuntimeError('E_REQUEST_SHAPE')
 task=str(v.get('task_id',''));bp_sha=str(v.get('blueprint_sha256',''))
 if not TASK_RE.fullmatch(task) or not SHA_RE.fullmatch(bp_sha):raise RuntimeError('E_REQUEST_FIELDS')
 if path.stem!=task:raise RuntimeError('E_REQUEST_FILENAME')
 w=(workspaces/task).resolve();root=workspaces.resolve()
 try:w.relative_to(root)
 except ValueError:raise RuntimeError('E_WORKSPACE_ESCAPE')
 lock=json.loads((w/'blueprint.lock.json').read_text())
 if lock.get('task_id')!=task or lock.get('blueprint_sha256')!=bp_sha:raise RuntimeError('E_BLUEPRINT_LOCK_DRIFT')
 return v
def process_one(req_path:Path,state:Path,workspaces:Path,dispatch:Path)->dict:
 req=load_request(req_path,workspaces);task=req['task_id'];result_path=state/'results'/f'{task}.json'
 if result_path.is_file():
  try:
   old=json.loads(result_path.read_text())
   if old.get('status')=='SUCCEEDED' and old.get('request_sha256')==csha(req):req_path.unlink(missing_ok=True);return old
  except Exception:pass
 cp=subprocess.run([str(dispatch),task],text=True,capture_output=True,timeout=740,check=False)
 if cp.returncode!=0:
  out={'schema':RESULT_SCHEMA,'task_id':task,'status':'FAILED','request_sha256':csha(req),'error':(cp.stderr or cp.stdout)[-1200:]};atomic_json(result_path,out);req_path.unlink(missing_ok=True);return out
 try:payload=json.loads(cp.stdout.strip().splitlines()[-1])
 except Exception as e:
  out={'schema':RESULT_SCHEMA,'task_id':task,'status':'FAILED','request_sha256':csha(req),'error':f'E_DISPATCH_RESULT:{type(e).__name__}'};atomic_json(result_path,out);req_path.unlink(missing_ok=True);return out
 if payload.get('status')!='SUCCEEDED' or payload.get('export_artifact_sha256')!=payload.get('sha256'):
  out={'schema':RESULT_SCHEMA,'task_id':task,'status':'FAILED','request_sha256':csha(req),'error':'E_DISPATCH_VERIFICATION'};atomic_json(result_path,out);req_path.unlink(missing_ok=True);return out
 out={'schema':RESULT_SCHEMA,'task_id':task,'status':'SUCCEEDED','request_sha256':csha(req),'dispatch':payload};atomic_json(result_path,out);req_path.unlink(missing_ok=True);return out
def loop(state:Path,workspaces:Path,dispatch:Path,once:bool)->int:
 for d in ['requests','results']:(state/d).mkdir(parents=True,exist_ok=True)
 while True:
  for p in sorted((state/'requests').glob('*.json')):
   try:r=process_one(p,state,workspaces,dispatch);print(json.dumps({'task_id':r.get('task_id'),'status':r.get('status')}),flush=True)
   except Exception as e:
    task=p.stem;atomic_json(state/'results'/f'{task}.json',{'schema':RESULT_SCHEMA,'task_id':task,'status':'FAILED','request_sha256':None,'error':f'{type(e).__name__}:{str(e)[:800]}'});p.unlink(missing_ok=True)
  if once:return 0
  time.sleep(0.5)
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--state-root',type=Path,default=DEFAULT_STATE);ap.add_argument('--workspaces',type=Path,default=DEFAULT_WORKSPACES);ap.add_argument('--dispatch',type=Path,default=DEFAULT_DISPATCH);ap.add_argument('--once',action='store_true');a=ap.parse_args();return loop(a.state_root,a.workspaces,a.dispatch,a.once)
if __name__=='__main__':raise SystemExit(main())
