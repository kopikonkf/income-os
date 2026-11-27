#!/opt/die/factory-asset/venv/bin/python
"""V2 post-production worker for PSR lane-2 (Founder GO required for full-run).

Mirrors bin/nexaburst-v2-worker.py (lane-1) but rooted at the lane-2 tree and
lane-2 conventions:
  ROOT ......... /var/lib/die/h01/nexaburst-lane2-psr
  QUEUE ........ state/v2-queue.jsonl (17.070 items, same schema as lane-1)
  DONE ......... state/v2-done.jsonl (created here)
  WORKSPACES ... workspaces/NBPSR-*
  PAUSE ........ state/STOP_PSR (present = idle; lane-2 convention)
  NOTIFY ....... nexaburst-notify.py with NEXABURST_ENV_PATH=lane2 env
                 (separate bot, report thread 6588)

OPSI A metadata: per-asset {title, description, keywords} from the KW-Gemini
PSR worker (kw-receipt.v2) are threaded into the pipeline as
metadata_overrides (title_override/description_override/keywords_override).
Assets without a KW receipt fall back to legacy minimal metadata.

Usage:
  nexaburst-v2-worker-psr.py --once [--asset-id NBPSR-...]
  nexaburst-v2-worker-psr.py --continuous [--poll-seconds 10]
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, sys, time, fcntl, shutil, subprocess
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst-lane2-psr')
QUEUE=ROOT/'state'/'v2-queue.jsonl'
DONE=ROOT/'state'/'v2-done.jsonl'
LOCK=ROOT/'state'/'v2-worker-psr.lock'
SHARD=(0,1)
HOLD=ROOT/'state'/'v2-hold-ids.txt'
STOP=ROOT/'state'/'STOP_PSR'
WORKSPACES=ROOT/'workspaces'
KW_RECEIPTS=Path('/var/lib/die/h01/nexaburst-kw-psr/receipts.jsonl')
FO=Path('/srv/die/company/die-agents/hermes/production-runtime/factory_orchestration_v2.py')
AU=Path('/srv/die/bridge/income_os_bridge/asset_upscale.py')
POLICY=Path('/srv/die/company/atlas/object-centric/object-asset-engine/source/scripts/postprocess/upscale-policy.v1.json')
NOTIFIER=SESSION/'bin'/'nexaburst-notify.py'
LANE2_ENV=Path('/home/kopiko/.config/die/nexaburst-lane2.env')
PAUSE=ROOT/'state'/'v2-pause.json'

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
fo=loadmod('nexaburst_fo_psr',FO)
au=loadmod('nexaburst_au_psr',AU)
policy=au.load_policy(POLICY)

def csha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(tmp,path)
def append(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('a',encoding='utf-8') as f:f.write(json.dumps(value,sort_keys=True,ensure_ascii=False)+'\n')

def notify(event,text):
    try:
        env=dict(os.environ); env['NEXABURST_ENV_PATH']=str(LANE2_ENV)
        subprocess.run([str(NOTIFIER),'--event',event,'--text',text],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=False,env=env)
    except Exception:
        pass

def load_kw() -> dict[str,dict]:
    """asset_id -> {title_override, description_override, keywords_override}."""
    out: dict[str,dict] = {}
    if KW_RECEIPTS.is_file():
        for line in KW_RECEIPTS.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            try:
                o=json.loads(line); aid=o.get('asset_id')
                if not aid: continue
                ov={}
                if o.get('title'): ov['title_override']=o['title']
                if o.get('description'): ov['description_override']=o['description']
                if o.get('keywords'): ov['keywords_override']=o['keywords']
                if ov: out[aid]=ov
            except Exception: pass
    return out
KW=load_kw()
KW_MTIME=KW_RECEIPTS.stat().st_mtime if KW_RECEIPTS.is_file() else 0.0

def refresh_kw():
    """Reload KW receipts if file grew (V2 follows KW tail; never legacy-leaks)."""
    global KW, KW_MTIME
    try:
        mt=KW_RECEIPTS.stat().st_mtime
    except Exception:
        return
    if mt > KW_MTIME:
        KW=load_kw(); KW_MTIME=mt

def safe(s): return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(s))

def build_legacy(item,workspace):
    noun=item['noun'];style=item.get('style','isolated-object');asset=item['asset_id']
    receipt=json.loads(Path(item['generation_receipt']).read_text(encoding='utf-8'))
    prompt=receipt['prompt']
    bp={
      'schema_version':'die.production.family-blueprint.v1',
      'request_id':'NEXABURST-PSR-'+safe(asset),
      'blueprint_id':'BP-NEXABURST-PSR-'+safe(asset),
      'task_id':asset,'mission_id':'M-001-PSR',
      'repository_sha':'RUNTIME_ISOLATED_NEXABURST_PSR',
      'principal':{'principal_id':'h01-nexaburst-psr','role':'PROVIDER_ADAPTER'},
      'seed':{'id':asset,'canonical_name':noun,'object_class':'concrete_visual','category_path':'object_atlas.nexaburst.psr','asset_tier':'U1-raster','demand_status':'atlas_candidate','demand_score':0.0},
      'family':{
        'family_id':'FAM-NEXABURST-PSR-'+safe(style),
        'family_thesis':f'{style} object-atlas stock component family (PSR lane).',
        'buyer_persona':['stock designers','content creators'],
        'use_cases':['isolated design component','commercial stock composition'],
        'commercial_use_hypothesis':'Object Atlas PSR production hypothesis pending marketplace evidence.',
        'evidence_status':'OBJECT_ATLAS_PRODUCTION_CANARY'
      },
      'production':{
        'asset_type':'RASTER_IMAGE','batch_size':1,'engine':'NEXABURST/nexaburst-lane2-psr',
        'master_prompt':prompt,
        'negative_constraints':['no logos','no trademarks','no brands','no watermark','no extra objects'],
        'semantic_variation_plan':[{'variation_id':'VAR-001','dimension':'style','instruction':style,'commercial_rationale':'Bounded Object Atlas PSR style lane.'}]
      },
      'metadata_direction':{
        'title_direction':f'{style} {noun} isolated stock illustration',
        'primary_keywords':[noun,style,'isolated'],
        'category_direction':['objects','design components']
      },
      'qa_requirements':{
        'required_checks':['artifact integrity','technical QA','visual commercial QC'],
        'forbidden_elements':['logos','trademarks','watermarks']
      },
      'lineage':{
        'seed_snapshot_sha256':item['source_sha256'],
        'source_kind':'NEXABURST_WEB_SESSION',
        'external_market_evidence_claimed':False
      },
      'authority':{
        'effect':'NONE','existing_production_authority_unchanged':True,
        'submission_authorized':False,'publication_authorized':False,'spend_authorized':False
      }
    }
    lock={
      'schema':'die.production.fixed-blueprint-lock.v1','task_id':asset,
      'blueprint_id':bp['blueprint_id'],'blueprint_sha256':csha(bp),
      'executive_review_id':'RUNTIME_NEXABURST_PSR',
      'executive_review_sha256':'0'*64,'author_receipt_sha256':'0'*64,'review_receipt_sha256':'0'*64,
      'locked_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'authority_effect':'NONE'
    }
    atomic(workspace/'blueprint.json',bp);atomic(workspace/'blueprint.lock.json',lock)
    atomic(workspace/'nexaburst-source.json',item)
    return bp,lock

def upscale_fn(source,output):
    return au.process(
      source=Path(source),output=Path(output),policy=policy,
      min_width=2000,min_height=2000,min_megapixels=4.0,
      rights_state='PENDING_HUMAN_REVIEW',safety_state='PENDING_HUMAN_REVIEW',
      timeout_sec=1800
    )

def processed_ids():
    out=set()
    if DONE.is_file():
        for line in DONE.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    d=json.loads(line)
                    if d.get('status')=='WAITING_FOUNDER_QC':out.add(d.get('asset_id'))
                except Exception:pass
    return out

def in_shard(asset_id):
    if not SHARD:return True
    return int(hashlib.sha256(asset_id.encode()).hexdigest(),16)%SHARD[1]==SHARD[0]

def pending(asset_id=None):
    if STOP.is_file():return []
    if not QUEUE.is_file():return []
    refresh_kw()
    done=processed_ids(); held=set()
    if HOLD.is_file():
        held={x.strip() for x in HOLD.read_text(encoding='utf-8').splitlines() if x.strip()}
    rows=[]
    for line in QUEUE.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        try:o=json.loads(line)
        except Exception:continue
        aid=o.get('asset_id')
        if not aid or aid in done or aid in held:continue
        if asset_id and aid!=asset_id:continue
        if not asset_id and aid not in KW:
            continue  # OPSI A: V2 menunggu KW receipt (tanpa legacy-leak)
        if not in_shard(aid):continue
        rows.append(o)
        if len(rows)>=1 and asset_id:break
    return rows

def error_count(asset_id):
    ep=ROOT/'state'/'v2-errors.jsonl'
    if not ep.is_file(): return 0
    n=0
    for line in ep.read_text(encoding='utf-8').splitlines():
        try:
            if json.loads(line).get('asset_id')==asset_id: n+=1
        except Exception: pass
    return n

def add_hold(asset_id):
    held=set()
    if HOLD.is_file():
        held={x.strip() for x in HOLD.read_text(encoding='utf-8').splitlines() if x.strip()}
    if asset_id not in held:
        held.add(asset_id)
        tmp=HOLD.with_name(HOLD.name+f'.tmp-{os.getpid()}')
        tmp.write_text('\n'.join(sorted(held))+'\n',encoding='utf-8')
        os.replace(tmp,HOLD)

def process_item(item):
    free=shutil.disk_usage(ROOT).free
    if free < 20*1024**3:
        raise RuntimeError(f'E_V2_STORAGE_GATE_FREE_BYTES:{free}')
    source=Path(item['source_path'])
    if not source.is_file() or sha(source)!=item['source_sha256']:raise RuntimeError('E_SOURCE_LINEAGE')
    workspace=WORKSPACES/item['asset_id'];workspace.mkdir(parents=True,exist_ok=True)
    build_legacy(item,workspace)
    ov=KW.get(item['asset_id'])
    started=time.time()
    kwargs=dict(workspace=workspace,source_path=source,provider_id='nexabot-web',
      expected_source_sha256=item['source_sha256'],upscale_fn=upscale_fn,send_fn=None)
    if ov: kwargs['metadata_overrides']=ov
    result=fo.postprocess_raster_workspace(**kwargs)
    row={
      'schema':'die.h01.nexaburst.v2-result.v1','asset_id':item['asset_id'],'job_id':item['job_id'],
      'status':result['status'],'workspace':str(workspace),'listing_path':result.get('listing_path'),
      'state_path':result.get('state_path'),'elapsed_sec':round(time.time()-started,3),
      'kw_override':bool(ov),
      'completed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    }
    atomic(workspace/'nexaburst-v2-result.json',row);append(DONE,row)
    if row['status']=='WAITING_FOUNDER_QC':
        notify('ARTIFACT_READY',
               f"Object: {item.get('noun','unknown')}\n"
               f"Asset: {row['asset_id']}\n"
               f"Lane: PSR-L0\n"
               f"State: WAITING_FOUNDER_QC\n"
               f"KW-override: {bool(ov)}\n"
               f"Post-process: {row['elapsed_sec']}s\n"
               f"Vault: queued for archive verification")
    print(json.dumps(row));return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--once',action='store_true');ap.add_argument('--continuous',action='store_true');ap.add_argument('--poll-seconds',type=int,default=10);ap.add_argument('--asset-id',default='')
    ap.add_argument('--shard',default='0/1',help='asset shard i/n for parallel workers')
    args=ap.parse_args()
    global SHARD,LOCK
    si,sn=(int(x) for x in args.shard.split('/'))
    assert 0<=si<sn,'bad shard'
    SHARD=(si,sn)
    if sn>1: LOCK=ROOT/'state'/f'v2-worker-psr-{si}of{sn}.lock'
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open('w') as lf:
        fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            rows=pending(args.asset_id or None)
            if rows:
                try:process_item(rows[0])
                except Exception as exc:
                    asset=rows[0].get('asset_id'); err=str(exc)
                    append(ROOT/'state'/'v2-errors.jsonl',{'schema':'die.h01.nexaburst.v2-error.v1','asset_id':asset,'error':err,'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
                    count=error_count(asset)
                    print(json.dumps({'status':'ERROR','asset_id':asset,'error':err,'attempt':count}),file=sys.stderr)
                    if err.startswith('E_SOURCE_LINEAGE'):
                        add_hold(asset)
                        notify('FOUNDER_ACTION_REQUIRED',f'PSR asset blocked by source-lineage mismatch. asset={asset} error={err}')
                    elif count >= 2:
                        add_hold(asset)
                        notify('FOUNDER_ACTION_REQUIRED',f'PSR V2 failed twice and is now held. asset={asset} error={err}')
                    else:
                        notify('V2_RETRY_SCHEDULED',f'PSR asset={asset} attempt={count}/2 retry_in=120s error={err[:240]}')
                        if args.continuous: time.sleep(120)
                    if args.once:return 2
            elif args.once:return 0
            if not args.continuous:return 0
            time.sleep(max(1,args.poll_seconds))
if __name__=='__main__':raise SystemExit(main())
