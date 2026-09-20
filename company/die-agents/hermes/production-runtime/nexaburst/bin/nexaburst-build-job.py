#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HOLD=ROOT/'config'/'lane23-activation-hold.v1.json'

class JobError(RuntimeError): pass

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def load(p:Path):return json.loads(p.read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--compiled',required=True,type=Path)
    ap.add_argument('--profile',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    hold=load(HOLD)
    compiled=load(args.compiled);profile=load(args.profile)
    if compiled.get('dispatch_authorized') is not False:raise JobError('E_COMPILED_AUTHORITY_UNEXPECTED')
    if profile.get('activation')!='PREPARED_NOT_AUTHORIZED':raise JobError('E_PROFILE_ACTIVATION_UNEXPECTED')
    engine=str(compiled['contract']['engine_id'])
    if engine!=profile.get('engine_id'):raise JobError('E_ENGINE_PROFILE_MISMATCH')
    final_prompt=str(compiled.get('final_provider_prompt') or '')
    if not final_prompt:raise JobError('E_FINAL_PROVIDER_PROMPT_MISSING')
    if sha(final_prompt.encode())!=compiled.get('final_provider_prompt_sha256'):raise JobError('E_FINAL_PROMPT_HASH_MISMATCH')
    aspect=1.0 if compiled['kind']=='OBJECT_EXPRESSION' else 1.5
    job={
      'schema':'die.h01.nexaburst.prepared-job.v1','status':'PREPARED_NOT_AUTHORIZED',
      'engine_id':engine,'profile_id':profile['profile_id'],'semantic_asset_id':compiled['semantic_asset_id'],
      'kind':compiled['kind'],'lane_id':compiled['lane_id'],'family_id':compiled.get('family_id'),
      'contract_sha256':compiled['contract_sha256'],'prompt_authority':compiled['contract']['authority'],
      'final_provider_prompt':final_prompt,'final_provider_prompt_sha256':compiled['final_provider_prompt_sha256'],
      'requested_output':{'provider_mode':'img','media_family':'RASTER','aspect':aspect},
      'provider_boundary':{'landing_url':profile['landing_url'],'cdp_host':profile['cdp_host'],'cdp_port':profile['cdp_port']},
      'roots':{'raw_root':profile['raw_root'],'receipt_root':profile['receipt_root'],'workspace_root':profile['workspace_root']},
      'dispatch_authorized':False,'hold_status':hold['status'],
      'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(job,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'JOB_PREPARED_NOT_AUTHORIZED','semantic_asset_id':job['semantic_asset_id'],
                      'profile_id':job['profile_id'],'final_provider_prompt_sha256':job['final_provider_prompt_sha256'],
                      'dispatch_authorized':False},sort_keys=True))
if __name__=='__main__':
    try:main()
    except JobError as e:raise SystemExit(str(e))
