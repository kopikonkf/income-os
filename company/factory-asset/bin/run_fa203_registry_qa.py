#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
from typing import Any
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,LIB/filename);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
state_manager=load('fa203_state_manager','factory_state_manager.py')
derivqa=load('fa203_derivqa','derivative_qa.py')
post=load('fa203_post','postproduction_state.py')

F=ROOT/'company/factory-asset/fixtures/governed-canary'
FA202_RESULT=F/'FA-202-live-result.json'
FA202_MUXIA=F/'FA-202-muxia-dispatch-receipt.json'
FA202_UPSCALE=F/'FA-202-realesrgan-x4-receipt.json'
BLUEPRINT=F/'FA-201-shopping-bag-blueprint-v2.json'
PROFILES=ROOT/'company/factory-asset/registries/marketplace-delivery-profiles.v1.json'
REGISTRY=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
ORCH=F/'FA-203-postproduction-state.json'
RESULT=F/'FA-203-registry-qa-result.json'

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def sha_json(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def atomic_json(path:Path,value:Any):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def master_qa(path:Path,expected_sha:str)->dict[str,Any]:
    data=path.read_bytes();magic=data.startswith(b'\x89PNG\r\n\x1a\n');actual=sha_file(path)
    with Image.open(path) as im:
        im.load();dims=list(im.size);fmt=im.format;mode=im.mode
    failures=[]
    if actual!=expected_sha:failures.append('SHA256_MISMATCH')
    if not magic or fmt!='PNG':failures.append('FORMAT_MISMATCH')
    if dims!=[4096,4096]:failures.append('DIMENSIONS_MISMATCH')
    if mode not in {'RGB','RGBA'}:failures.append('COLOR_MODE_UNEXPECTED')
    return {'schema':'die.factory-asset.fa203-master-technical-qa.v1','result':'PASS' if not failures else 'FAIL','failures':failures,'sha256':actual,'bytes':path.stat().st_size,'format':fmt,'dimensions':dims,'mode':mode,'magic_mime_match':magic,'decode_reopen':True,'color_space_contract':'SRGB_BLUEPRINT_EXPECTATION'}

def build_orchestration(*,provider_sha:str,master_sha:str,derivatives:list[dict[str,Any]])->dict[str,Any]:
    if ORCH.exists():
        d=post.load_state(ORCH)
        if d.get('state')!='TECHNICAL_QA_PASS' or d.get('active_master_sha256')!=master_sha:raise RuntimeError('E_ORCHESTRATION_EXISTING_CONFLICT')
        return d
    d=post.create_state(ORCH,job_id='FA-203',semantic_asset_id='FASA-SHOPPING_BAG_FULFILLMENT_ISOLATED',blueprint_id='FABP-FA200_SHOPPING_BAG_FULFILLMENT',source_master_sha256=provider_sha)
    d=post.advance(ORCH,target_state='MASTER_VALIDATED',evidence={'result':'PASS','master_sha256':provider_sha},event_id='FA203-MASTER-VALIDATED',expected_revision=d['revision'])
    d=post.advance(ORCH,target_state='UPSCALE_DECIDED',evidence={'result':'PASS','source_sha256':provider_sha,'source_unchanged':True,'final_sha256':master_sha},event_id='FA203-UPSCALE-DECIDED',expected_revision=d['revision'])
    rows=[{'derivative_id':x['derivative_id'],'sha256':x['sha256'],'master_sha256':master_sha} for x in derivatives]
    d=post.advance(ORCH,target_state='DERIVATIVES_READY',evidence={'master_sha256':master_sha,'derivatives':rows},event_id='FA203-DERIVATIVES-READY',expected_revision=d['revision'])
    qa=[{'derivative_id':x['derivative_id'],'sha256':x['sha256'],'result':'PASS'} for x in derivatives]
    d=post.advance(ORCH,target_state='TECHNICAL_QA_PASS',evidence={'result':'PASS','derivatives':qa},event_id='FA203-TECHNICAL-QA-PASS',expected_revision=d['revision'])
    return d

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--fa202-workspace',type=Path,required=True);args=ap.parse_args();w=args.fa202_workspace.resolve()
    live=json.loads(FA202_RESULT.read_text());mux=json.loads(FA202_MUXIA.read_text());up=json.loads(FA202_UPSCALE.read_text());bp=json.loads(BLUEPRINT.read_text());profiles=json.loads(PROFILES.read_text())
    sid=live['semantic_asset_id'];master_sha=live['master']['sha256'];provider_sha=live['provider_original']['sha256']
    if sid!='FASA-SHOPPING_BAG_FULFILLMENT_ISOLATED':raise RuntimeError('E_SEMANTIC_ASSET_ID')
    # Verify live bytes remain identical to canonical FA-202 evidence.
    paths={'provider':w/'provider/source-original.png','master':w/'master/master.png','ADOBE_JPEG':w/'derivatives/adobe-jpeg.jpg','PNG_PREVIEW':w/'derivatives/png-preview.png','WEBP_PREVIEW':w/'derivatives/webp-preview.webp'}
    expected={'provider':provider_sha,'master':master_sha,**{k:v['receipt']['output']['sha256'] for k,v in live['derivatives'].items()}}
    for k,p in paths.items():
        if not p.is_file() or sha_file(p)!=expected[k]:raise RuntimeError(f'E_LIVE_ARTIFACT_DRIFT:{k}')
    mqa=master_qa(paths['master'],master_sha)
    if mqa['result']!='PASS':raise RuntimeError('E_MASTER_QA')
    drows=[]
    fmts={'ADOBE_JPEG':'JPEG','PNG_PREVIEW':'PNG','WEBP_PREVIEW':'WEBP'}
    for did in ('ADOBE_JPEG','PNG_PREVIEW','WEBP_PREVIEW'):
        rec=live['derivatives'][did]['receipt'];q=derivqa.inspect_derivative(paths[did],expected_format=fmts[did],expected_dimensions=(4096,4096),expected_alpha='ABSENT',expected_sha256=rec['output']['sha256'])
        if q['result']!='PASS':raise RuntimeError(f'E_DERIVATIVE_QA:{did}')
        drows.append({'derivative_id':did,'format':fmts[did],'purpose':rec['output'].get('purpose') or ('MARKETPLACE_DELIVERY' if did=='ADOBE_JPEG' else 'PREVIEW'),'recipe_id':rec['recipe_id'],'sha256':q['sha256'],'bytes':q['bytes'],'dimensions':q['dimensions'],'technical_qa':'PASS','semantic_identity_effect':'NONE','compatibility':'COMPATIBLE'})
    # Conditional upscale evidence: 1254px original required the accepted x4 recovery; master is deterministic 4096 normalization.
    upscale_ok=(up.get('status')=='PASS' and up.get('action')=='UPSCALE_X4' and up.get('source',{}).get('sha256')==provider_sha and up.get('model',{}).get('sha256')=='8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292')
    if not upscale_ok:raise RuntimeError('E_UPSCALE_EVIDENCE')
    adobe=next(x for x in profiles['profiles'] if x['platform_id']=='ADOBE_STOCK')
    delivery_formats={str(x).upper().replace('JPG','JPEG') for x in adobe['delivery']['raster']}
    jpeg=next(x for x in drows if x['derivative_id']=='ADOBE_JPEG')
    if adobe['profile_state']!='EVIDENCE_PINNED' or jpeg['format'] not in delivery_formats:raise RuntimeError('E_ADOBE_COMPATIBILITY')
    package_compat={'schema':'die.factory-asset.fa203-package-compatibility.v1','state':'TECHNICALLY_COMPATIBLE_METADATA_RIGHTS_PENDING','marketplace':'ADOBE_STOCK','profile_revision':profiles['revision'],'profile_state':adobe['profile_state'],'marketplace_delivery_derivative_id':'ADOBE_JPEG','marketplace_delivery_format':'JPEG','preview_derivatives':['PNG_PREVIEW','WEBP_PREVIEW'],'package_ready':False,'blocking_next':['METADATA_PENDING_FA204','RIGHTS_REVIEW_PENDING_FA204'],'submission_authorized':False,'publication_authorized':False}
    capacity={'kind':'PROVIDER','route_class':'PROVIDER_ROUTER','provider_id':'chatgpt','cluster_id':'cluster-a','profile_id':'chatgpt-linux-a','transport':'BROWSER_CDP','state':'OBSERVED_SUCCESS','capacity_state_at_observation':'AVAILABLE','observed_at':mux['completed_at'],'evidence_ref':'company/factory-asset/fixtures/governed-canary/FA-202-muxia-dispatch-receipt.json','evidence_type':'OBSERVED_SUCCESS_NOT_QUOTA_GUESS','freshness':'STALE_FOR_CURRENT_ROUTING_RETAINED_AS_ACCEPTANCE_EVIDENCE','routing_eligible_now':False,'native_capacity_required':False}
    orch=build_orchestration(provider_sha=provider_sha,master_sha=master_sha,derivatives=drows)
    proposal=live['master']['staging']['state_manager_proposal']
    staged=Path(proposal['staged_blob_path'])
    if not staged.is_file() or sha_file(staged)!=master_sha:raise RuntimeError('E_STAGED_MASTER_DRIFT')
    evidence={'schema':'die.factory-asset.asset-registry-commit-evidence.v1','semantic_asset_id':sid,'blueprint_id':bp['blueprint_id'],'master':{'sha256':master_sha,'format':'PNG','dimensions':[4096,4096],'technical_qa':'PASS','qa':mqa,'provider_original_sha256':provider_sha,'upscale':{'required':True,'decision':'UPSCALE_X4','receipt_ref':'company/factory-asset/fixtures/governed-canary/FA-202-realesrgan-x4-receipt.json'}},'derivatives':drows,'package_compatibility':package_compat,'capacity':capacity,'orchestration':{'state':orch['state'],'revision':orch['revision'],'state_sha256':sha_file(ORCH),'next_task':'FA-204'},'authority':{'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'spend_usd':0}}
    first=state_manager.commit_asset(registry_path=REGISTRY,proposal=proposal,evidence=evidence,writer_id='DIE_STATE_MANAGER')
    replay=state_manager.commit_asset(registry_path=REGISTRY,proposal=proposal,evidence=evidence,writer_id='DIE_STATE_MANAGER')
    reg=state_manager.load_registry(REGISTRY)
    if replay['result']!='IDEMPOTENT_REUSE' or len(reg['assets'])!=1 or len(reg['physical_masters'])!=1:raise RuntimeError('E_DUPLICATE_SUPPRESSION')
    result={'schema':'die.factory-asset.fa203-registry-qa-result.v1','result':'PASS','task_id':'FA-203','semantic_asset_id':sid,'canonical_writer_commit':first,'canonical_writer_replay':replay,'registry':{'path':'company/factory-asset/registries/governed-canary-assets.v1.json','revision':reg['revision'],'semantic_asset_count':len(reg['assets']),'physical_master_count':len(reg['physical_masters']),'canonical_truth':True,'committed_by':'DIE_STATE_MANAGER'},'master_qa':mqa,'upscale':{'decision':'UPSCALE_X4_REQUIRED_AND_PASS','provider_original_dimensions':[1254,1254],'active_master_dimensions':[4096,4096],'model_sha256':up['model']['sha256']},'derivatives':drows,'package_compatibility':package_compat,'duplicate_suppression':{'same_semantic_commit_replay':'IDEMPOTENT_REUSE','semantic_asset_count_after_replay':len(reg['assets']),'physical_master_count_after_replay':len(reg['physical_masters'])},'capacity':capacity,'orchestration':{'state':orch['state'],'revision':orch['revision'],'state_sha256':sha_file(ORCH),'next_task':'FA-204'},'authority':evidence['authority'],'rights_state':'REVIEW_REQUIRED','metadata_state':'PENDING_FA204','provider_calls_performed':False}
    atomic_json(RESULT,result);print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())