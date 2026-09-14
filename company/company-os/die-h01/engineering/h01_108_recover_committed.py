#!/usr/bin/env python3
"""Acquire an already-committed Qwen answer under a scheduler lease; never dispatch a prompt."""
import argparse,hashlib,json,subprocess,time,uuid
from pathlib import Path
from h01_108_autonomous_supervisor import atomic_json,load
E=Path(__file__).resolve().parent
S='/opt/die/h01/bin/h01-brave-scheduler';NODE='/usr/local/bin/node';PY='/opt/die/factory-asset/venv/bin/python'
def call(args):return json.loads(subprocess.check_output(args,text=True))
def recover(w):
 d=load(w/'provider-dispatch.receipt.json');p=w/'prompt.txt'
 if load(w/'generation-complete.receipt.json').get('status')=='GENERATION_COMPLETE':return 0
 if d.get('status')!='COMMITTED' or d.get('provider')!='qwen':return 4
 raw=p.read_bytes();hashes={hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.strip()).hexdigest()}
 if d.get('prompt_sha256') not in hashes:raise ValueError('E_DISPATCH_PROMPT_HASH')
 from urllib.parse import urlparse
 url=d.get('conversation_url','');u=urlparse(url)
 if u.scheme!='https' or u.netloc!='chat.qwen.ai' or not u.path.startswith('/c/'):raise ValueError('E_RECOVERY_THREAD_URL')
 old=load(w/'committed-thread-recheck.json');attempt=old.get('attempt',0)+1
 if attempt>3 or time.time()<old.get('next_check_epoch',0):return 4
 job='H01-108-RECOVERY-'+uuid.uuid4().hex[:16]
 lease=call([S,'acquire','--dispatch-id',job,'--job-id',job,'--preferred-provider','qwen'])['lease']
 dest=w/'recovery'/job;dest.mkdir(parents=True)
 state={'schema':'die.h01.committed-thread-recheck.v2','status':'COMMITTED_AWAITING_ACQUISITION','attempt':attempt,'next_check_epoch':time.time()+900,'provider_generation_dispatched':False,'conversation_url':url,'evidence_dir':str(dest)}
 atomic_json(w/'committed-thread-recheck.json',state)
 runtime=None;success=False
 try:
  with (dest/'runtime.log').open('w') as log:
   runtime=subprocess.Popen([NODE,str(E/'brave_udd_runtime.mjs'),'--profile-id',lease['profile_id'],'--provider-id','qwen','--provider-url',url,'--job-id',job,'--mode','wait-result','--result-receipt',str(dest/'result.json'),'--runtime-receipt',str(dest/'runtime.json'),'--result-timeout-ms','420000'],stdout=log,stderr=log)
   time.sleep(8)
   cp=subprocess.run([NODE,str(E/'provider_svg_playwright_strategy.mjs'),'--provider','qwen','--cdp-port',str(lease['cdp_port']),'--prompt-file',str(p),'--output-file',str(dest/'provider-output.svg'),'--observation-file',str(dest/'observation.json'),'--dispatch-receipt',str(w/'provider-dispatch.receipt.json'),'--recheck-url',url,'--timeout-ms','300000'],capture_output=True,text=True,timeout=350)
   atomic_json(dest/'driver.json',{'returncode':cp.returncode,'stderr':cp.stderr[-2000:]})
   if cp.returncode:raise RuntimeError('E_RECHECK_DRIVER:'+cp.stderr[-500:])
   import xml.etree.ElementTree as ET
   ET.fromstring((dest/'provider-output.svg').read_bytes())
   it=load(w/'batch-item.json');a=int(w.name.rsplit('-a',1)[1]);original_job=f"H01-108-P{it['batch_position']:03d}-{it['source_candidate_id']}-A{a}"
   atomic_json(dest/'prior-browser-job-result.json',load(w/'browser-job-result.json'))
   cap=subprocess.run([PY,str(E/'h01_108_capture.py'),'--workspace',str(w),'--provider','qwen','--source-kind','TEXT','--source',str(dest/'provider-output.svg'),'--job-id',original_job,'--profile-id',lease['profile_id'],'--udd-id',lease['udd_id']],capture_output=True,text=True,timeout=120)
   if cap.returncode:raise RuntimeError('E_RECOVERY_CAPTURE:'+cap.stderr[-500:])
   fin=subprocess.run([PY,str(E/'h01_108_technical_finalize.py'),'--workspace',str(w)],capture_output=True,text=True,timeout=180)
   if fin.returncode:raise RuntimeError('E_RECOVERY_TECHNICAL_FINALIZE:'+fin.stderr[-500:])
   success=True;state['status']='GENERATION_COMPLETE'
 except Exception as exc:
  state['error']=str(exc)[:1000]
 finally:
  atomic_json(dest/'result.json',{'job_id':job,'provider_id':'qwen','profile_id':lease['profile_id'],'terminal_state':'SUCCEEDED' if success else 'FAILED','authority':{'provider_generation_dispatched':False}})
  if runtime:
   try:runtime.wait(timeout=40)
   except subprocess.TimeoutExpired:state['runtime_cleanup_pending']=True
  rr=load(dest/'runtime.json')
  if rr.get('status')=='PASS':call([S,'complete','--lease-id',lease['lease_id'],'--lease-token='+lease['lease_token'],'--terminal-state','SUCCEEDED' if success else 'FAILED','--provider-cooldown-seconds','0'])
  else:state['runtime_cleanup_pending']=True
  state['updated_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());atomic_json(w/'committed-thread-recheck.json',state)
 print(json.dumps(state));return 0 if success else 3
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();raise SystemExit(recover(Path(ns.workspace)))
