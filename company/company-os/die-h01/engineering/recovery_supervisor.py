from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

SCHEMA='die.h01.recovery-incident.v1'
DECISION_SCHEMA='die.h01.recovery-decision.v1'
OBS_SCHEMA='die.h01.recovery-observation.v1'
WINDOW_SECONDS=3600
MAX_L1_ATTEMPTS=2

# Exact local recovery surface. Mission Control is intentionally absent: die-control owns its watchdog/recovery.
L1_SYSTEMD_ALLOWLIST={
 'h01.executive-runtime-mcp':'die-executive-runtime-mcp.service',
 'h01.division01-runtime-mcp':'die-division01-runtime-mcp.service',
 'h01.runtime-mcp-ingress':'die-runtime-mcp-cloudflared.service',
 'factory.cluster-a-broker':'die-fa121-cluster-broker.service',
 'factory.cluster-b-broker':'die-muxia-cluster-b.service',
 'factory.dispatch':'die-muxia-dispatch.service',
 'browser.cluster-a-owner':'die-muxia-cluster-a-browser.service',
 'browser.cluster-b-owner':'die-muxia-cluster-b-browser.service',
}
OBSERVE_ONLY_COMPONENTS={'mission-control','universal-mcp'}
L0_PLAYBOOKS={'L0_REOBSERVE','L0_RECONCILE_SAME_WORK','L0_WAIT_BACKOFF'}
L1_PLAYBOOK='L1_RESTART_ALLOWLISTED_SYSTEMD'
FORBIDDEN_KEYS={
 'new_task','create_task','enqueue_work','dispatch_work','task_selection','provider_selection','choose_provider',
 'seed_selection','business_schedule','cron_expression','prompt_generation','work_card_generation','scope_expansion',
 'submission_authorized','publication_authorized','spend_authorized','credential_mutation_authorized',
 'mission_lease_token','review_token','cookie','cookies','access_token','refresh_token','session_bytes',
}

class SupervisorError(ValueError):
 def __init__(self,code:str,detail:str=''):
  super().__init__(f'{code}:{detail}' if detail else code); self.code=code

def _atomic_json(path:Path,value:dict[str,Any])->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 data=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
 fd,tmp=tempfile.mkstemp(prefix=f'.{path.name}.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as h: h.write(data); h.flush(); os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

def _walk_keys(value:Any):
 if isinstance(value,dict):
  for k,v in value.items(): yield str(k); yield from _walk_keys(v)
 elif isinstance(value,list):
  for v in value: yield from _walk_keys(v)

def validate_incident(i:dict[str,Any])->None:
 if i.get('schema')!=SCHEMA: raise SupervisorError('E_INCIDENT_SCHEMA')
 for k in ('incident_id','fingerprint','level','component_id','requested_playbook','ownership','reconciliation'):
  if k not in i: raise SupervisorError('E_INCIDENT_REQUIRED',k)
 bad=sorted(set(_walk_keys(i)) & FORBIDDEN_KEYS)
 if bad: raise SupervisorError('E_HIDDEN_AUTHORITY_FIELD',','.join(bad))
 if i['level'] not in {'L0','L1','L2','L3'}: raise SupervisorError('E_LEVEL',str(i['level']))
 if not isinstance(i['ownership'],dict) or not isinstance(i['reconciliation'],dict): raise SupervisorError('E_INCIDENT_OBJECTS')

class RecoveryLedger:
 def __init__(self,path:str|Path): self.path=Path(path)
 def _load(self)->dict[str,Any]:
  if not self.path.exists(): return {'schema':'die.h01.recovery-ledger.v1','events':[]}
  v=json.loads(self.path.read_text());
  if v.get('schema')!='die.h01.recovery-ledger.v1' or not isinstance(v.get('events'),list): raise SupervisorError('E_LEDGER_CORRUPT')
  return v
 def recent(self,fingerprint:str,now:float)->list[dict[str,Any]]:
  return [e for e in self._load()['events'] if e.get('fingerprint')==fingerprint and now-float(e.get('ts',0))<=WINDOW_SECONDS]
 def append(self,event:dict[str,Any])->None:
  v=self._load(); v['events'].append(event); _atomic_json(self.path,v)

class RecoverySupervisor:
 def __init__(self,ledger:RecoveryLedger): self.ledger=ledger
 def evaluate(self,i:dict[str,Any],*,now:float|None=None)->dict[str,Any]:
  validate_incident(i); now=time.time() if now is None else now
  base={'schema':DECISION_SCHEMA,'incident_id':i['incident_id'],'fingerprint':i['fingerprint'],'component_id':i['component_id'],'level':i['level'],'requested_playbook':i['requested_playbook'],'mutation_authorized':False,'business_work_generation_authorized':False,'scheduler_authorized':False}
  if i['level'] in {'L2','L3'}: return base|{'decision':'ESCALATE','reason':'ENGINEERING_OR_FOUNDER_REQUIRED'}
  if i['level']=='L0':
   if i['requested_playbook'] not in L0_PLAYBOOKS: return base|{'decision':'ESCALATE','reason':'L0_PLAYBOOK_NOT_ALLOWLISTED'}
   return base|{'decision':'ALLOW_L0','reason':'BOUNDED_NONMUTATING_RECOVERY'}
  # L1
  if i['requested_playbook']!=L1_PLAYBOOK: return base|{'decision':'ESCALATE','reason':'L1_PLAYBOOK_NOT_ALLOWLISTED'}
  if i['component_id'] in OBSERVE_ONLY_COMPONENTS: return base|{'decision':'ESCALATE','reason':'REMOTE_CONTROL_PLANE_RECOVERY_NOT_H01_AUTHORITY'}
  service=L1_SYSTEMD_ALLOWLIST.get(i['component_id'])
  if not service: return base|{'decision':'ESCALATE','reason':'COMPONENT_NOT_ALLOWLISTED'}
  if i['ownership'].get('status')!='UNAMBIGUOUS': return base|{'decision':'QUARANTINE','reason':'OWNERSHIP_AMBIGUOUS'}
  recon=i['reconciliation']
  if bool(recon.get('ambiguous_external_side_effect')): return base|{'decision':'QUARANTINE','reason':'AMBIGUOUS_EXTERNAL_SIDE_EFFECT'}
  if bool(recon.get('active_business_work')) and not bool(recon.get('same_work_reconciled_safe')): return base|{'decision':'QUARANTINE','reason':'ACTIVE_WORK_NOT_RECONCILED'}
  if i['component_id'].startswith('browser.') and (bool(recon.get('browser_job_active')) or bool(recon.get('udd_lock_held'))): return base|{'decision':'QUARANTINE','reason':'BROWSER_OWNERSHIP_ACTIVE'}
  recent=self.ledger.recent(i['fingerprint'],now); attempts=[e for e in recent if e.get('level')=='L1' and e.get('phase')=='ATTEMPT']
  successes=[e for e in recent if e.get('level')=='L1' and e.get('phase')=='RESULT' and e.get('success') is True]
  if successes: return base|{'decision':'ESCALATE','reason':'RECURRENT_AFTER_L1_SUCCESS'}
  if len(attempts)>=MAX_L1_ATTEMPTS: return base|{'decision':'ESCALATE','reason':'L1_ATTEMPT_BUDGET_EXHAUSTED'}
  return base|{'decision':'ALLOW_L1','reason':'ALLOWLISTED_DETERMINISTIC_RECOVERY','mutation_authorized':True,'systemd_service':service,'attempts_in_window':len(attempts)}
 def execute(self,i:dict[str,Any],decision:dict[str,Any],*,runner:Callable[[list[str]],tuple[int,str,str]]|None=None,now:float|None=None)->dict[str,Any]:
  validate_incident(i); now=time.time() if now is None else now
  if decision.get('incident_id')!=i['incident_id'] or decision.get('fingerprint')!=i['fingerprint']: raise SupervisorError('E_DECISION_INCIDENT_MISMATCH')
  if decision['decision']=='ALLOW_L0':
   return {'schema':'die.h01.recovery-result.v1','incident_id':i['incident_id'],'fingerprint':i['fingerprint'],'level':'L0','playbook':i['requested_playbook'],'status':'PASS','mutation_performed':False,'business_work_generated':False}
  if decision['decision']!='ALLOW_L1' or not decision.get('mutation_authorized'): raise SupervisorError('E_EXECUTION_NOT_AUTHORIZED',decision.get('decision',''))
  service=decision.get('systemd_service')
  if L1_SYSTEMD_ALLOWLIST.get(i['component_id'])!=service: raise SupervisorError('E_SERVICE_ALLOWLIST_MISMATCH')
  runner=runner or _run
  self.ledger.append({'ts':now,'fingerprint':i['fingerprint'],'incident_id':i['incident_id'],'level':'L1','phase':'ATTEMPT','playbook':L1_PLAYBOOK,'component_id':i['component_id'],'service':service})
  rc,out,err=runner(['sudo','-n','systemctl','restart',service])
  if rc!=0:
   self.ledger.append({'ts':now,'fingerprint':i['fingerprint'],'incident_id':i['incident_id'],'level':'L1','phase':'RESULT','success':False,'error':'RESTART_FAILED'})
   raise SupervisorError('E_L1_RESTART_FAILED',(err or out)[-300:])
  rc,out,err=runner(['systemctl','is-active',service])
  ok=rc==0 and out.strip()=='active'
  self.ledger.append({'ts':now,'fingerprint':i['fingerprint'],'incident_id':i['incident_id'],'level':'L1','phase':'RESULT','success':ok,'verification':'systemctl is-active'})
  if not ok: raise SupervisorError('E_L1_VERIFY_FAILED',(err or out)[-300:])
  return {'schema':'die.h01.recovery-result.v1','incident_id':i['incident_id'],'fingerprint':i['fingerprint'],'level':'L1','playbook':L1_PLAYBOOK,'status':'PASS','mutation_performed':True,'systemd_service':service,'verification':'active','business_work_generated':False}

def _run(argv:list[str])->tuple[int,str,str]:
 p=subprocess.run(argv,text=True,capture_output=True,timeout=60,check=False); return p.returncode,p.stdout,p.stderr

def _systemctl_state(service:str)->str:
 rc,out,_=_run(['systemctl','is-active',service]); return out.strip() if rc==0 else (out.strip() or 'inactive')

def _http_status(url:str)->dict[str,Any]:
 try:
  with urllib.request.urlopen(url,timeout=4) as r: v=json.loads(r.read().decode())
  return {'reachable':True,'state':v.get('state'),'browser_owner_pid':v.get('browser_owner_pid'),'active_leases':(v.get('tab_leases') or {}).get('active_leases'),'open_pages':(v.get('tab_leases') or {}).get('open_pages')}
 except Exception as e: return {'reachable':False,'error_class':type(e).__name__}

def collect_local_observation(*,control_plane:dict[str,Any]|None=None)->dict[str,Any]:
 services={k:{'unit':v,'state':_systemctl_state(v)} for k,v in sorted(L1_SYSTEMD_ALLOWLIST.items())}
 factories={'cluster-a':_http_status('http://127.0.0.1:39121/v1/status'),'cluster-b':_http_status('http://127.0.0.1:39122/v1/status')}
 return {'schema':OBS_SCHEMA,'observed_at':int(time.time()),'control_plane':control_plane or {'source':'CONTROL_SIDE_REQUIRED','status':'NOT_SUPPLIED'},'services':services,'factories':factories,'browser_owners':{k:v for k,v in services.items() if k.startswith('browser.')},'safety':{'cookies_read':False,'tokens_read':False,'session_bytes_read':False,'business_graph_read':False,'business_work_generated':False}}

def main()->int:
 ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
 o=sub.add_parser('observe'); o.add_argument('--output')
 e=sub.add_parser('evaluate'); e.add_argument('--incident',required=True); e.add_argument('--ledger',required=True)
 x=sub.add_parser('execute'); x.add_argument('--incident',required=True); x.add_argument('--decision',required=True); x.add_argument('--ledger',required=True)
 ns=ap.parse_args()
 if ns.cmd=='observe':
  v=collect_local_observation(); text=json.dumps(v,indent=2,sort_keys=True); print(text); Path(ns.output).write_text(text+'\n') if ns.output else None; return 0
 inc=json.loads(Path(ns.incident).read_text()); sup=RecoverySupervisor(RecoveryLedger(ns.ledger))
 if ns.cmd=='evaluate': print(json.dumps(sup.evaluate(inc),indent=2,sort_keys=True)); return 0
 dec=json.loads(Path(ns.decision).read_text()); print(json.dumps(sup.execute(inc,dec),indent=2,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
