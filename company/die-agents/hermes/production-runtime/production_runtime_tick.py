#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, fcntl, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from production_active_card_resolver import resolve_active_card
from production_seed_selector import select_seed
import factory_orchestration_v2 as factory_v2
WORKSPACES=Path('/var/lib/die/workspaces'); DB=Path('/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db')
HERMES='/opt/die/hermes/venv/bin/hermes'; HERMES_HOME='/var/lib/die/hermes/income-operator'
WORKER_DISPATCH=HERE/'worker_dispatch.py'; WORKER_RUNNER=Path('/srv/die/company/workers/opencode/runner.py')
UPSCALE=Path('/srv/die/bridge/income_os_bridge/asset_upscale.py'); UPSCALE_POLICY=Path('/srv/die/company/atlas/object-centric/object-asset-engine/source/scripts/postprocess/upscale-policy.v1.json')
MUXIA_QUEUE=Path('/var/lib/die/state/muxia-dispatch')
LOCK=Path('/var/lib/die/state/production-runtime/tick.lock')

def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def csha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def sha(p:Path):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def send(msg:str):
 cp=subprocess.run([HERMES,'send','--to','telegram',msg],env={**os.environ,'HERMES_HOME':HERMES_HOME},text=True,capture_output=True,check=False)
 if cp.returncode!=0:raise RuntimeError('E_TELEGRAM:'+(cp.stderr or cp.stdout)[-500:])
def write_progress(w:Path,lines:list[str]):(w/'PROGRESS.md').write_text('# '+w.name+' progress\n\n'+'\n'.join('- '+x for x in lines)+'\n')

def start_seed()->dict:
 s=select_seed(DB,WORKSPACES)
 if s['status']!='SELECTED':return {'status':'IDLE','reason':s['status']}
 seed=s['seed'];task='PROD'+seed['id'].replace('-','')
 w=WORKSPACES/task;w.mkdir(parents=True,exist_ok=False)
 fam=f"{seed['category_path']} (object_class: {seed['object_class']})"
 write_progress(w,[f"Seed: {seed['id']} ({seed['canonical_name']})",f"Family: {fam}",'State: BLUEPRINT_REQUIRED','Blueprint status: REQUIRED','Intended provider: MUXIA (chatgpt-linux-a)',f'Started: {now()}','Next action: Production cognition line authors/reviews fixed Blueprint.'])
 factory_v2.telegram_event(w,'PRODUCTION_STARTED',{'seed':seed['canonical_name'],'seed_id':seed['id'],'family':fam,'blueprint':'REQUIRED','provider':'MUXIA/chatgpt-linux-a'},send)
 return {'status':'STARTED','task_id':task,'seed':seed['canonical_name']}

def build_worker(w:Path,bp:dict,lock:dict):
 if lock.get('blueprint_sha256')!=csha(bp):raise RuntimeError('E_BLUEPRINT_LOCK_HASH')
 prod=bp.get('production',{})
 if prod.get('engine')!='MUXIA/chatgpt-linux-a':raise RuntimeError('E_ENGINE')
 job={'schema':'die.worker-job-envelope.v1','task_id':w.name,'mission_id':'M-001','executor':'opencode','goal':'Prepare bounded MUXIA image-generation handoff from the fixed Blueprint without semantic changes.','context':f"Fixed Blueprint {bp['blueprint_id']} sha256={lock['blueprint_sha256']}. Seed {bp['seed']['id']}={bp['seed']['canonical_name']}. Worker must not rewrite master_prompt.",'workspace':str(w),'constraints':{'time_budget_min':30,'allowed_paths':[str(w)],'network':'none','forbidden':['credentials','market submission','spawning workers','writes outside workspace','destructive operations']},'acceptance_criteria':[{'id':'AC-1','statement':'Pinned OpenCode executable is present and version-probed.','verify_with':'opencode-probe.json'},{'id':'AC-2','statement':'Validated MUXIA image-generation request is written inside assigned workspace.','verify_with':'muxia-job-request.json'}],'handoff':{'kind':'muxia_job','provider_id':'chatgpt','required_capability':'image.generate','profile_selector':'chatgpt-linux-a','timeout_ms':600000}}
 (w/'job.json').write_text(json.dumps(job,indent=2)+'\n')
 progress=w/'PROGRESS.md'; prior=progress.read_bytes() if progress.is_file() else None
 try:
  cp=subprocess.run(['/usr/bin/python3',str(WORKER_DISPATCH),'--job',str(w/'job.json'),'--worker-result',str(w/'result.json'),'--dispatch-receipt',str(w/'dispatch-receipt.json'),'--worker-runner',str(WORKER_RUNNER),'--workspace-root',str(WORKSPACES),'--opencode-bin','/opt/die/workers/opencode/bin/opencode','--worker-home','/var/lib/die/workers/opencode/home','--timeout-sec','120'],text=True,capture_output=True,check=False)
 finally:
  if prior is not None: progress.write_bytes(prior)
 if cp.returncode!=0:raise RuntimeError('E_WORKER:'+(cp.stderr or cp.stdout)[-800:])
 rec=json.loads((w/'dispatch-receipt.json').read_text())
 if rec.get('accepted_status')!='done':raise RuntimeError('E_WORKER_ACCEPTANCE')

def generate(w:Path)->dict:
 bp=json.loads((w/'blueprint.json').read_text());lock=json.loads((w/'blueprint.lock.json').read_text());build_worker(w,bp,lock)
 req={'schema':'die.muxia-dispatch-request.v1','task_id':w.name,'blueprint_sha256':lock['blueprint_sha256']}
 reqdir=MUXIA_QUEUE/'requests';resdir=MUXIA_QUEUE/'results';reqdir.mkdir(parents=True,exist_ok=True);resdir.mkdir(parents=True,exist_ok=True)
 reqp=reqdir/f'{w.name}.json';resp=resdir/f'{w.name}.json';expected=csha(req)
 if resp.is_file():
  try:
   old=json.loads(resp.read_text())
   if old.get('status')!='SUCCEEDED' or old.get('request_sha256')!=expected:resp.unlink()
  except Exception:resp.unlink()
 if reqp.is_file():
  old=json.loads(reqp.read_text())
  if old!=req:raise RuntimeError('E_MUXIA_QUEUE_REQUEST_DRIFT')
 else:
  tmp=reqp.with_name(reqp.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(req,indent=2)+'\n');os.replace(tmp,reqp)
 deadline=time.time()+740
 while time.time()<deadline and not resp.is_file():time.sleep(1)
 if not resp.is_file():raise RuntimeError('E_MUXIA_QUEUE_TIMEOUT')
 qres=json.loads(resp.read_text())
 if qres.get('status')!='SUCCEEDED' or qres.get('request_sha256')!=expected:raise RuntimeError('E_MUXIA:'+str(qres.get('error','queue failure'))[:1200])
 rec=qres['dispatch'];src=Path(rec['export_artifact_path'])
 if rec.get('status')!='SUCCEEDED' or not src.is_file() or sha(src)!=rec.get('export_artifact_sha256') or rec.get('export_artifact_sha256')!=rec.get('sha256'):raise RuntimeError('E_MUXIA_EXPORT_RECEIPT')
 if src.parent.resolve()!=(w/'provider').resolve():raise RuntimeError('E_MUXIA_EXPORT_PATH')
 dst=src
 seed=bp['seed'];fam=f"{seed['category_path']} (object_class: {seed['object_class']})"
 write_progress(w,[f"Seed: {seed['id']} ({seed['canonical_name']})",f"Family: {fam}",'State: ARTIFACT_CREATED',f"Blueprint status: FIXED {bp['blueprint_id']} sha256={lock['blueprint_sha256']}",'Worker status: ACCEPTED done; dispatch-receipt.json','Provider: MUXIA (chatgpt-linux-a)',f'Provider artifact: provider/{dst.name}',f'Artifact sha256: {sha(dst)}',f'Artifact bytes: {dst.stat().st_size}',f"Artifact dimensions: {rec['generated_image_observed']['width']}x{rec['generated_image_observed']['height']}",'Next action: Run bounded technical upscale/recovery, then park for Founder QC.'])
 factory_v2.telegram_event(w,'ARTIFACT_CREATED',{'seed':seed['canonical_name'],'provider':'MUXIA/chatgpt-linux-a','file':dst.name,'dimensions':f"{rec['generated_image_observed']['width']}x{rec['generated_image_observed']['height']}",'bytes':dst.stat().st_size,'sha256':sha(dst)[:12]+'...','next':'factory-v2-postproduction'},send)
 return upscale_and_park(w)

def source_for(w:Path)->Path:
 rows=list((w/'provider').glob('source-original.*'))
 if len(rows)!=1:raise RuntimeError('E_PROVIDER_SOURCE_COUNT')
 return rows[0]
def _legacy_upscale_adapter(src:Path,out:Path)->dict:
 receipt=out.parent/'legacy-upscale.receipt.json';out.parent.mkdir(parents=True,exist_ok=True)
 cp=subprocess.run(['/usr/bin/python3',str(UPSCALE),'--source',str(src),'--output',str(out),'--policy',str(UPSCALE_POLICY),'--receipt',str(receipt),'--min-width','2000','--min-height','2000','--min-megapixels','4','--rights-state','PENDING_HUMAN_REVIEW','--safety-state','PENDING_HUMAN_REVIEW'],text=True,capture_output=True,timeout=1200,check=False)
 if cp.returncode!=0:raise RuntimeError('E_UPSCALE:'+(cp.stderr or cp.stdout)[-1000:])
 ur=json.loads(receipt.read_text())
 if ur.get('status')!='PASS':raise RuntimeError('E_UPSCALE_STATUS:'+str(ur.get('status')))
 return ur

def _progress_from_v2(w:Path,result:dict)->None:
 bp=json.loads((w/'blueprint.json').read_text());lock=json.loads((w/'blueprint.lock.json').read_text());seed=bp['seed'];fam=f"{seed['category_path']} (object_class: {seed['object_class']})"
 state_name=result.get('status','POSTPROCESSING')
 if state_name=='WAITING_FOUNDER_QC': progress_state='WAITING_FOUNDER_QC';next_action='Park this card for Founder QC. Backend rights/package eligibility remains governed separately; no upload/publish authority granted.'
 elif state_name=='PACKAGE_BLOCKED': progress_state='WAITING_FOUNDER_QC';next_action='Park this card for Founder QC with backend package blocker preserved; independent production may continue.'
 else: progress_state='POSTPROCESSING';next_action='Continue durable Factory v2 postproduction.'
 rows=[f"Seed: {seed['id']} ({seed['canonical_name']})",f"Family: {fam}",f'State: {progress_state}',f"Blueprint status: FIXED {bp['blueprint_id']} sha256={lock['blueprint_sha256']}",'Provider: MUXIA (chatgpt-linux-a)',f"Factory v2 result: {state_name}"]
 if result.get('listing_path'):rows.append(f"Listing artifact: {Path(result['listing_path']).relative_to(w)}")
 if result.get('metadata'):rows.append(f"Metadata: {Path(result['metadata']).relative_to(w)}")
 if result.get('submission_fields'):rows.append(f"Submission fields: {Path(result['submission_fields']).relative_to(w)}")
 rows+=['Founder QC: PENDING',f'Next action: {next_action}'];write_progress(w,rows)

def upscale_and_park(w:Path)->dict:
 src=source_for(w)
 result=factory_v2.postprocess_raster_workspace(workspace=w,source_path=src,provider_id='chatgpt-linux-a',expected_source_sha256=sha(src),upscale_fn=_legacy_upscale_adapter,send_fn=send)
 _progress_from_v2(w,result)
 return result


def tick()->dict:
 a=resolve_active_card(WORKSPACES)
 if a['status']=='NO_ACTIVE_CARD':return start_seed()
 if a['status']=='DELEGATED_ACTIVE_CARD':return {'status':'IDLE','reason':'WAITING_COGNITION'}
 if a['status']!='CONTINUE_ACTIVE_CARD':return {'status':'IDLE','reason':a['status']}
 c=a['active_card'];w=Path(c['workspace']);state=c['state']
 if state=='BLUEPRINT_REQUIRED':return {'status':'IDLE','reason':'WAITING_COGNITION'}
 if state=='BLUEPRINT_READY':return generate(w)
 if state in {'ARTIFACT_CREATED','MASTER_VALIDATED','UPSCALE_DECIDED','DERIVATIVES_READY','TECHNICAL_QA_PASS','RIGHTS_SIGNAL_PASS_OR_REVIEW','METADATA_READY','PACKAGE_READY','POSTPROCESSING'}:return upscale_and_park(w)
 return {'status':'IDLE','reason':'UNHANDLED_STATE','state':state}

def main()->int:
 LOCK.parent.mkdir(parents=True,exist_ok=True)
 with LOCK.open('a+') as fh:
  try:fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 0
  try:r=tick();
  except Exception as e:
   try:send(f"PRODUCTION_FAILED | stage=deterministic-runtime | retryable=yes | error={type(e).__name__}:{str(e)[:500]} | next=retry same durable card; no compensating seed")
   except Exception:pass
   print(json.dumps({'status':'FAILED','error':type(e).__name__,'message':str(e)[:800]}));return 2
  if r.get('status') not in {'IDLE'}:print(json.dumps(r))
 return 0
if __name__=='__main__':raise SystemExit(main())
