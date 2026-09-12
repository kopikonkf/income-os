#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
FACTORY_PY='/opt/die/factory-asset/venv/bin/python';RIGHTS_PY='/opt/die/factory-asset-rights/venv/bin/python';SCHED='/opt/die/h01/bin/h01-brave-scheduler';NODE='/usr/local/bin/node'
ORIGIN={'claude':'https://claude.ai','chatgpt':'https://chatgpt.com','qwen':'https://chat.qwen.ai','gemini':'https://gemini.google.com','manus':'https://manus.im','copilot':'https://copilot.microsoft.com'}
TEXT={'claude','chatgpt','qwen','manus','copilot'}
TIMEOUT={'qwen':1200000,'claude':600000,'chatgpt':600000,'manus':600000,'copilot':600000,'gemini':600000}
def run(cmd,**kw):
 r=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if r.returncode: raise RuntimeError(f"E_CMD:{cmd[0]}:{r.returncode}:{(r.stderr or r.stdout)[-1200:]}")
 return r
def jrun(cmd,**kw):return json.loads(run(cmd,**kw).stdout)
def dump(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fail_result(w,job,provider,profile,udd,code):
 dump(w/'browser-job-result.json',{'schema':'die.h01.browser-job-result.v1','job_id':job,'job_kind':'H01_108_PRODUCTION','provider_id':provider,'profile_id':profile,'udd_id':udd,'terminal_state':'FAILED','completed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'error_code':code,'authority':{'provider_generation_dispatched':None,'provider_generation_dispatch_state':'UNKNOWN_AFTER_PROVIDER_DRIVER_ERROR','submission_authorized':False,'publication_authorized':False}})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--position',type=int,required=True);ap.add_argument('--provider',default='');ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--attempt',type=int,default=1);ns=ap.parse_args()
 m=json.loads(Path(ns.manifest).read_text());it=next((x for x in m['items'] if x['batch_position']==ns.position),None)
 if not it:raise SystemExit('E_POSITION')
 provider=ns.provider or it['planned_provider']
 if provider not in ORIGIN:raise SystemExit('E_PROVIDER')
 job=f"H01-108-P{ns.position:03d}-{it['source_candidate_id']}-A{ns.attempt}";w=Path(ns.runs_root)/f"{ns.position:03d}-{it['canonical_name'].replace(' ','-')}-{provider}-a{ns.attempt}"
 if (w/'asset-receipt.json').exists():
  old=json.loads((w/'asset-receipt.json').read_text());print(json.dumps({'status':'REPLAY','workspace':str(w),'receipt':old}));return
 w.mkdir(parents=True,exist_ok=False)
 lease=jrun([SCHED,'acquire','--dispatch-id',job,'--job-id',job,'--preferred-provider',provider])['lease'];lid=lease['lease_id'];token=lease['lease_token'];profile=lease['profile_id'];udd=lease['udd_id'];port=str(lease['cdp_port'])
 safe_lease={k:v for k,v in lease.items() if k!='lease_token'};dump(w/'scheduler-lease.sanitized.json',safe_lease)
 completed=False
 try:
  run([FACTORY_PY,str(H01/'engineering/h01_108_blueprint.py'),'--manifest',ns.manifest,'--position',str(ns.position),'--provider',provider,'--out-dir',str(w)])
  claim=jrun([SCHED,'claim-dispatch','--lease-id',lid,f'--lease-token={token}']);
  if claim.get('dispatch_authorized') is not True:raise RuntimeError('E_DISPATCH_NOT_AUTHORIZED')
  dump(w/'scheduler-dispatch-claim.sanitized.json',{k:v for k,v in claim.items() if k!='lease_token'})
  runtime_cmd=[NODE,str(H01/'engineering/brave_udd_runtime.mjs'),'--profile-id',profile,'--provider-id',provider,'--provider-url',ORIGIN[provider],'--job-id',job,'--mode','wait-result','--result-receipt',str(w/'browser-job-result.json'),'--runtime-receipt',str(w/'brave-runtime.receipt.json'),'--result-timeout-ms',str(TIMEOUT[provider]+120000)]
  runtime=subprocess.Popen(runtime_cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  time.sleep(2)
  try:
   if provider in TEXT:
    src=w/'raw-provider-response.txt';obs=w/'provider-observation.json';driver=[NODE,str(H01/'engineering/provider_text_svg_cdp_canary.mjs'),'--provider',provider,'--cdp-port',port,'--prompt-file',str(w/'prompt.txt'),'--response-file',str(src),'--observation-file',str(obs),'--timeout-ms',str(TIMEOUT[provider])];run(driver,timeout=TIMEOUT[provider]/1000+90);kind='TEXT'
   else:
    src=w/'provider-native.svg';obs=w/'provider-observation.json';dld=w/'downloads';driver=[NODE,str(H01/'engineering/provider_gemini_svg_download_cdp.mjs'),'--cdp-port',port,'--prompt-file',str(w/'prompt.txt'),'--output-file',str(src),'--download-dir',str(dld),'--observation-file',str(obs),'--timeout-ms',str(TIMEOUT[provider])];run(driver,timeout=TIMEOUT[provider]/1000+90);kind='FILE'
   run([FACTORY_PY,str(H01/'engineering/h01_108_finalize.py'),'--workspace',str(w),'--provider',provider,'--source-kind',kind,'--source',str(src),'--job-id',job,'--profile-id',profile,'--udd-id',udd],timeout=300)
  except Exception as e:
   if not (w/'browser-job-result.json').exists():fail_result(w,job,provider,profile,udd,type(e).__name__+':'+str(e)[:400])
   raise
  finally:
   try:out,err=runtime.communicate(timeout=90)
   except subprocess.TimeoutExpired:runtime.terminate();out,err=runtime.communicate(timeout=20)
   dump(w/'runtime-process.json',{'returncode':runtime.returncode,'stdout':out[-4000:],'stderr':err[-4000:]})
  if runtime.returncode!=0:raise RuntimeError('E_H01_025_RUNTIME')
  terminal=jrun([SCHED,'complete','--lease-id',lid,f'--lease-token={token}','--terminal-state','SUCCEEDED','--provider-cooldown-seconds','180']);completed=True;dump(w/'scheduler-terminal.json',terminal)
  img=w/'postproduction/preview.jpg';ish=sha_file(img);det=w/'visual-rights-detector.json';selftest=w/'visual-rights-self-test.json';scratch=w/'rights-scratch'
  run([RIGHTS_PY,str(ROOT/'company/factory-asset/bin/run_visual_rights_detector.py'),'--master',str(img),'--expected-sha256',ish,'--output',str(det),'--self-test-output',str(selftest),'--scratch',str(scratch),'--asset-type','ISOLATED_OBJECT'],timeout=600)
  r=run([FACTORY_PY,str(H01/'engineering/h01_108_rights_finalize.py'),'--workspace',str(w)],timeout=60);final=json.loads(r.stdout);dump(w/'run-one.receipt.json',{'schema':'die.h01.h01-108-run-one.v1','status':final['status'],'job_id':job,'batch_position':ns.position,'noun':it['canonical_name'],'provider_id':provider,'profile_id':profile,'udd_id':udd,'workspace':str(w),'rights':final['rights'],'provider_original_sha256':json.loads((w/'asset-receipt.json').read_text())['provider_original_sha256'],'submission_authorized':False,'publication_authorized':False});print(json.dumps({'status':final['status'],'job_id':job,'position':ns.position,'noun':it['canonical_name'],'provider':provider,'workspace':str(w),'rights':final['rights']}))
 except Exception as e:
  if not completed:
   try:jrun([SCHED,'complete','--lease-id',lid,f'--lease-token={token}','--terminal-state','FAILED','--provider-cooldown-seconds','180'])
   except Exception:pass
  dump(w/'run-one.failure.json',{'status':'FAILED','error':type(e).__name__,'detail':str(e)[:2000]});raise
if __name__=='__main__':main()
