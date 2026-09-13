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
  done=[i for i in items if generated(root,i)];remaining=[i for i in items if not generated(root,i)]
  state={'schema':'die.h01.h01-108-autonomous-supervisor.v1','task_id':'H01-108','status':'RUNNING' if remaining else 'COMPLETE_PASS','generated_count':len(done),'remaining_count':len(remaining),'total_count':len(items),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'current':None,'failures':failures,'submission_authorized':False,'publication_authorized':False}
  atomic_json(progress,state);print(json.dumps(state,sort_keys=True),flush=True)
  if not remaining:return 0
  sched=scheduler_status();ready=set(sched.get('ready_provider_ids',[]));candidate=None
  for item in remaining:
   provider=item['planned_provider'];used=attempts(root,item,provider)
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
