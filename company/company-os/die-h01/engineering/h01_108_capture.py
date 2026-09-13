#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
import sys;sys.path.insert(0,str(H01/'engineering'))
from provider_output_acquisition import acquire_svg_text
from native_svg_request_contract import build_request
from svg_prompt_composer_v2 import sha256_value
now=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ap.add_argument('--provider',required=True);ap.add_argument('--source-kind',choices=['TEXT','FILE'],required=True);ap.add_argument('--source',required=True);ap.add_argument('--job-id',required=True);ap.add_argument('--profile-id',required=True);ap.add_argument('--udd-id',required=True);ns=ap.parse_args()
 w=Path(ns.workspace);f=w/'final';f.mkdir(parents=True,exist_ok=True);bp=json.loads((w/'blueprint.json').read_text());mi=json.loads((w/'master-instruction.json').read_text());pp=json.loads((w/'provider-prompt.json').read_text());it=json.loads((w/'batch-item.json').read_text());done=now();bph=sha256_value(bp)
 req=build_request(request_id=f'H01SVGREQ-{ns.job_id}',queue_item_id=it['queue_item_id'],source_candidate_id=it['source_candidate_id'],semantic_asset_id=bp['semantic_asset_id'],provider_id=ns.provider,provider_profile=f'{ns.provider.upper()}_WEB_P001',blueprint_id=bp['blueprint_id'],blueprint_sha256=bph,master_instruction_sha256=mi['master_instruction_sha256'],provider_prompt=pp['prompt'],provider_prompt_sha256=pp['prompt_sha256']);dump(f/'native-svg-request.json',req)
 src=Path(ns.source)
 if ns.source_kind=='TEXT':
  raw=src.read_text().rstrip('\n');acq,_=acquire_svg_text(job_id=ns.job_id,request_id=req['request_id'],provider_id=ns.provider,profile_id=ns.profile_id,provider_status='COMPLETED',provider_response_text=raw,output_dir=f,completion_signal='SVG_COMPLETE_STABLE_NO_STOP',completed_at=done,finish_reason='PROVIDER_UI_TERMINAL');original=(f/'provider-original.svg').read_bytes();acq_method='TEXT_SVG'
 else:
  original=src.read_bytes();target=f/'provider-original.svg';
  if target.exists() and target.read_bytes()!=original:raise SystemExit('E_PROVIDER_ORIGINAL_COLLISION')
  if not target.exists():target.write_bytes(original)
  dump(f/'provider-file-acquisition.receipt.json',{'schema':'die.h01.provider-native-svg-file-acquisition.v1','status':'SUCCEEDED','job_id':ns.job_id,'provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'source_kind':'PROVIDER_FILE_DOWNLOAD','mime':'image/svg+xml','acquisition_method':'UI_DOWNLOAD_SVG','artifact':{'path':str(target),'sha256':sha(original),'bytes':len(original),'immutable_provider_original':True},'cookies_or_tokens_read':False,'session_bytes_read':False,'completed_at':done});acq_method='NATIVE_SVG'
 rec={'schema':'die.h01.h01-108-artifact-created.v1','task_id':'H01-108','status':'ARTIFACT_CREATED','job_id':ns.job_id,'batch_position':it['batch_position'],'noun':it['canonical_name'],'provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'provider_original_path':str(f/'provider-original.svg'),'provider_original_sha256':sha(original),'provider_original_bytes':len(original),'classification':acq_method,'semantic_asset_id':bp['semantic_asset_id'],'created_at':done,'postproduction_state':'PENDING','submission_authorized':False,'publication_authorized':False};dump(w/'artifact-created.receipt.json',rec)
 job={'schema':'die.h01.browser-job-result.v1','job_id':ns.job_id,'job_kind':'H01_108_PRODUCTION','provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'terminal_state':'SUCCEEDED','completed_at':done,'classification':acq_method,'provider_original_sha256':sha(original),'semantic_asset_id':bp['semantic_asset_id'],'production_boundary':'ARTIFACT_CREATED','postproduction_required':True,'authority':{'provider_generation_dispatched':True,'submission_authorized':False,'publication_authorized':False}};dump(w/'browser-job-result.json',job)
 print(json.dumps(rec))
if __name__=='__main__':main()
