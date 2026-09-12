#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, json, os, shutil, subprocess, sys
from pathlib import Path

SCHEMA='die.h01.brave-storage-gate.v1'
DEFAULT_ROOT=Path('/var/lib/die/h01/browser')
DEFAULT_MANIFEST=DEFAULT_ROOT/'fabric-manifest-v1.json'
DEFAULT_RUNTIME=Path('/run/user/1000/die-h01-brave')
MAX_LIVE=5
MIN_FREE=20*1024**3
POPULATED_THRESHOLD=16*1024**2
FORECAST_FLOOR=512*1024**2
CACHE_NAMES=('Cache','Code Cache','GPUCache','DawnGraphiteCache','DawnWebGPUCache')
UDD_CACHE_PATHS=(('GPUPersistentCache','GPUCache'),)
PROTECTED_NAMES={
 'Cookies','Cookies-journal','Local Storage','IndexedDB','WebStorage','Session Storage','Sessions',
 'Service Worker','Login Data','Login Data For Account','Preferences','Secure Preferences','Network',
 'GCM Store','Sync Data','BraveWallet','Extension State','File System','ClientCertificates'
}
class GateError(RuntimeError): pass

def du_bytes(path:Path)->int:
 r=subprocess.run(['du','-sxB1',str(path)],capture_output=True,text=True)
 if r.returncode: raise GateError(f'E_DU:{path}')
 return int(r.stdout.split()[0])

def load_manifest(path:Path)->dict:
 m=json.loads(path.read_text())
 if m.get('schema')!='die.h01.brave-fabric.host-local.v1': raise GateError('E_MANIFEST_SCHEMA')
 ps=m.get('profiles');
 if not isinstance(ps,list) or len(ps)!=100: raise GateError('E_PROFILE_COUNT')
 return m

def binding(m:dict,profile_id:str)->dict:
 for p in m['profiles']:
  if p.get('profile_id')==profile_id:return p
 raise GateError('E_PROFILE_UNKNOWN')

def lock_path(udd_id:str,runtime_root:Path)->Path:return runtime_root/f'{udd_id}.lock'

def udd_process_active(user_data_dir:str)->bool:
 r=subprocess.run(['ps','-eo','args='],capture_output=True,text=True,check=True)
 needle=f'--user-data-dir={user_data_dir}'
 return any(needle in line and ('brave' in line.lower()) for line in r.stdout.splitlines())

def try_lock(udd_id:str,runtime_root:Path):
 runtime_root.mkdir(parents=True,exist_ok=True)
 p=lock_path(udd_id,runtime_root); f=open(p,'a+')
 try:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  f.close(); raise GateError('E_UDD_LOCKED')
 return f

def live_h01_profiles(m:dict)->list[str]:
 r=subprocess.run(['ps','-eo','args='],capture_output=True,text=True,check=True)
 out=[]
 for p in m['profiles']:
  if any(f'--user-data-dir={p["user_data_dir"]}' in line and f'--profile-directory={p["profile_directory"]}' in line and 'brave' in line.lower() for line in r.stdout.splitlines()): out.append(p['profile_id'])
 return sorted(set(out))

def measure(m:dict,root:Path)->dict:
 usage=shutil.disk_usage(root)
 rows=[]
 for p in m['profiles']:
  d=Path(p['user_data_dir'])/p['profile_directory']
  b=du_bytes(d) if d.exists() else 0
  rows.append({'profile_id':p['profile_id'],'udd_id':p['udd_id'],'bytes':b})
 populated=[x for x in rows if x['bytes']>=POPULATED_THRESHOLD]
 largest=max((x['bytes'] for x in populated),default=0)
 forecast=max(largest,FORECAST_FLOOR)
 live=live_h01_profiles(m)
 required=MIN_FREE + max(0,MAX_LIVE-len(live))*forecast
 return {'filesystem':{'total_bytes':usage.total,'used_bytes':usage.used,'free_bytes':usage.free},'profiles':{'count':len(rows),'populated_threshold_bytes':POPULATED_THRESHOLD,'populated_count':len(populated),'populated':sorted(populated,key=lambda x:x['bytes'],reverse=True),'largest_populated_bytes':largest,'forecast_per_additional_live_profile_bytes':forecast},'live':{'profile_ids':live,'count':len(live),'hard_cap':MAX_LIVE},'capacity':{'minimum_free_reserve_bytes':MIN_FREE,'required_free_bytes':required,'admit':len(live)<MAX_LIVE and usage.free>=required}}

def cache_candidates(profile_dir:Path,udd_dir:Path)->list[Path]:
 out=[]
 for n in CACHE_NAMES:
  p=profile_dir/n
  if p.exists():out.append(p)
 for bits in UDD_CACHE_PATHS:
  p=udd_dir.joinpath(*bits)
  if p.exists():out.append(p)
 return out

def ensure_safe_candidate(p:Path,profile_dir:Path,udd_dir:Path):
 rp=p.resolve(); pr=profile_dir.resolve(); ur=udd_dir.resolve()
 if not (str(rp).startswith(str(pr)+os.sep) or str(rp).startswith(str(ur)+os.sep)): raise GateError('E_PATH_ESCAPE')
 if any(part in PROTECTED_NAMES for part in rp.parts): raise GateError('E_PROTECTED_PATH')

def janitor(m:dict,profile_id:str,runtime_root:Path,execute:bool)->dict:
 b=binding(m,profile_id); udd=Path(b['user_data_dir']); prof=udd/b['profile_directory']
 if udd_process_active(str(udd)): raise GateError('E_UDD_ACTIVE')
 lk=try_lock(b['udd_id'],runtime_root)
 try:
  c=cache_candidates(prof,udd); [ensure_safe_candidate(p,prof,udd) for p in c]
  items=[{'path':str(p),'bytes':du_bytes(p)} for p in c]
  protected_present=sorted(n for n in PROTECTED_NAMES if (prof/n).exists())
  if execute:
   for p in c:
    if p.is_dir(): shutil.rmtree(p)
    else:p.unlink()
  return {'udd_id':b['udd_id'],'profile_id':profile_id,'udd_closed':True,'lock_acquired':True,'mode':'EXECUTE' if execute else 'DRY_RUN','candidates':items,'reclaimable_bytes':sum(x['bytes'] for x in items),'protected_root_entries_present':protected_present,'protected_entries_touched':False}
 finally:
  fcntl.flock(lk,fcntl.LOCK_UN);lk.close()

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['measure','admit','janitor']); ap.add_argument('--manifest',default=str(DEFAULT_MANIFEST)); ap.add_argument('--root',default=str(DEFAULT_ROOT)); ap.add_argument('--runtime-root',default=str(DEFAULT_RUNTIME)); ap.add_argument('--profile-id'); ap.add_argument('--execute',action='store_true'); ns=ap.parse_args()
 m=load_manifest(Path(ns.manifest))
 if ns.command=='measure': out={'schema':SCHEMA,'command':'measure','result':measure(m,Path(ns.root))}
 elif ns.command=='admit':
  x=measure(m,Path(ns.root)); out={'schema':SCHEMA,'command':'admit','result':x};
  if not x['capacity']['admit']: print(json.dumps(out,indent=2)); return 75
 else:
  if not ns.profile_id: raise GateError('E_PROFILE_REQUIRED')
  out={'schema':SCHEMA,'command':'janitor','result':janitor(m,ns.profile_id,Path(ns.runtime_root),ns.execute)}
 print(json.dumps(out,indent=2,sort_keys=True)); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except GateError as e: print(json.dumps({'schema':SCHEMA,'status':'ERROR','error':str(e)})); raise SystemExit(74)
