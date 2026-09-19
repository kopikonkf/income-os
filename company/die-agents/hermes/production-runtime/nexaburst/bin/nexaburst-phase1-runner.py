#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst')
STATE=ROOT/'state'
RESERVOIR=SESSION/'bin'/'nexaburst-reservoir.py'
COMPILER=SESSION/'bin'/'nexaburst-prompt-compile.py'
ADAPTER=SESSION/'bin'/'nexaburst-adapter.mjs'
HEALTH=SESSION/'bin'/'nexaburst-health.mjs'
NOTIFIER=SESSION/'bin'/'nexaburst-notify.py'
PAUSE=STATE/'phase1-pause.json'
PROGRESS=STATE/'phase1-progress.json'
DONE_MARK=STATE/'phase1-first100-raw-complete.json'
LANE='WC-L0'
PRESET='ISOLATED_SOFT_WATERCOLOR_CLIPART_WHITE_L0'
TYPED_CACHE=SESSION/'config'/'market-canary-100-wave3pass-watercolor-typed.jsonl'


def typed_cache():
    out={}
    if TYPED_CACHE.is_file():
        for line in TYPED_CACHE.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            try:
                row=json.loads(line); out[str(row.get('candidate_id'))]=row
            except Exception: pass
    return out
TYPED=typed_cache()

def run(cmd,timeout=300):
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)

def notify(event,text):
    try: run([str(NOTIFIER),'--event',event,'--text',text],30)
    except Exception: pass

def atomic(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    os.replace(tmp,path)

def health():
    cp=run(['node',str(HEALTH)],30)
    if cp.returncode!=0: return {'cdp':False,'error':(cp.stderr or cp.stdout)[-300:]}
    try:return json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception:return {'cdp':False,'error':'E_HEALTH_PARSE'}

def set_pause(code,detail,resume_after=None,founder=False):
    old={}
    if PAUSE.is_file():
        try: old=json.loads(PAUSE.read_text())
        except Exception: pass
    obj={'schema':'die.h01.nexaburst.phase1-pause.v1','status':'PAUSED','code':code,'detail':detail,
         'resume_after_epoch':resume_after,'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    atomic(PAUSE,obj)
    if old.get('code')!=code or old.get('detail')!=detail:
        notify('FOUNDER_ACTION_REQUIRED' if founder else 'PHASE1_PAUSED',detail)
    return obj

def clear_pause():
    if PAUSE.exists(): PAUSE.unlink()

def reservoir_cmd(args):
    cp=run([str(RESERVOIR),*args],60)
    if cp.returncode!=0: raise RuntimeError('E_RESERVOIR:'+(cp.stderr or cp.stdout)[-500:])
    return json.loads(cp.stdout.strip().splitlines()[-1])

def mark(row,status,**kw):
    cmd=['mark','--candidate-id',str(row['candidate_id']),'--lane',LANE,'--status',status]
    if row.get('claim_id'):cmd+=['--claim-id',str(row['claim_id'])]
    for k,v in kw.items():
        if v is not None:cmd+=['--'+k.replace('_','-'),str(v)]
    return reservoir_cmd(cmd)

def parse_adapter_error(cp):
    text=(cp.stderr or '')+'\n'+(cp.stdout or '')
    for line in reversed(text.splitlines()):
        if 'NEXABURST_ERROR ' in line:return line.split('NEXABURST_ERROR ',1)[1][:600]
    return text[-600:].strip() or f'exit={cp.returncode}'

def compile_prompt(row):
    cached=TYPED.get(str(row['candidate_id']))
    if cached:
        if cached.get('prompt_authority')!='TYPED_VISUAL_CONTRACT_V1': raise RuntimeError('E_TYPED_CACHE_AUTHORITY')
        return cached
    asset='NBWC-'+str(row['candidate_id']).replace('CAND-','C')
    cp=run([str(COMPILER),'--noun',row['canonical_name'],'--candidate-id',str(row['candidate_id']),
            '--suitability',row.get('suitability') or 'lexname=noun.artifact',
            '--preset',PRESET,'--asset-id',asset],60)
    if cp.returncode!=0:raise RuntimeError('E_PROMPT_COMPILE:'+(cp.stderr or cp.stdout)[-500:])
    return json.loads(cp.stdout)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--max-success',type=int,default=100); ap.add_argument('--max-priority',type=int,default=999)
    args=ap.parse_args()
    successes=0
    notify('PHASE1_PROGRESS','Watercolor Phase-1 acquisition started. Window: first 100 strict Wave3-pass/no-IP nouns.')
    while successes < args.max_success:
        h=health()
        if not h.get('cdp') or not h.get('page'):
            set_pause('BROWSER_UNAVAILABLE','Browser/CDP is unavailable. Phase-1 stopped before submit.',founder=True); return 20
        if not h.get('authenticated'):
            set_pause('AUTH_REQUIRED','NexaBurst authentication is required. No further submits will occur until login is restored.',founder=True); return 21
        if not h.get('unlimited_active'):
            set_pause('UNLIMITED_INACTIVE','Nexa Unlimited is inactive. Phase-1 is paused; please top up/restore Unlimited.',founder=True); return 22
        stat=os.statvfs(ROOT); free=stat.f_bavail*stat.f_frsize
        if free < 25*1024**3:
            set_pause('STORAGE_GATE',f'Free disk is below 25 GiB ({free/1024**3:.1f} GiB). Phase-1 paused before submit.',founder=True); return 23

        row=reservoir_cmd(['claim','--lane',LANE,'--max-priority',str(args.max_priority)])
        if row.get('status') in {'NO_CLAIMABLE','EXHAUSTED'}:
            stats=reservoir_cmd(['stats','--lane',LANE])
            atomic(DONE_MARK,{'schema':'die.h01.nexaburst.phase1-first100-raw-complete.v1','status':'RAW_WINDOW_DRAINED',
                              'stats':stats,'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            notify('PHASE1_BATCH_COMPLETE',f'First-100 raw acquisition window drained. first100_complete={stats.get("first100_complete")} V2/Vault may still be draining.')
            return 0

        attempts=int(row.get('attempts') or 1)
        try:
            prompt=compile_prompt(row)
        except Exception as exc:
            mark(row,'BLOCKED',error=str(exc)[:400])
            set_pause('PROMPT_COMPILE_BLOCK',f'Prompt compile blocked candidate={row["candidate_id"]} noun={row["canonical_name"]} error={str(exc)[:260]}',founder=True)
            return 24

        cmd=['node',str(ADAPTER),'--noun',row['canonical_name'],'--style','soft-watercolor-clipart',
             '--asset-id',prompt['asset_id'],'--aspect','1','--prompt',prompt['prompt'],
             '--prompt-authority',prompt['prompt_authority'],'--compiled-contract-sha256',prompt['compiled_contract_sha256'],
             '--candidate-id',str(row['candidate_id']),'--lane-id',LANE]
        cp=run(cmd,360)
        if cp.returncode!=0:
            err=parse_adapter_error(cp)
            fatal=any(code in err for code in ('E_AUTH_REQUIRED','E_UNLIMITED_INACTIVE','E_RAW_STORAGE_GATE_FREE_BYTES','E_CDP_CONTEXT_MISSING'))
            if fatal:
                mark(row,'FAILED_RETRYABLE',error=err[:400])
                set_pause('PROVIDER_GATE',f'Provider gate stopped Phase-1 at {row["canonical_name"]}: {err[:260]}',founder=True); return 25
            if attempts >= 2:
                mark(row,'BLOCKED',error=err[:400])
                set_pause('CANDIDATE_BLOCKED',f'Candidate failed two bounded outer attempts and is held. noun={row["canonical_name"]} candidate={row["candidate_id"]} error={err[:240]}',founder=True)
                return 26
            mark(row,'FAILED_RETRYABLE',error=err[:400])
            set_pause('RETRY_BACKOFF',f'One bounded retry scheduled for noun={row["canonical_name"]}. No immediate retry loop. error={err[:220]}',resume_after=int(time.time())+300,founder=False)
            return 12

        try:
            result=json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:
            mark(row,'BLOCKED',error='E_ADAPTER_RESULT_PARSE')
            set_pause('RESULT_PARSE_BLOCK',f'Adapter returned success but result JSON could not be parsed for {row["canonical_name"]}.',founder=True); return 27
        mark(row,'RAW_DONE',raw_job_id=result.get('job_id'),raw_sha256=result.get('sha256'))
        successes+=1
        if successes % 25 == 0:
            stats=reservoir_cmd(['stats','--lane',LANE])
            notify('PHASE1_PROGRESS',f'Watercolor raw acquisition progress: {successes}/100 this run. Lane complete={stats.get("complete")}/{stats.get("total")}.')
    stats=reservoir_cmd(['stats','--lane',LANE])
    atomic(DONE_MARK,{'schema':'die.h01.nexaburst.phase1-first100-raw-complete.v1','status':'RAW_LIMIT_REACHED',
                      'run_successes':successes,'stats':stats,'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    notify('PHASE1_BATCH_COMPLETE',f'Watercolor first-100 raw acquisition reached limit: {successes}/100 generated. V2 continues asynchronously.')
    return 0

if __name__=='__main__': raise SystemExit(main())
