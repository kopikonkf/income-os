#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, sqlite3, subprocess, sys, time
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst')
STATE=ROOT/'state'
PLAN=SESSION/'config'/'watercolor-rollout-plan-v1.jsonl'
ARM=STATE/'FULL_ROLLOUT_ARMED.json'
FIRST100=STATE/'FIRST100_COMPLETE.json'
CONTROL=STATE/'operator-control.json'
LEDGER=STATE/'nexaburst-manifestation-ledger.db'
RESERVOIR=SESSION/'bin'/'nexaburst-reservoir.py'
COMPILER=SESSION/'bin'/'nexaburst-prompt-compile.py'
ADAPTER=SESSION/'bin'/'nexaburst-adapter.mjs'
HEALTH=SESSION/'bin'/'nexaburst-health.mjs'
NOTIFIER=SESSION/'bin'/'nexaburst-notify.py'
PROGRESS=STATE/'full-rollout-progress.json'
PAUSE=STATE/'full-rollout-pause.json'
LANE='WC-L0'
PRESET='ISOLATED_SOFT_WATERCOLOR_CLIPART_WHITE_L0'
BACKLOG_HARD=1000
BACKLOG_RESUME=500
MIN_FREE_GIB=100
MAX_CHECKPOINT_FAILURE_RATE=0.05

def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_name(path.name+f'.tmp-{os.getpid()}')
    t.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    os.replace(t,path)

def run(cmd,timeout=360):
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)

def notify(event,text):
    try: run([str(NOTIFIER),'--event',event,'--text',text],30)
    except Exception: pass

def control_mode():
    try:return json.loads(CONTROL.read_text(encoding='utf-8')).get('mode','PAUSED')
    except Exception:return 'PAUSED'

def health():
    cp=run(['node',str(HEALTH)],30)
    try:return json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception:return {'cdp':False,'error':(cp.stderr or cp.stdout)[-300:]}

def plan_sha():
    return hashlib.sha256(PLAN.read_bytes()).hexdigest()

def require_authority():
    if not FIRST100.is_file(): raise RuntimeError('E_FIRST100_NOT_COMPLETE')
    if not PLAN.is_file(): raise RuntimeError('E_ROLLOUT_PLAN_MISSING')
    if not ARM.is_file(): raise RuntimeError('E_FULL_ROLLOUT_NOT_ARMED')
    a=json.loads(ARM.read_text(encoding='utf-8'))
    if a.get('authorized') is not True or a.get('lane_id')!=LANE:
        raise RuntimeError('E_FULL_ROLLOUT_ARM_INVALID')
    if a.get('plan_sha256')!=plan_sha():
        raise RuntimeError('E_FULL_ROLLOUT_PLAN_SHA_MISMATCH')
    return a

def plan_rows():
    return [json.loads(x) for x in PLAN.read_text(encoding='utf-8').splitlines() if x.strip()]

def ledger_row(candidate_id):
    c=sqlite3.connect(str(LEDGER));c.row_factory=sqlite3.Row
    try:return c.execute('select * from manifestations where candidate_id=? and lane_id=?',(candidate_id,LANE)).fetchone()
    finally:c.close()

def backlog():
    c=sqlite3.connect(str(LEDGER))
    try:
        return c.execute("select count(*) from manifestations where lane_id=? and status='RAW_DONE'",(LANE,)).fetchone()[0]
    finally:c.close()

def free_gib():
    s=os.statvfs(ROOT);return s.f_bavail*s.f_frsize/1024**3

def set_pause(code,detail):
    atomic(PAUSE,{'schema':'die.h01.nexaburst.full-rollout-pause.v1','status':'PAUSED','code':code,'detail':detail,'at':now()})
    notify('PHASE1_PAUSED','Full rollout paused: '+detail)

def clear_pause():
    PAUSE.unlink(missing_ok=True)

def claim_exact(cid):
    cp=run([str(RESERVOIR),'claim','--lane',LANE,'--candidate-id',cid],60)
    if cp.returncode!=0: raise RuntimeError('E_RESERVOIR_CLAIM:'+(cp.stderr or cp.stdout)[-500:])
    return json.loads(cp.stdout.strip().splitlines()[-1])

def mark(row,status,**kw):
    cmd=[str(RESERVOIR),'mark','--candidate-id',row['candidate_id'],'--lane',LANE,'--status',status]
    if row.get('claim_id'):cmd+=['--claim-id',str(row['claim_id'])]
    for k,v in kw.items():
        if v is not None:cmd+=['--'+k.replace('_','-'),str(v)]
    cp=run(cmd,60)
    if cp.returncode!=0:raise RuntimeError('E_RESERVOIR_MARK:'+(cp.stderr or cp.stdout)[-500:])

def compile_prompt(row):
    asset='NBWC-'+str(row['candidate_id']).replace('CAND-','C')
    cp=run([str(COMPILER),'--noun',row['canonical_name'],'--candidate-id',row['candidate_id'],
            '--suitability',row.get('suitability') or 'lexname=noun.artifact',
            '--preset',PRESET,'--asset-id',asset],60)
    if cp.returncode!=0:raise RuntimeError('E_PROMPT_COMPILE:'+(cp.stderr or cp.stdout)[-500:])
    return json.loads(cp.stdout)

def checkpoint_ok(progress):
    attempts=max(1,int(progress.get('checkpoint_attempts',0)))
    failures=int(progress.get('checkpoint_failures',0))
    rate=failures/attempts
    b=backlog(); fg=free_gib()
    return rate<=MAX_CHECKPOINT_FAILURE_RATE and b<BACKLOG_HARD and fg>=MIN_FREE_GIB, {
      'attempts':attempts,'failures':failures,'failure_rate':rate,'raw_backlog':b,'disk_free_gib':round(fg,1)
    }

def main():
    try: require_authority()
    except Exception as e:
        print(json.dumps({'status':'LOCKED','error':str(e)}));return 76
    rows=plan_rows()
    progress={'next_index':1,'successes':0,'failures':0,'checkpoint_attempts':0,'checkpoint_failures':0}
    if PROGRESS.is_file():
        try:progress.update(json.loads(PROGRESS.read_text(encoding='utf-8')))
        except Exception:pass

    while int(progress['next_index'])<=len(rows):
        if control_mode()!='RUNNING':
            print(json.dumps({'status':'PAUSED_BY_OPERATOR','next_index':progress['next_index']}));return 0
        h=health()
        if not (h.get('cdp') and h.get('page') and h.get('authenticated') and h.get('unlimited_active')):
            set_pause('PROVIDER_HEALTH_GATE','Browser/auth/Unlimited health gate failed before submit.')
            return 20
        if free_gib()<MIN_FREE_GIB:
            set_pause('STORAGE_GATE',f'Free disk below {MIN_FREE_GIB} GiB.')
            return 21
        if backlog()>=BACKLOG_HARD:
            set_pause('V2_BACKLOG_GATE',f'RAW_DONE backlog reached {backlog()} (hard={BACKLOG_HARD}, resume={BACKLOG_RESUME}).')
            return 22

        item=rows[int(progress['next_index'])-1]
        existing=ledger_row(item['candidate_id'])
        if existing and existing['status'] in ('WAITING_FOUNDER_QC','VAULT_VERIFIED'):
            progress['next_index']=int(progress['next_index'])+1
            atomic(PROGRESS,progress);continue

        row=claim_exact(item['candidate_id'])
        if row.get('status') not in ('CLAIMED',):
            # Already in a non-claimable durable state: do not force reset.
            set_pause('PLAN_LEDGER_CONFLICT',f"candidate={item['candidate_id']} claim_status={row.get('status')}")
            return 23
        progress['checkpoint_attempts']=int(progress.get('checkpoint_attempts',0))+1
        try:
            prompt=compile_prompt(row)
            cp=run(['node',str(ADAPTER),'--noun',row['canonical_name'],'--style','soft-watercolor-clipart',
                    '--asset-id',prompt['asset_id'],'--aspect','1','--prompt',prompt['prompt'],
                    '--prompt-authority',prompt['prompt_authority'],'--compiled-contract-sha256',prompt['compiled_contract_sha256'],
                    '--candidate-id',row['candidate_id'],'--lane-id',LANE],360)
            if cp.returncode!=0:
                err=((cp.stderr or '')+'\n'+(cp.stdout or ''))[-600:]
                progress['failures']=int(progress.get('failures',0))+1
                progress['checkpoint_failures']=int(progress.get('checkpoint_failures',0))+1
                mark(row,'FAILED_RETRYABLE',error=err[:400])
                atomic(PROGRESS,progress)
                if '429' in err:
                    set_pause('PROVIDER_429','Provider returned 429/rate limit; Founder review required.')
                    return 24
                set_pause('PROVIDER_FAILURE','Bounded rollout stopped after provider failure; no loop.')
                return 25
            result=json.loads(cp.stdout.strip().splitlines()[-1])
            mark(row,'RAW_DONE',raw_job_id=result.get('job_id'),raw_sha256=result.get('sha256'))
            progress['successes']=int(progress.get('successes',0))+1
            progress['next_index']=int(progress['next_index'])+1
            atomic(PROGRESS,progress)
        except Exception as e:
            progress['failures']=int(progress.get('failures',0))+1
            progress['checkpoint_failures']=int(progress.get('checkpoint_failures',0))+1
            atomic(PROGRESS,progress)
            set_pause('ROLLOUT_EXCEPTION',str(e)[:400]);return 26

        # Every 100 planned items: health checkpoint. No manual approval if green.
        if (int(progress['next_index'])-1)%100==0:
            ok,metrics=checkpoint_ok(progress)
            notify('PHASE1_PROGRESS',f"Full rollout checkpoint {int(progress['next_index'])-1}/{len(rows)} metrics={json.dumps(metrics,separators=(',',':'))}")
            if not ok:
                set_pause('CHECKPOINT_GATE',f'Checkpoint unhealthy: {json.dumps(metrics,separators=(",",":"))}')
                return 27
            progress['checkpoint_attempts']=0;progress['checkpoint_failures']=0
            atomic(PROGRESS,progress)
    notify('PHASE1_BATCH_COMPLETE',f'Full WC-L0 semantic-presence rollout raw plan drained: {len(rows)} planned representatives.')
    return 0

if __name__=='__main__':raise SystemExit(main())
