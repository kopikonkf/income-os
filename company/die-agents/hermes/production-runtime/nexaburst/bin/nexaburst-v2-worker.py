#!/opt/die/factory-asset/venv/bin/python
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, sys, time, fcntl, shutil
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst')
QUEUE=ROOT/'state'/'v2-queue.jsonl'
DONE=ROOT/'state'/'v2-done.jsonl'
LOCK=ROOT/'state'/'v2-worker.lock'
WORKSPACES=ROOT/'workspaces'
FO=Path('/srv/die/company/die-agents/hermes/production-runtime/factory_orchestration_v2.py')
AU=Path('/srv/die/bridge/income_os_bridge/asset_upscale.py')
POLICY=Path('/srv/die/company/atlas/object-centric/object-asset-engine/source/scripts/postprocess/upscale-policy.v1.json')

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader;sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
fo=loadmod('nexaburst_fo',FO)
au=loadmod('nexaburst_au',AU)
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
def safe(text):
    import re
    return (re.sub(r'[^A-Z0-9_]+','_',str(text).upper()).strip('_')[:48] or 'ASSET')

def build_legacy(item,workspace):
    noun=item['noun'];style=item.get('style','isolated-object');asset=item['asset_id']
    receipt=json.loads(Path(item['generation_receipt']).read_text(encoding='utf-8'))
    prompt=receipt['prompt']
    bp={
      'schema_version':'die.production.family-blueprint.v1',
      'request_id':'NEXABURST-'+safe(asset),
      'blueprint_id':'BP-NEXABURST-'+safe(asset),
      'task_id':asset,'mission_id':'M-001',
      'repository_sha':'RUNTIME_ISOLATED_NEXABURST',
      'principal':{'principal_id':'h01-nexaburst','role':'PROVIDER_ADAPTER'},
      'seed':{'id':asset,'canonical_name':noun,'object_class':'concrete_visual','category_path':'object_atlas.nexaburst','asset_tier':'U1-raster','demand_status':'atlas_candidate','demand_score':0.0},
      'family':{
        'family_id':'FAM-NEXABURST-'+safe(style),
        'family_thesis':f'{style} object-atlas stock component family.',
        'buyer_persona':['stock designers','content creators'],
        'use_cases':['isolated design component','commercial stock composition'],
        'commercial_use_hypothesis':'Object Atlas production hypothesis pending marketplace evidence.',
        'evidence_status':'OBJECT_ATLAS_PRODUCTION_CANARY'
      },
      'production':{
        'asset_type':'RASTER_IMAGE','batch_size':1,'engine':'NEXABURST/nexaburst-p001',
        'master_prompt':prompt,
        'negative_constraints':['no logos','no trademarks','no brands','no watermark','no extra objects'],
        'semantic_variation_plan':[{'variation_id':'VAR-001','dimension':'style','instruction':style,'commercial_rationale':'Bounded Object Atlas style lane.'}]
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
      'executive_review_id':'RUNTIME_NEXABURST_CANARY',
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

def pending():
    if not QUEUE.is_file():return []
    done=processed_ids();rows=[]
    for line in QUEUE.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        try:d=json.loads(line)
        except Exception:continue
        if d.get('asset_id') not in done:rows.append(d)
    return rows

def process_item(item):
    free=shutil.disk_usage(ROOT).free
    min_free=20*1024**3
    try:
        cfg=json.loads((SESSION/'config'/'nexaburst.json').read_text(encoding='utf-8'))
        min_free=int(cfg.get('v2_min_free_gib',20))*1024**3
    except Exception:
        pass
    if free < min_free:
        raise RuntimeError(f'E_V2_STORAGE_GATE_FREE_BYTES:{free}')
    source=Path(item['source_path'])
    if not source.is_file() or sha(source)!=item['source_sha256']:raise RuntimeError('E_SOURCE_LINEAGE')
    workspace=WORKSPACES/item['asset_id'];workspace.mkdir(parents=True,exist_ok=True)
    build_legacy(item,workspace)
    started=time.time()
    result=fo.postprocess_raster_workspace(
      workspace=workspace,source_path=source,provider_id='nexabot-web',
      expected_source_sha256=item['source_sha256'],upscale_fn=upscale_fn,send_fn=None
    )
    row={
      'schema':'die.h01.nexaburst.v2-result.v1','asset_id':item['asset_id'],'job_id':item['job_id'],
      'status':result['status'],'workspace':str(workspace),'listing_path':result.get('listing_path'),
      'state_path':result.get('state_path'),'elapsed_sec':round(time.time()-started,3),
      'completed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    }
    atomic(workspace/'nexaburst-v2-result.json',row);append(DONE,row);print(json.dumps(row));return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--once',action='store_true');ap.add_argument('--continuous',action='store_true');ap.add_argument('--poll-seconds',type=int,default=10)
    args=ap.parse_args()
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open('w') as lf:
        fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            rows=pending()
            if rows:
                try:process_item(rows[0])
                except Exception as exc:
                    append(ROOT/'state'/'v2-errors.jsonl',{'schema':'die.h01.nexaburst.v2-error.v1','asset_id':rows[0].get('asset_id'),'error':str(exc),'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
                    print(json.dumps({'status':'ERROR','asset_id':rows[0].get('asset_id'),'error':str(exc)}),file=sys.stderr)
                    if args.once:return 2
            elif args.once:return 0
            if not args.continuous:return 0
            time.sleep(max(1,args.poll_seconds))
if __name__=='__main__':raise SystemExit(main())
