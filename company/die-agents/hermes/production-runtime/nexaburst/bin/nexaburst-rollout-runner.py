#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, sqlite3, subprocess, sys, time
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
CONTROL_SCRIPT=SESSION/'bin'/'nexaburst-control.py'
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
    try: limit=int(a.get('authorized_plan_items',0))
    except Exception: raise RuntimeError('E_FULL_ROLLOUT_AUTH_LIMIT_INVALID')
    if limit<1: raise RuntimeError('E_FULL_ROLLOUT_AUTH_LIMIT_INVALID')
    a['authorized_plan_items']=limit
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

def set_pause(code,detail,resume_after=None):
    atomic(PAUSE,{'schema':'die.h01.nexaburst.full-rollout-pause.v1','status':'PAUSED','code':code,'detail':detail,
                  'resume_after_epoch':resume_after,'at':now()})
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

def parse_adapter_error(cp):
    text=(cp.stderr or '')+'\n'+(cp.stdout or '')
    for line in reversed(text.splitlines()):
        if 'NEXABURST_ERROR ' in line:
            return line.split('NEXABURST_ERROR ',1)[1][:600]
    return text[-600:].strip() or f'exit={cp.returncode}'

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
    try: authority=require_authority()
    except Exception as e:
        print(json.dumps({'status':'LOCKED','error':str(e)}));return 76
    rows=plan_rows()
    authorized_limit=min(int(authority['authorized_plan_items']),len(rows))
    progress={'next_index':1,'successes':0,'failures':0,'checkpoint_attempts':0,'checkpoint_failures':0}
    if PROGRESS.is_file():
        try:progress.update(json.loads(PROGRESS.read_text(encoding='utf-8')))
        except Exception:pass

    while int(progress['next_index'])<=authorized_limit:
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
            cmd=['node',str(ADAPTER),'--noun',row['canonical_name'],'--style','soft-watercolor-clipart',
                 '--asset-id',prompt['asset_id'],'--aspect','1','--prompt',prompt['prompt'],
                 '--prompt-authority',prompt['prompt_authority'],'--compiled-contract-sha256',prompt['compiled_contract_sha256'],
                 '--candidate-id',row['candidate_id'],'--lane-id',LANE]
            if row.get('raw_job_id'):
                cmd += ['--resume-job-id',str(row['raw_job_id'])]
            cp=run(cmd,360)
            if cp.returncode!=0:
                err=parse_adapter_error(cp)
                attempts=int(row.get('attempts') or 1)
                progress['failures']=int(progress.get('failures',0))+1
                progress['checkpoint_failures']=int(progress.get('checkpoint_failures',0))+1
                atomic(PROGRESS,progress)
                if 'E_JOB_STILL_PROCESSING:' in err:
                    m=re.search(r'"job_id":"([^"]+)"',err)
                    job_id=m.group(1) if m else row.get('raw_job_id')
                    if attempts>=3:
                        mark(row,'BLOCKED',raw_job_id=job_id,error=err[:400])
                        set_pause('CANDIDATE_BLOCKED',f'Provider job stayed non-terminal across three bounded poll windows. noun={row["canonical_name"]} job_id={job_id}. No resubmit.')
                        return 28
                    mark(row,'FAILED_RETRYABLE',raw_job_id=job_id,error=err[:400])
                    set_pause('RETRY_BACKOFF',f'Resume same provider job after bounded poll timeout. noun={row["canonical_name"]} job_id={job_id} poll_window={attempts}/3. No new submit.',
                              resume_after=int(time.time())+120)
                    return 13
                fatal=any(code in err for code in ('E_AUTH_REQUIRED','E_UNLIMITED_INACTIVE','E_RAW_STORAGE_GATE_FREE_BYTES','E_CDP_CONTEXT_MISSING'))
                if fatal:
                    mark(row,'FAILED_RETRYABLE',error=err[:400])
                    set_pause('PROVIDER_GATE',f'Provider gate stopped rollout at {row["canonical_name"]}: {err[:260]}')
                    return 25
                if '429' in err or 'E_PROVIDER_RATE_LIMITED' in err:
                    mark(row,'FAILED_RETRYABLE',error=err[:400])
                    set_pause('PROVIDER_429',f'Provider returned rate limit at noun={row["canonical_name"]}; Founder review required.')
                    return 24
                if attempts>=2:
                    mark(row,'BLOCKED',error=err[:400])
                    set_pause('CANDIDATE_BLOCKED',f'Candidate failed two bounded outer attempts. noun={row["canonical_name"]} candidate={row["candidate_id"]} error={err[:240]}')
                    return 26
                mark(row,'FAILED_RETRYABLE',error=err[:400])
                set_pause('RETRY_BACKOFF',f'One bounded retry scheduled for noun={row["canonical_name"]}. No immediate retry loop. error={err[:220]}',
                          resume_after=int(time.time())+300)
                return 12
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
            notify('PHASE1_PROGRESS',f"Authorized rollout checkpoint {int(progress['next_index'])-1}/{authorized_limit} metrics={json.dumps(metrics,separators=(',',':'))}")
            if not ok:
                set_pause('CHECKPOINT_GATE',f'Checkpoint unhealthy: {json.dumps(metrics,separators=(",",":"))}')
                return 27
            progress['checkpoint_attempts']=0;progress['checkpoint_failures']=0
            atomic(PROGRESS,progress)
    # Authorization boundary is always a durable pause. A new Founder authorization
    # is required before the next cohort/slice can start.
    run([str(CONTROL_SCRIPT),'set','--mode','PAUSED','--reason',
         f'Authorized WC-L0 slice complete: {authorized_limit}/{len(rows)} planned representatives; next slice locked.',
         '--actor','nexaburst-rollout-authorization-boundary'],30)
    notify('PHASE1_BATCH_COMPLETE',
           f'Authorized WC-L0 slice COMPLETE: {authorized_limit}/{authorized_limit} raw representatives acquired. '
           f'Production auto-paused at Founder authorization boundary; {len(rows)-authorized_limit} planned representatives remain locked.')
    return 0

if __name__=='__main__':raise SystemExit(main())