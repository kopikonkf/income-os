#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,re,subprocess,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
PYTHON='/opt/die/factory-asset/venv/bin/python';SCHED='/opt/die/h01/bin/h01-brave-scheduler'
PROVIDERS=('claude','chatgpt','qwen','gemini','manus','copilot')
TERMINAL_OUTPUT_MISMATCH={'PROVIDER_OUTPUT_WRONG_MODALITY_RASTER'}

def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def slug(s):return s.replace(' ','-')

def semantic_master_valid(w:Path)->bool:
 g=load(w/'generation-complete.receipt.json');v=load(w/'final/h01-103-validation.json')
 return g.get('status')=='GENERATION_COMPLETE' and v.get('status')=='PASS' and g.get('canonical_svg_sha256')==v.get('canonical_svg_sha256')

def generated(root,item):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-"
 return any(semantic_master_valid(w) for w in root.glob(prefix+'*'))

def next_attempt_id(root,item,provider):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{provider}-a";vals=[]
 for w in root.glob(prefix+'*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:vals.append(int(m.group(1)))
 return max(vals,default=0)+1

def next_global_attempt_id(root,item):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-";vals=[]
 for w in root.glob(prefix+'*-a*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:vals.append(int(m.group(1)))
 return max(vals,default=0)+1

def workspaces(root,item,provider):
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{provider}-a";out=[]
 for w in root.glob(prefix+'*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:out.append((int(m.group(1)),w))
 return [w for _,w in sorted(out)]

def committed_attempt_count(root,item,provider):
 count=0
 for w in workspaces(root,item,provider):
  d=load(w/'provider-dispatch.receipt.json');o=load(w/'provider-observation.json');ce=o.get('dispatch_commit_evidence') or {}
  if d.get('status')=='COMMITTED' or o.get('status')=='SUCCEEDED' or ce.get('committed') is True:count+=1
 return count

def recover_local_output(root,item,provider):
 for w in reversed(workspaces(root,item,provider)):
  if semantic_master_valid(w):return False
  obs=load(w/'provider-observation.json')
  if obs.get('status')!='SUCCEEDED':continue
  src=w/'provider-output.svg'
  if not src.is_file():src=w/'raw-provider-response.txt'
  if not src.is_file():continue
  lease=load(w/'scheduler-lease.sanitized.json');m=re.search(r'-a(\d+)$',w.name);attempt=int(m.group(1))
  job=f"H01-108-P{item['batch_position']:03d}-{item['source_candidate_id']}-A{attempt}"
  kind='FILE' if obs.get('source_kind')=='PROVIDER_FILE_DOWNLOAD' else 'TEXT'
  cap=subprocess.run([PYTHON,str(H01/'engineering/h01_108_capture.py'),'--workspace',str(w),'--provider',provider,'--source-kind',kind,'--source',str(src),'--job-id',job,'--profile-id',lease.get('profile_id','h01-web-p001'),'--udd-id',lease.get('udd_id','h01-web-s01')],text=True,capture_output=True)
  if cap.returncode==0:
   fin=subprocess.run([PYTHON,str(H01/'engineering/h01_108_technical_finalize.py'),'--workspace',str(w)],text=True,capture_output=True)
  else:fin=None
  ok=cap.returncode==0 and fin is not None and fin.returncode==0
  atomic_json(w/'local-output-recovery.receipt.json',{'schema':'die.h01.h01-108-local-output-recovery.v2','status':'SUCCEEDED' if ok else 'FAILED','provider':provider,'attempt':attempt,'source':str(src),'provider_generation_dispatched':False,'capture_stdout':cap.stdout[-800:],'capture_stderr':cap.stderr[-800:],'finalize_stdout':fin.stdout[-800:] if fin else '', 'finalize_stderr':fin.stderr[-800:] if fin else ''})
  return ok
 return False

def committed_pending(root,item,provider):
 for w in reversed(workspaces(root,item,provider)):
  if semantic_master_valid(w):return None
  d=load(w/'provider-dispatch.receipt.json');o=load(w/'provider-observation.json');ce=o.get('dispatch_commit_evidence') or {}
  committed=d.get('status')=='COMMITTED' or o.get('status')=='SUCCEEDED' or ce.get('committed') is True
  if committed:return {'workspace':str(w),'conversation_url':d.get('conversation_url') or ce.get('url') or o.get('conversation_url'),'prompt_sha256':d.get('prompt_sha256') or o.get('prompt_sha256'),'provider':provider,'legacy_commit_evidence':d.get('status')!='COMMITTED','semantic_master_valid':False}
 return None

def terminal_output_mismatch(root,item,provider):
 pending=committed_pending(root,item,provider)
 if not pending:return None
 w=Path(pending['workspace']);r=load(w/'committed-output-recovery.receipt.json')
 if r.get('status') not in TERMINAL_OUTPUT_MISMATCH:return None
 if r.get('do_not_acquire_other_turn_svg') is not True:return None
 return {'workspace':str(w),'provider':provider,'status':r.get('status'),'provider_output_kind':r.get('provider_output_kind'),'next_action':r.get('next_action'),'do_not_acquire_other_turn_svg':True}

def recoverable_pending_for_item(root,item):
 for provider in PROVIDERS:
  pending=committed_pending(root,item,provider)
  if pending and not terminal_output_mismatch(root,item,provider):return pending
 return None

def terminal_mismatches_for_item(root,item):
 return {provider:m for provider in PROVIDERS if (m:=terminal_output_mismatch(root,item,provider))}

def redistribution_provider(root,item,ready_order,max_attempts,max_redistributions):
 if not item.get('adaptive_provider_redistribution_allowed'):return None
 mismatches=terminal_mismatches_for_item(root,item)
 if item['planned_provider'] not in mismatches or len(mismatches)>max_redistributions:return None
 if recoverable_pending_for_item(root,item):return None
 for provider in ready_order:
  if provider not in PROVIDERS or provider in mismatches:continue
  if committed_attempt_count(root,item,provider)>=max_attempts:continue
  return provider
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
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--poll-seconds',type=int,default=15);ap.add_argument('--max-attempts-per-item',type=int,default=12);ap.add_argument('--max-provider-redistributions-per-item',type=int,default=1);ap.add_argument('--progress-file',default='/var/lib/die/h01/runs/H01-108/autonomous-progress.json');ap.add_argument('--intent-manifest',default='');ns=ap.parse_args()
 manifest=json.loads(Path(ns.manifest).read_text());items=manifest['items'];root=Path(ns.runs_root);root.mkdir(parents=True,exist_ok=True);progress=Path(ns.progress_file);failures={}
 while True:
  for item in items:
   if not generated(root,item):recover_local_output(root,item,item['planned_provider'])
  done=[i for i in items if generated(root,i)];remaining=[i for i in items if not generated(root,i)]
  pending_committed={str(i['batch_position']):recoverable_pending_for_item(root,i) for i in remaining};pending_committed={k:v for k,v in pending_committed.items() if v}
  terminal_mismatches={str(i['batch_position']):terminal_mismatches_for_item(root,i) for i in remaining};terminal_mismatches={k:v for k,v in terminal_mismatches.items() if v}
  state={'schema':'die.h01.h01-108-autonomous-supervisor.v2','task_id':'H01-108','status':'COMPLETE_PASS' if not remaining else 'RUNNING','generated_count':len(done),'remaining_count':len(remaining),'total_count':len(items),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'current':None,'failures':failures,'committed_recovery_pending':pending_committed,'terminal_provider_output_mismatches':terminal_mismatches,'duplicate_retry_policy':'NO_AUTO_RESUBMIT_AFTER_COMMIT','adaptive_redistribution_policy':'ONE_PROVIDER_SWITCH_AFTER_PROVEN_TERMINAL_MODALITY_MISMATCH','attempt_budget_policy':'COMMITTED_PROVIDER_DISPATCHES_ONLY','generation_acceptance_boundary':'H01_103_PASS_SEMANTIC_MASTER','postproduction_dependency':'NONE','submission_authorized':False,'publication_authorized':False}
  atomic_json(progress,state);print(json.dumps(state,sort_keys=True),flush=True)
  if not remaining:return 0
  sched=scheduler_status();ready_order=list(sched.get('ready_provider_ids',[]));ready=set(ready_order);candidate=None
  for item in remaining:
   planned=item['planned_provider'];provider=planned;route='PLANNED_PROVIDER'
   if terminal_output_mismatch(root,item,planned):
    provider=redistribution_provider(root,item,ready_order,ns.max_attempts_per_item,ns.max_provider_redistributions_per_item);route='ADAPTIVE_REDISTRIBUTION_AFTER_TERMINAL_MODALITY_MISMATCH'
    if not provider:continue
   elif committed_pending(root,item,planned):continue
   if committed_attempt_count(root,item,provider)>=ns.max_attempts_per_item:continue
   if provider in ready:
    attempt=next_global_attempt_id(root,item) if route!='PLANNED_PROVIDER' else next_attempt_id(root,item,provider)
    candidate=(item,provider,attempt,route);break
  if candidate is None:
   state['status']='AWAITING_RECOVERY_OR_READY_PROVIDER';atomic_json(progress,state)
   for pending in pending_committed.values():
    w=Path(pending['workspace']);r=load(w/'committed-thread-recheck.json')
    if pending['provider']=='qwen' and 'qwen' in ready and not semantic_master_valid(w) and r.get('attempt',0)<3 and time.time()>=r.get('next_check_epoch',0):
     subprocess.run([PYTHON,str(H01/'engineering/h01_108_recover_committed.py'),'--workspace',str(w)],capture_output=True,text=True);break
   exhausted=[i for i in remaining if committed_attempt_count(root,i,i['planned_provider'])>=ns.max_attempts_per_item]
   if exhausted and len(exhausted)==len(remaining):
    state['status']='BLOCKED_MAX_ATTEMPTS';state['exhausted_positions']=[i['batch_position'] for i in exhausted];atomic_json(progress,state);print(json.dumps(state,sort_keys=True),flush=True);return 2
   time.sleep(ns.poll_seconds);continue
  item,provider,attempt,route=candidate;state['current']={'position':item['batch_position'],'noun':item['canonical_name'],'provider':provider,'planned_provider':item['planned_provider'],'provider_route':route,'attempt':attempt};atomic_json(progress,state)
  cmd=[PYTHON,str(H01/'engineering/h01_108_run_one.py'),'--manifest',ns.manifest,'--position',str(item['batch_position']),'--provider',provider,'--attempt',str(attempt)]
  if ns.intent_manifest:cmd += ['--intent-manifest',ns.intent_manifest]
  cp=subprocess.run(cmd,text=True,capture_output=True)
  key=str(item['batch_position'])
  if cp.returncode:failures[key]={'provider':provider,'attempt':attempt,'stderr':cp.stderr[-600:],'stdout':cp.stdout[-600:]}
  else:failures.pop(key,None)
  time.sleep(1)

if __name__=='__main__':raise SystemExit(main())
