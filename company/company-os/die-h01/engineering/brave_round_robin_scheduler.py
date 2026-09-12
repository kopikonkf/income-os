#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, secrets, subprocess, time
from pathlib import Path
from typing import Any

SCHEMA='die.h01.brave-round-robin-scheduler.v1'
STATE_SCHEMA='die.h01.brave-round-robin-scheduler-state.v1'
DEFAULT_MANIFEST=Path('/var/lib/die/h01/browser/fabric-manifest-v1.json')
DEFAULT_POLICY=Path('/etc/die/h01/brave/scheduler-policy-v1.json')
DEFAULT_READINESS=Path('/var/lib/die/h01/browser/profile-readiness-v1.json')
DEFAULT_STATE=Path('/var/lib/die/h01/browser/scheduler/state-v1.json')
DEFAULT_RUNTIME=Path('/run/user/1000/die-h01-brave')
TERMINAL={'SUCCEEDED','FAILED','TIMEOUT','CANCELLED','UNSUPPORTED','AMBIGUOUS','EMPTY'}

class SchedulerError(RuntimeError):
    def __init__(self,code:str,detail:str=''):
        super().__init__(f'{code}:{detail}' if detail else code); self.code=code; self.detail=detail

def readj(p:Path)->dict[str,Any]: return json.loads(p.read_text())
def atomic_write(p:Path,v:dict[str,Any])->None:
    p.parent.mkdir(parents=True,exist_ok=True); os.chmod(p.parent,0o700)
    t=p.with_name(p.name+f'.tmp.{os.getpid()}'); t.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); os.chmod(t,0o600); os.replace(t,p)

def load_manifest(p:Path)->dict[str,Any]:
    m=readj(p)
    if m.get('schema')!='die.h01.brave-fabric.host-local.v1': raise SchedulerError('E_MANIFEST_SCHEMA')
    ps=m.get('profiles') or []
    if len(ps)!=100 or m.get('topology',{}).get('udd_count')!=20 or m.get('topology',{}).get('profiles_per_udd')!=5 or m.get('topology',{}).get('max_active_per_udd')!=1: raise SchedulerError('E_MANIFEST_TOPOLOGY')
    return m

def load_policy(p:Path)->dict[str,Any]:
    v=readj(p)
    if v.get('schema')!='die.h01.brave-round-robin-policy.v1': raise SchedulerError('E_POLICY_SCHEMA')
    cap=int(v.get('global_max_live_udd_owners',0)); approved=int(v.get('founder_approved_max_live_udd_owners',0)); absolute=int(v.get('absolute_max_udd_owners',0))
    if cap<1 or approved<1 or absolute!=20 or cap>approved or approved>absolute: raise SchedulerError('E_POLICY_CAP')
    providers=v.get('providers') or []
    if not providers or len({x.get('provider_id') for x in providers})!=len(providers): raise SchedulerError('E_PROVIDER_POLICY')
    return v

def load_readiness(p:Path)->dict[str,Any]:
    v=readj(p)
    if v.get('schema')!='die.h01.brave-profile-readiness.v1': raise SchedulerError('E_READINESS_SCHEMA')
    return v

def initial_state()->dict[str,Any]:
    return {'schema':STATE_SCHEMA,'revision':1,'global_udd_cursor':-1,'profile_cursor_by_udd':{},'provider_cursor_by_udd':{},'provider_cooldown_until':{},'active_leases':{},'dispatch_ledger':{}}

def state_lock(state_path:Path):
    state_path.parent.mkdir(parents=True,exist_ok=True); os.chmod(state_path.parent,0o700)
    f=open(state_path.with_suffix(state_path.suffix+'.lock'),'a+'); os.chmod(f.name,0o600); fcntl.flock(f,fcntl.LOCK_EX); return f

def load_state(p:Path)->dict[str,Any]:
    if not p.exists(): return initial_state()
    v=readj(p)
    if v.get('schema')!=STATE_SCHEMA: raise SchedulerError('E_STATE_SCHEMA')
    return v

def release_lock(f)->None: fcntl.flock(f,fcntl.LOCK_UN); f.close()
def profile_ready(readiness:dict[str,Any],pid:str)->bool: return (readiness.get('profiles') or {}).get(pid,{}).get('state')=='READY'
def provider_ready(policy:dict[str,Any],state:dict[str,Any],provider_id:str,now:float)->bool:
    row=next((x for x in policy['providers'] if x['provider_id']==provider_id),None)
    return bool(row and row.get('state')=='READY' and float(state['provider_cooldown_until'].get(provider_id,0))<=now)

def runtime_udd_free(udd_id:str,runtime_root:Path)->bool:
    runtime_root.mkdir(parents=True,exist_ok=True)
    f=open(runtime_root/f'{udd_id}.lock','a+')
    try:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return False
        return True
    finally:
        try: fcntl.flock(f,fcntl.LOCK_UN)
        except Exception: pass
        f.close()

def live_udd_active(user_data_dir:str)->bool:
    r=subprocess.run(['ps','-eo','args='],capture_output=True,text=True,check=True)
    needle=f'--user-data-dir={user_data_dir}'
    return any(needle in x and 'brave' in x.lower() for x in r.stdout.splitlines())

def ordered_after(items:list[Any],last_index:int)->list[tuple[int,Any]]:
    if not items:return []
    return [((last_index+1+i)%len(items),items[(last_index+1+i)%len(items)]) for i in range(len(items))]

def rows_by_udd(manifest:dict[str,Any])->dict[str,list[dict[str,Any]]]:
    out:dict[str,list[dict[str,Any]]]={}
    for p in manifest['profiles']: out.setdefault(p['udd_id'],[]).append(p)
    for rows in out.values(): rows.sort(key=lambda x:x['slot'])
    return dict(sorted(out.items()))

def active_udd_ids(state:dict[str,Any])->set[str]: return {v['udd_id'] for v in state['active_leases'].values()}
def dispatch_key(raw:str)->str: return hashlib.sha256(raw.encode()).hexdigest()
def lease_public(v:dict[str,Any])->dict[str,Any]: return {k:v[k] for k in v if k!='lease_token'}

class Scheduler:
    def __init__(self,manifest:Path=DEFAULT_MANIFEST,policy:Path=DEFAULT_POLICY,readiness:Path=DEFAULT_READINESS,state:Path=DEFAULT_STATE,runtime_root:Path=DEFAULT_RUNTIME):
        self.manifest_path=Path(manifest); self.policy_path=Path(policy); self.readiness_path=Path(readiness); self.state_path=Path(state); self.runtime_root=Path(runtime_root)

    def _inputs(self): return load_manifest(self.manifest_path),load_policy(self.policy_path),load_readiness(self.readiness_path)

    def acquire(self,*,dispatch_id:str,job_id:str,preferred_provider:str|None=None,now:float|None=None)->dict[str,Any]:
        if not dispatch_id or not job_id: raise SchedulerError('E_JOB_ID')
        now=time.time() if now is None else now; key=dispatch_key(dispatch_id); lock=state_lock(self.state_path)
        try:
            m,policy,ready=self._inputs(); s=load_state(self.state_path); old=s['dispatch_ledger'].get(key)
            if old:
                if old.get('terminal_state'): return {'schema':SCHEMA,'status':'ALREADY_TERMINAL','dispatch_authorized':False,'record':old}
                lid=old.get('lease_id'); lease=s['active_leases'].get(lid)
                if lease:return {'schema':SCHEMA,'status':'REUSED','dispatch_authorized':False,'lease':lease_public(lease)}
                raise SchedulerError('E_LEDGER_ORPHAN')
            if len(s['active_leases'])>=policy['global_max_live_udd_owners']: raise SchedulerError('E_GLOBAL_ADMISSION')
            groups=rows_by_udd(m); udds=list(groups); active=active_udd_ids(s); gu=int(s.get('global_udd_cursor',-1)); chosen=None
            for ui,udd in ordered_after(udds,gu):
                if udd in active: continue
                rows=groups[udd]
                if not any(profile_ready(ready,r['profile_id']) for r in rows): continue
                if live_udd_active(rows[0]['user_data_dir']) or not runtime_udd_free(udd,self.runtime_root): continue
                chosen=(ui,udd,rows); break
            if not chosen: raise SchedulerError('E_NO_ELIGIBLE_UDD')
            ui,udd,rows=chosen; pc=int(s['profile_cursor_by_udd'].get(udd,-1)); pr=None
            for pi,row in ordered_after(rows,pc):
                if profile_ready(ready,row['profile_id']): pr=(pi,row); break
            if not pr: raise SchedulerError('E_NO_READY_PROFILE')
            pi,row=pr; providers=policy['providers']; vc=int(s['provider_cursor_by_udd'].get(udd,-1)); pv=None
            if preferred_provider:
                for vi,p in enumerate(providers):
                    if p.get('provider_id')==preferred_provider:
                        if provider_ready(policy,s,preferred_provider,now): pv=(vi,p)
                        else: raise SchedulerError('E_PROVIDER_NOT_ELIGIBLE',preferred_provider)
                        break
                if pv is None: raise SchedulerError('E_PROVIDER_UNKNOWN',preferred_provider)
            else:
                for vi,p in ordered_after(providers,vc):
                    if provider_ready(policy,s,p['provider_id'],now): pv=(vi,p); break
            if not pv: raise SchedulerError('E_NO_READY_PROVIDER')
            vi,pvrow=pv; lid=secrets.token_hex(16); token=secrets.token_urlsafe(24)
            lease={'lease_id':lid,'lease_token':token,'dispatch_key':key,'dispatch_id':dispatch_id,'job_id':job_id,'udd_id':udd,'profile_id':row['profile_id'],'profile_slot':row['slot'],'provider_id':pvrow['provider_id'],'cdp_host':row['cdp_host'],'cdp_port':row['cdp_port'],'user_data_dir':row['user_data_dir'],'profile_directory':row['profile_directory'],'state':'LEASED','dispatch_claimed':False,'acquired_epoch':now}
            s['active_leases'][lid]=lease; s['dispatch_ledger'][key]={'dispatch_id':dispatch_id,'job_id':job_id,'lease_id':lid,'terminal_state':None}
            s['global_udd_cursor']=ui; s['profile_cursor_by_udd'][udd]=pi; s['provider_cursor_by_udd'][udd]=vi; s['revision']=int(s.get('revision',0))+1; atomic_write(self.state_path,s)
            return {'schema':SCHEMA,'status':'LEASED','dispatch_authorized':False,'lease':lease}
        finally: release_lock(lock)

    def claim_dispatch(self,lease_id:str,lease_token:str)->dict[str,Any]:
        lock=state_lock(self.state_path)
        try:
            s=load_state(self.state_path); lease=s['active_leases'].get(lease_id)
            if not lease: raise SchedulerError('E_LEASE_UNKNOWN')
            if not secrets.compare_digest(str(lease.get('lease_token','')),str(lease_token)): raise SchedulerError('E_LEASE_TOKEN')
            if lease.get('dispatch_claimed'):
                return {'schema':SCHEMA,'status':'ALREADY_DISPATCHED','dispatch_authorized':False,'lease':lease_public(lease)}
            lease['dispatch_claimed']=True; lease['state']='DISPATCH_CLAIMED'; lease['dispatch_claimed_epoch']=time.time(); s['revision']+=1; atomic_write(self.state_path,s)
            return {'schema':SCHEMA,'status':'DISPATCH_CLAIMED','dispatch_authorized':True,'lease':lease_public(lease)}
        finally: release_lock(lock)

    def complete(self,lease_id:str,lease_token:str,terminal_state:str,provider_cooldown_seconds:int=0)->dict[str,Any]:
        if terminal_state not in TERMINAL: raise SchedulerError('E_TERMINAL_STATE')
        if provider_cooldown_seconds<0: raise SchedulerError('E_COOLDOWN')
        lock=state_lock(self.state_path)
        try:
            s=load_state(self.state_path); lease=s['active_leases'].get(lease_id)
            if not lease: raise SchedulerError('E_LEASE_UNKNOWN')
            if not secrets.compare_digest(str(lease.get('lease_token','')),str(lease_token)): raise SchedulerError('E_LEASE_TOKEN')
            done=time.time(); key=lease['dispatch_key']; provider=lease['provider_id']
            rec={'dispatch_id':lease['dispatch_id'],'job_id':lease['job_id'],'lease_id':lease_id,'udd_id':lease['udd_id'],'profile_id':lease['profile_id'],'provider_id':provider,'dispatch_claimed':bool(lease['dispatch_claimed']),'terminal_state':terminal_state,'completed_epoch':done}
            s['dispatch_ledger'][key]=rec; del s['active_leases'][lease_id]
            if provider_cooldown_seconds: s['provider_cooldown_until'][provider]=done+provider_cooldown_seconds
            s['revision']+=1; atomic_write(self.state_path,s)
            return {'schema':SCHEMA,'status':'TERMINAL','record':rec,'provider_cooldown_until':s['provider_cooldown_until'].get(provider,0)}
        finally: release_lock(lock)

    def status(self)->dict[str,Any]:
        lock=state_lock(self.state_path)
        try:
            m,p,r=self._inputs(); s=load_state(self.state_path); now=time.time(); groups=rows_by_udd(m)
            ready_profiles={u:[x['profile_id'] for x in rows if profile_ready(r,x['profile_id'])] for u,rows in groups.items()}
            providers=[x['provider_id'] for x in p['providers'] if provider_ready(p,s,x['provider_id'],now)]
            return {'schema':SCHEMA,'status':'PASS','global_max_live_udd_owners':p['global_max_live_udd_owners'],'founder_approved_max_live_udd_owners':p['founder_approved_max_live_udd_owners'],'absolute_max_udd_owners':p['absolute_max_udd_owners'],'active_lease_count':len(s['active_leases']),'active_udd_ids':sorted(active_udd_ids(s)),'ready_profiles_by_udd':ready_profiles,'ready_provider_ids':providers,'state_revision':s['revision']}
        finally: release_lock(lock)

def build_scheduler(ns)->Scheduler:
    return Scheduler(Path(ns.manifest),Path(ns.policy),Path(ns.readiness),Path(ns.state),Path(ns.runtime_root))

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',default=str(DEFAULT_MANIFEST)); ap.add_argument('--policy',default=str(DEFAULT_POLICY)); ap.add_argument('--readiness',default=str(DEFAULT_READINESS)); ap.add_argument('--state',default=str(DEFAULT_STATE)); ap.add_argument('--runtime-root',default=str(DEFAULT_RUNTIME))
    sub=ap.add_subparsers(dest='command',required=True)
    a=sub.add_parser('acquire'); a.add_argument('--dispatch-id',required=True); a.add_argument('--job-id',required=True); a.add_argument('--preferred-provider',default='')
    c=sub.add_parser('claim-dispatch'); c.add_argument('--lease-id',required=True); c.add_argument('--lease-token',required=True)
    d=sub.add_parser('complete'); d.add_argument('--lease-id',required=True); d.add_argument('--lease-token',required=True); d.add_argument('--terminal-state',required=True); d.add_argument('--provider-cooldown-seconds',type=int,default=0)
    sub.add_parser('status')
    ns=ap.parse_args(); s=build_scheduler(ns)
    if ns.command=='acquire': out=s.acquire(dispatch_id=ns.dispatch_id,job_id=ns.job_id,preferred_provider=ns.preferred_provider or None)
    elif ns.command=='claim-dispatch': out=s.claim_dispatch(ns.lease_id,ns.lease_token)
    elif ns.command=='complete': out=s.complete(ns.lease_id,ns.lease_token,ns.terminal_state,ns.provider_cooldown_seconds)
    else: out=s.status()
    print(json.dumps(out,indent=2,sort_keys=True)); return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except SchedulerError as e:
        print(json.dumps({'schema':SCHEMA,'status':'ERROR','error':e.code,'detail':e.detail},sort_keys=True)); raise SystemExit(74)
