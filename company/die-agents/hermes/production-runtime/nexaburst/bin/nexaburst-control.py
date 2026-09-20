#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sqlite3, subprocess, time
from pathlib import Path

ROOT=Path('/var/lib/die/h01/nexaburst')
STATE=ROOT/'state'
CONTROL=STATE/'operator-control.json'
LEDGER=STATE/'nexaburst-manifestation-ledger.db'
SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
HEALTH=SESSION/'bin'/'nexaburst-health.mjs'
VALID={'RUNNING','PAUSED','STOPPED'}

def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def current():
    if CONTROL.is_file():
        try:
            d=json.loads(CONTROL.read_text(encoding='utf-8'))
            if d.get('mode') in VALID:return d
        except Exception:pass
    return {'schema':'die.h01.nexaburst.operator-control.v1','mode':'PAUSED','reason':'SAFE_DEFAULT_UNINITIALIZED','updated_at':None,'updated_by':'system'}

def set_mode(mode,reason,actor):
    mode=mode.upper()
    if mode not in VALID: raise SystemExit('E_MODE')
    d={'schema':'die.h01.nexaburst.operator-control.v1','mode':mode,'reason':reason[:500],
       'updated_at':now(),'updated_by':actor[:160]}
    atomic(CONTROL,d)
    return d

def proc(pattern):
    cp=subprocess.run(['pgrep','-f',pattern],text=True,capture_output=True,check=False)
    return [x for x in cp.stdout.split() if x.isdigit()]

def health():
    cp=subprocess.run(['node',str(HEALTH)],text=True,capture_output=True,timeout=20,check=False)
    try:return json.loads(cp.stdout.strip().splitlines()[-1])
    except:return {'cdp':False,'page':False,'authenticated':False,'unlimited_active':False,'error':(cp.stderr or cp.stdout)[-200:]}

def stats():
    out={'total':0,'complete':0,'first100_complete':0,'by_status':{}}
    if not LEDGER.is_file():return out
    c=sqlite3.connect(str(LEDGER))
    try:
        rows=c.execute("select status,count(*) from manifestations where lane_id='WC-L0' group by status").fetchall()
        out['by_status']={k:v for k,v in rows}; out['total']=sum(v for _,v in rows)
        out['complete']=sum(out['by_status'].get(k,0) for k in ('WAITING_FOUNDER_QC','VAULT_VERIFIED'))
        out['first100_complete']=c.execute("select count(*) from manifestations where lane_id='WC-L0' and priority<1000 and status in ('WAITING_FOUNDER_QC','VAULT_VERIFIED')").fetchone()[0]
        out['first100_failed']=c.execute("select count(*) from manifestations where lane_id='WC-L0' and priority<1000 and status in ('FAILED_RETRYABLE','BLOCKED')").fetchone()[0]
        out['first100_pending']=100-out['first100_complete']-out['first100_failed']
    finally:c.close()
    return out

def status():
    ctl=current(); h=health(); st=stats()
    stat=os.statvfs(ROOT); free=stat.f_bavail*stat.f_frsize
    phase_pause=None
    pp=STATE/'phase1-pause.json'
    if pp.is_file():
        try:phase_pause=json.loads(pp.read_text()).get('code')
        except:phase_pause='UNKNOWN'
    return {
      'control':ctl,'health':h,'stats':st,'disk_free_gib':round(free/1024**3,1),
      'phase1_pause':phase_pause,
      'runner_alive':bool(proc('nexaburst-phase1-runner.py')),
      'v2_alive':bool(proc('nexaburst-v2-worker.py --continuous')),
      'realesrgan_active':bool(proc('realesrgan_backend.py'))
    }

def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('set');p.add_argument('--mode',required=True);p.add_argument('--reason',default='Founder command');p.add_argument('--actor',default='local')
    sp.add_parser('status')
    a=ap.parse_args()
    if a.cmd=='set':print(json.dumps(set_mode(a.mode,a.reason,a.actor),ensure_ascii=False))
    else: print(json.dumps(status(),ensure_ascii=False))
if __name__=='__main__':main()
