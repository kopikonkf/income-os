#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,re,subprocess,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
PYTHON='/opt/die/factory-asset/venv/bin/python';SCHED='/opt/die/h01/bin/h01-brave-scheduler'
def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def slug(s):return s.replace(' ','-')
def generated(root,item):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-"
 for w in root.glob(prefix+'*'):
  if load(w/'artifact-created.receipt.json').get('status')=='ARTIFACT_CREATED':return True
  b=load(w/'browser-job-result.json')
  if b.get('terminal_state')=='SUCCEEDED' and (w/'final/provider-original.svg').is_file():return True
 return False
def attempts(root,item,provider):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{provider}-a";vals=[]
 for w in root.glob(prefix+'*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:vals.append(int(m.group(1)))
 return max(vals,default=0)

def workspaces(root,item,provider):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{provider}-a"
 out=[]
 for w in root.glob(prefix+'*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:out.append((int(m.group(1)),w))
 return [w for _,w in sorted(out)]
def recover_local_output(root,item,provider):
 for w in reversed(workspaces(root,item,provider)):
  if load(w/'artifact-created.receipt.json').get('status')=='ARTIFACT_CREATED':return False
  obs=load(w/'provider-observation.json')
  if obs.get('status')!='SUCCEEDED':continue
  src=w/'provider-output.svg'
  if not src.is_file():src=w/'raw-provider-response.txt'
  if not src.is_file():continue
  lease=load(w/'scheduler-lease.sanitized.json');m=re.search(r'-a(\d+)$',w.name);attempt=int(m.group(1))
  job=f"H01-108-P{item['batch_position']:03d}-{item['source_candidate_id']}-A{attempt}"
  kind='FILE' if obs.get('source_kind')=='PROVIDER_FILE_DOWNLOAD' else 'TEXT'
  cp=subprocess.run([PYTHON,str(H01/'engineering/h01_108_capture.py'),'--workspace',str(w),'--provider',provider,'--source-kind',kind,'--source',str(src),'--job-id',job,'--profile-id',lease.get('profile_id','h01-web-p001'),'--udd-id',lease.get('udd_id','h01-web-s01')],text=True,capture_output=True)
  atomic_json(w/'local-output-recovery.receipt.json',{'schema':'die.h01.h01-108-local-output-recovery.v1','status':'SUCCEEDED' if cp.returncode==0 else 'FAILED','provider':provider,'attempt':attempt,'source':str(src),'provider_generation_dispatched':False,'stdout':cp.stdout[-800:],'stderr':cp.stderr[-800:]})
  return cp.returncode==0
 return False
def committed_pending(root,item,provider):
 for w in reversed(workspaces(root,item,provider)):
  if load(w/'artifact-created.receipt.json').get('status')=='ARTIFACT_CREATED':return None
  d=load(w/'provider-dispatch.receipt.json')
  if d.get('status')=='COMMITTED':return {'workspace':str(w),'conversation_url':d.get('conversation_url'),'prompt_sha256':d.get('prompt_sha256'),'provider':provider}
 return None

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
 fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as h:h.write(data);h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def scheduler_status():
 cp=subprocess.run([SCHED,'status'],text=True,capture_output=True)
 if cp.returncode:raise RuntimeError('E_SCHEDULER_STATUS:'+cp.stderr[-400:])
 return json.loads(cp.stdout)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--poll-seconds',type=int,default=15);ap.add_argument('--max-attempts-per-item',type=int,default=12);ap.add_argument('--progress-file',default='/var/lib/die/h01/runs/H01-108/autonomous-progress.json');ns=ap.parse_args()
 manifest=json.loads(Path(ns.manifest).read_text());items=manifest['items'];root=Path(ns.runs_root);root.mkdir(parents=True,exist_ok=True);progress=Path(ns.progress_file);failures={}
 while True:
  for item in items:
   if not generated(root,item):recover_local_output(root,item,item['planned_provider'])
  done=[i for i in items if generated(root,i)];remaining=[i for i in items if not generated(root,i)]
  pending_committed={str(i['batch_position']):committed_pending(root,i,i['planned_provider']) for i in remaining};pending_committed={k:v for k,v in pending_committed.items() if v}
  state={'schema':'die.h01.h01-108-autonomous-supervisor.v1','task_id':'H01-108','status':'RUNNING' if remaining else 'COMPLETE_PASS','generated_count':len(done),'remaining_count':len(remaining),'total_count':len(items),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'current':None,'failures':failures,'committed_recovery_pending':pending_committed,'duplicate_retry_policy':'NO_AUTO_RESUBMIT_AFTER_COMMIT','submission_authorized':False,'publication_authorized':False}
  atomic_json(progress,state);print(json.dumps(state,sort_keys=True),flush=True)
  if not remaining:return 0
  sched=scheduler_status();ready=set(sched.get('ready_provider_ids',[]));candidate=None
  for item in remaining:
   provider=item['planned_provider'];used=attempts(root,item,provider)
   if committed_pending(root,item,provider):continue
   if used>=ns.max_attempts_per_item:continue
   if provider in ready:candidate=(item,provider,used+1);break
  if candidate is None:
   exhausted=[i for i in remaining if attempts(root,i,i['planned_provider'])>=ns.max_attempts_per_item]
   if exhausted and len(exhausted)==len(remaining):
    state['status']='BLOCKED_MAX_ATTEMPTS';state['exhausted_positions']=[i['batch_position'] for i in exhausted];atomic_json(progress,state);print(json.dumps(state,sort_keys=True),flush=True);return 2
   time.sleep(ns.poll_seconds);continue
  item,provider,attempt=candidate;state['current']={'position':item['batch_position'],'noun':item['canonical_name'],'provider':provider,'attempt':attempt};atomic_json(progress,state)
  cp=subprocess.run([PYTHON,str(H01/'engineering/h01_108_run_one.py'),'--manifest',ns.manifest,'--position',str(item['batch_position']),'--attempt',str(attempt)],text=True,capture_output=True)
  key=str(item['batch_position'])
  if cp.returncode:failures[key]={'provider':provider,'attempt':attempt,'stderr':cp.stderr[-600:],'stdout':cp.stdout[-600:]}
  else:failures.pop(key,None)
  time.sleep(1)
if __name__=='__main__':raise SystemExit(main())
