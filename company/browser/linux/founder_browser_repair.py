#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,os,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path

REPAIR_ROOT=Path('/var/lib/muxia/state/founder-repair')
CFG={
 'cluster-a':{'display':101,'broker':39121,'view_service':'die-founder-vnc-cluster-a.service','interactive_port':59201},
 'cluster-b':{'display':102,'broker':39122,'view_service':'die-founder-vnc-cluster-b.service','interactive_port':59202},
}
def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def atomic(path:Path,value:dict):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,path)
def status(cluster:str):
 p=REPAIR_ROOT/f'{cluster}.json'
 if not p.is_file():return {'schema':'die.factory-asset.founder-repair-lease.v1','cluster_id':cluster,'state':'INACTIVE'}
 try:d=json.loads(p.read_text())
 except Exception:return {'schema':'die.factory-asset.founder-repair-lease.v1','cluster_id':cluster,'state':'INVALID'}
 if d.get('state')=='ACTIVE' and float(d.get('expires_at_epoch',0))<=time.time(): d['state']='EXPIRED'
 return d
def broker(cluster:str):
 with urllib.request.urlopen(f"http://127.0.0.1:{CFG[cluster]['broker']}/v1/status",timeout=5) as r:return json.load(r)
def open_repair(cluster:str,timeout:int)->int:
 if timeout<30 or timeout>1800:raise RuntimeError('E_TIMEOUT_RANGE')
 existing=status(cluster)
 if existing.get('state')=='ACTIVE':raise RuntimeError('E_REPAIR_ALREADY_ACTIVE')
 b=broker(cluster); leases=int((b.get('tab_leases') or {}).get('active_leases',-1))
 if b.get('state')!='READY' or leases!=0:raise RuntimeError(f'E_CLUSTER_NOT_IDLE:{b.get("state")}:{leases}')
 cfg=CFG[cluster];start=time.time();lease={'schema':'die.factory-asset.founder-repair-lease.v1','cluster_id':cluster,'state':'ACTIVE','mode':'INTERACTIVE_BROWSER_REPAIR','opened_at':now(),'opened_at_epoch':start,'expires_at_epoch':start+timeout,'timeout_seconds':timeout,'interactive_port':cfg['interactive_port'],'bind_host':'127.0.0.1','transport':'SSH_LOCAL_FORWARD','credential_values_read':False,'cookies_or_tokens_read':False,'captcha_bypass_authorized':False}
 atomic(REPAIR_ROOT/f'{cluster}.json',lease)
 subprocess.run(['sudo','systemctl','stop',cfg['view_service']],check=True)
 cmd=['/usr/bin/bash','/opt/die/factory-asset-observability/founder_vnc_view.sh','--cluster-id',cluster,'--display',str(cfg['display']),'--port',str(cfg['interactive_port']),'--mode','interactive']
 proc=subprocess.Popen(cmd,start_new_session=True)
 try:
  atomic(REPAIR_ROOT/f'{cluster}.runtime.json',{'pid':proc.pid,'cluster_id':cluster,'interactive_port':cfg['interactive_port'],'started_at':now()})
  deadline=time.time()+timeout
  while time.time()<deadline and proc.poll() is None:time.sleep(1)
 finally:
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  lease['state']='CLOSED';lease['closed_at']=now();atomic(REPAIR_ROOT/f'{cluster}.json',lease)
  (REPAIR_ROOT/f'{cluster}.runtime.json').unlink(missing_ok=True)
  subprocess.run(['sudo','systemctl','start',cfg['view_service']],check=True)
 return 0
def revoke(cluster:str)->int:
 cfg=CFG[cluster];rp=REPAIR_ROOT/f'{cluster}.runtime.json'
 if rp.is_file():
  try:pid=int(json.loads(rp.read_text()).get('pid',0))
  except Exception:pid=0
  if pid>1:
   try:os.killpg(pid,signal.SIGTERM)
   except ProcessLookupError:pass
 d=status(cluster);d['state']='REVOKED';d['revoked_at']=now();atomic(REPAIR_ROOT/f'{cluster}.json',d);rp.unlink(missing_ok=True);subprocess.run(['sudo','systemctl','start',cfg['view_service']],check=True);return 0
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 for n in ('status','revoke'):
  x=sp.add_parser(n);x.add_argument('--cluster',choices=CFG,required=True)
 x=sp.add_parser('open');x.add_argument('--cluster',choices=CFG,required=True);x.add_argument('--timeout',type=int,default=900)
 a=ap.parse_args()
 if a.cmd=='status':print(json.dumps(status(a.cluster),sort_keys=True));return 0
 if a.cmd=='revoke':return revoke(a.cluster)
 return open_repair(a.cluster,a.timeout)
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(f'{type(e).__name__}:{e}',file=sys.stderr);raise SystemExit(2)
