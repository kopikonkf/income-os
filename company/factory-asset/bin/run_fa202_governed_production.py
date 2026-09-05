#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path
from typing import Any
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,LIB/filename);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
expr=load('fa202_expr','asset_expression_plan.py')
router=load('fa202_router','semantic_producer_router.py')
provider_original=load('fa202_provider_original','provider_original.py')
ingestion=load('fa202_ingestion','master_ingestion.py')
raster=load('fa202_raster','raster_derivative.py')
derivqa=load('fa202_derivqa','derivative_qa.py')

PLAN=ROOT/'company/factory-asset/fixtures/governed-canary/FA-200-shopping-bag-expression-plan.json'
BLUEPRINT=ROOT/'company/factory-asset/fixtures/governed-canary/FA-201-shopping-bag-blueprint-v2.json'
PROD=ROOT/'company/factory-asset/fixtures/governed-canary/FA-201-shopping-bag-production-plan.json'
LOCK=ROOT/'company/factory-asset/fixtures/governed-canary/FA-201-shopping-bag-blueprint-lock.json'
POLICY=Path('/srv/die/company/atlas/object-centric/object-asset-engine/source/scripts/postprocess/upscale-policy.v1.json')
UPSCALE=Path('/srv/die/bridge/income_os_bridge/asset_upscale.py')
DISPATCH=Path('/srv/die/company/muxia/scripts/linux/die-muxia-image-dispatch.py')

def sha_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def sha_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def csha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def atomic_json(path:Path,value:Any):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');os.replace(tmp,path)
def write_once_json(path:Path,value:dict):
    if path.exists():
        old=json.loads(path.read_text())
        if old!=value:raise RuntimeError(f'E_IMMUTABLE_JSON_CONFLICT:{path}')
        return True
    atomic_json(path,value);return False

def deterministic_prompt(plan:dict,bp:dict)->str:
    e=plan['expressions'][0]
    assert e['semantic_asset_id']==bp['semantic_identity']['semantic_asset_id']
    return (
      f"Create one photorealistic {e['product_expression'].lower()}. "
      "Show a single neutral kraft-paper shopping bag, front three-quarter studio view, centered and fully visible, with clean realistic handles. "
      "Pure white seamless background, soft commercial studio lighting, crisp edges, realistic paper texture, generous copy space, square composition. "
      "No people, no hands, no text, no logos, no trademarks, no brands, no watermark, no decorative graphics, no extra objects."
    )

def recipe(recipe_id:str,fmt:str,purpose:str,master_sha:str,sid:str,*,quality:int=92,alpha_policy:str='NOT_APPLICABLE')->dict:
    return {'schema':'die.factory-asset.derivative-recipe.v1','recipe_id':recipe_id,'recipe_version':'1.0.0','input':{'master_sha256':master_sha,'semantic_asset_id':sid,'format':'PNG'},'output':{'format':fmt,'purpose':purpose,'width_px':4096,'height_px':4096,'color_space':'SRGB','alpha_policy':alpha_policy,'quality':quality,'semantic_identity_effect':'NONE'},'marketplace_profile':{'platform_id':'ADOBE_STOCK','profile_revision':'1.0'},'idempotency':{'key_material':['master_sha256','recipe_id','recipe_version','marketplace_profile.platform_id','marketplace_profile.profile_revision','output'],'output_collision_action':'VERIFY_HASH_AND_REUSE_OR_FAIL'},'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256':True,'dimensions_if_raster':True},'compatibility':{'unknown_action':'BLOCK_PACKAGE','require_profile_match':True}}

def render_or_reuse(master:Path,out:Path,rec_path:Path,rec:dict)->tuple[dict,bool]:
    key=raster.canonical_idempotency_key(rec)
    if out.exists() or rec_path.exists():
        if not out.is_file() or not rec_path.is_file():raise RuntimeError(f'E_DERIVATIVE_PARTIAL:{out}')
        old=json.loads(rec_path.read_text())
        if old.get('idempotency_key')!=key or old.get('output',{}).get('sha256')!=sha_file(out):raise RuntimeError(f'E_DERIVATIVE_REUSE_CONFLICT:{out}')
        return old,True
    result=raster.render_raster_derivative(master,out,rec)
    atomic_json(rec_path,result)
    return result,False

def copy_master_preview(master:Path,out:Path,rec_path:Path,sid:str)->tuple[dict,bool]:
    key=csha({'master_sha256':sha_file(master),'recipe_id':'raster-png-export-v1','semantic_asset_id':sid,'format':'PNG','dimensions':[4096,4096]})
    if out.exists() or rec_path.exists():
        if not out.is_file() or not rec_path.is_file():raise RuntimeError('E_PNG_PREVIEW_PARTIAL')
        old=json.loads(rec_path.read_text())
        if old.get('idempotency_key')!=key or old['output']['sha256']!=sha_file(out) or out.read_bytes()!=master.read_bytes():raise RuntimeError('E_PNG_PREVIEW_CONFLICT')
        return old,True
    out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(master,out)
    result={'schema':'die.factory-asset.derivative-receipt.v1','recipe_id':'raster-png-export-v1','recipe_version':'1.0.0','idempotency_key':key,'input':{'master_sha256':sha_file(master),'semantic_asset_id':sid},'marketplace_profile':{'platform_id':'ADOBE_STOCK','profile_revision':'1.0'},'output':{'format':'PNG','sha256':sha_file(out),'bytes':out.stat().st_size,'width_px':4096,'height_px':4096,'semantic_identity_effect':'NONE'},'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256_verified':True,'failure_code':None},'compatibility':{'state':'COMPATIBLE','reason':None},'result':'PASS'}
    atomic_json(rec_path,result);return result,False

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=Path,required=True);args=ap.parse_args();w=args.workspace.resolve();w.mkdir(parents=True,exist_ok=True)
    plan=json.loads(PLAN.read_text());bp=json.loads(BLUEPRINT.read_text());prod=json.loads(PROD.read_text());lock=json.loads(LOCK.read_text());expr.validate_asset_expression_plan(plan)
    sid=bp['semantic_identity']['semantic_asset_id'];frozen_sha=router.canonical_sha256(bp)
    if frozen_sha!=prod['blueprint_sha256'] or frozen_sha!=lock['blueprint']['canonical_blueprint_sha256']:raise RuntimeError('E_FROZEN_BLUEPRINT_DRIFT')
    semantic_route=router.route_frozen_expression(plan=plan,semantic_asset_id=sid,blueprint=bp,frozen_blueprint_sha256=frozen_sha)
    if semantic_route['route_kind']!='PROVIDER_ROUTER':raise RuntimeError('E_PROVIDER_ROUTE_REQUIRED')
    prompt=deterministic_prompt(plan,bp);prompt_sha=sha_bytes(prompt.encode())
    job=w.name
    dispatch_bp={'schema':'die.factory-asset.fa202-provider-dispatch.v1','task_id':job,'semantic_asset_id':sid,'frozen_blueprint_id':bp['blueprint_id'],'frozen_blueprint_sha256':frozen_sha,'semantic_route':{'route_kind':semantic_route['route_kind'],'dispatch_adapter':semantic_route['dispatch_adapter'],'dispatch_key':semantic_route['dispatch_key']},'concrete_provider_route':{'provider_id':'chatgpt','cluster_id':'cluster-a','transport':'BROWSER_CDP','runtime_owner':'MUXIA','selection_basis':'FA117_LIVE_ACCEPTED_MUXIA_EXPORT_BOUNDARY'},'production':{'engine':'MUXIA/chatgpt-linux-a','master_prompt':prompt},'authority':{'provider_call_authorized_for_fa202':True,'submission_authorized':False,'publication_authorized':False,'spend_usd':0}}
    dispatch_sha=csha(dispatch_bp);dispatch_lock={'schema':'die.factory-asset.fa202-provider-dispatch-lock.v1','task_id':job,'blueprint_sha256':dispatch_sha,'prompt_sha256':prompt_sha,'frozen_blueprint_sha256':frozen_sha}
    write_once_json(w/'blueprint.json',dispatch_bp);write_once_json(w/'blueprint.lock.json',dispatch_lock)
    muxia_receipt=Path('/var/lib/muxia/state/receipts')/f'{job}-muxia.json';provider_call_performed=not muxia_receipt.is_file()
    cp=subprocess.run([sys.executable,str(DISPATCH),job],text=True,capture_output=True,timeout=720,check=False)
    if cp.returncode!=0:raise RuntimeError('E_PROVIDER_DISPATCH:'+(cp.stderr or cp.stdout)[-1000:])
    dispatch=json.loads(cp.stdout.strip().splitlines()[-1]);source=Path(dispatch['export_artifact_path'])
    if dispatch.get('status')!='SUCCEEDED' or not source.is_file() or sha_file(source)!=dispatch['sha256']:raise RuntimeError('E_PROVIDER_EXPORT_INVALID')
    provider_sha=dispatch['sha256'];provider_bytes_before=source.read_bytes()
    intake=provider_original.intake_provider_original(source_path=source,staging_root=w/'master-staging'/'provider-original',attempt_id=job+'-provider-original',semantic_asset_id=sid,blueprint_id=bp['blueprint_id'],provider_id='chatgpt',expected_sha256=provider_sha,declared_mime_type=str(dispatch.get('content_type','image/png')).split(';')[0])
    atomic_json(w/'provider-original-intake.json',intake)
    updir=w/'master-work';updir.mkdir(parents=True,exist_ok=True);x4=updir/'realesrgan-x4.png';uprec=updir/'realesrgan-x4.receipt.json'
    if x4.exists() and uprec.exists():
        ur=json.loads(uprec.read_text());
        if ur.get('source',{}).get('sha256')!=provider_sha or ur.get('output',{}).get('sha256')!=sha_file(x4):raise RuntimeError('E_UPSCALE_REUSE_CONFLICT')
        upscale_reused=True
    else:
        cp=subprocess.run([sys.executable,str(UPSCALE),'--source',str(source),'--output',str(x4),'--policy',str(POLICY),'--receipt',str(uprec),'--min-width','4096','--min-height','4096','--min-megapixels','16','--rights-state','PENDING_HUMAN_REVIEW','--safety-state','PENDING_HUMAN_REVIEW'],text=True,capture_output=True,timeout=1200,check=False)
        if cp.returncode!=0:raise RuntimeError('E_UPSCALE:'+(cp.stderr or cp.stdout)[-1000:])
        ur=json.loads(uprec.read_text());upscale_reused=False
    if ur.get('status')!='PASS' or not x4.is_file() or ur.get('output',{}).get('sha256')!=sha_file(x4):raise RuntimeError('E_UPSCALE_INVALID')
    active=w/'master'/'master.png';normrec=w/'master'/'master-normalization.json';x4sha=sha_file(x4)
    if active.exists() and normrec.exists():
        nr=json.loads(normrec.read_text())
        if nr.get('input_sha256')!=x4sha or nr.get('output_sha256')!=sha_file(active):raise RuntimeError('E_MASTER_REUSE_CONFLICT')
        master_reused=True
    else:
        with Image.open(x4) as im:
            im.load()
            if im.width!=im.height:raise RuntimeError(f'E_MASTER_ASPECT_NOT_SQUARE:{im.width}x{im.height}')
            out=im.convert('RGB').resize((4096,4096),Image.Resampling.LANCZOS)
            active.parent.mkdir(parents=True,exist_ok=True);out.save(active,format='PNG',compress_level=9)
        nr={'schema':'die.factory-asset.fa202-master-normalization.v1','method':'REALESRGAN_X4_THEN_LANCZOS_DOWNSAMPLE','input_sha256':x4sha,'input_dimensions':ur['output']['width_height'] if 'width_height' in ur.get('output',{}) else [ur['output']['width'],ur['output']['height']],'output_sha256':sha_file(active),'output_dimensions':[4096,4096],'semantic_asset_id':sid,'semantic_identity_effect':'NONE','provider_original_sha256':provider_sha,'provider_original_immutable':True};atomic_json(normrec,nr);master_reused=False
    if source.read_bytes()!=provider_bytes_before or sha_file(source)!=provider_sha:raise RuntimeError('E_PROVIDER_ORIGINAL_MUTATED')
    master_sha=sha_file(active)
    active_stage_root=w/'master-staging'/'active-master'
    active_attempt=active_stage_root/'attempt-receipts'/f'{job}-active-master.json'
    if active_attempt.is_file():
        master_stage=json.loads(active_attempt.read_text())
        if master_stage.get('source_sha256')!=master_sha or master_stage.get('semantic_asset_id')!=sid or master_stage.get('blueprint_id')!=bp['blueprint_id']:
            raise RuntimeError('E_ACTIVE_MASTER_STAGE_CONFLICT')
        staged_blob=Path(master_stage['staged_blob_path'])
        if not staged_blob.is_file() or sha_file(staged_blob)!=master_sha:
            raise RuntimeError('E_ACTIVE_MASTER_STAGE_BLOB_INVALID')
        active_stage_reused=True
    else:
        master_stage=ingestion.stage_master(source_path=active,staging_root=active_stage_root,attempt_id=job+'-active-master',semantic_asset_id=sid,blueprint_id=bp['blueprint_id'],expected_sha256=master_sha)
        active_stage_reused=False
    atomic_json(w/'active-master-ingestion.json',master_stage)
    deriv=w/'derivatives';deriv.mkdir(parents=True,exist_ok=True)
    jpg,jreuse=render_or_reuse(active,deriv/'adobe-jpeg.jpg',deriv/'adobe-jpeg.receipt.json',recipe('raster-jpeg-stock-v1','JPEG','MARKETPLACE_DELIVERY',master_sha,sid,quality=92,alpha_policy='FLATTEN_WHITE'))
    png,preuse=copy_master_preview(active,deriv/'png-preview.png',deriv/'png-preview.receipt.json',sid)
    web,wreuse=render_or_reuse(active,deriv/'webp-preview.webp',deriv/'webp-preview.receipt.json',recipe('raster-webp-preview-v1','WEBP','PREVIEW',master_sha,sid,quality=90,alpha_policy='FORBID'))
    qa={}
    for key,path,fmt,rec in [('ADOBE_JPEG',deriv/'adobe-jpeg.jpg','JPEG',jpg),('PNG_PREVIEW',deriv/'png-preview.png','PNG',png),('WEBP_PREVIEW',deriv/'webp-preview.webp','WEBP',web)]:
        q=derivqa.inspect_derivative(path,expected_format=fmt,expected_dimensions=(4096,4096),expected_alpha='ABSENT' if fmt in {'JPEG','WEBP'} else 'ANY',expected_sha256=rec['output']['sha256']);
        if q['result']!='PASS':raise RuntimeError(f'E_DERIVATIVE_QA:{key}')
        qa[key]=q
    result={'schema':'die.factory-asset.fa202-governed-production.v1','result':'PASS','task_id':job,'semantic_asset_id':sid,'semantic_asset_count':1,'packaging_variant_count':3,'frozen_blueprint_sha256':frozen_sha,'semantic_route':semantic_route,'provider_route':dispatch_bp['concrete_provider_route'],'prompt_sha256':prompt_sha,'provider_call_performed':provider_call_performed,'provider_original':{'path':str(source),'sha256':provider_sha,'bytes':source.stat().st_size,'media':intake['provider_original']['media'],'immutable_after_postprocess':sha_file(source)==provider_sha},'master':{'path':str(active),'sha256':master_sha,'dimensions':[4096,4096],'format':'PNG','lineage':{'provider_original_sha256':provider_sha,'realesrgan_x4_sha256':x4sha,'normalization_method':'REALESRGAN_X4_THEN_LANCZOS_DOWNSAMPLE'},'staging':master_stage,'active_stage_reused':active_stage_reused,'upscale_reused':upscale_reused,'master_reused':master_reused},'derivatives':{'ADOBE_JPEG':{'receipt':jpg,'idempotent_reuse':jreuse,'qa':qa['ADOBE_JPEG']},'PNG_PREVIEW':{'receipt':png,'idempotent_reuse':preuse,'qa':qa['PNG_PREVIEW']},'WEBP_PREVIEW':{'receipt':web,'idempotent_reuse':wreuse,'qa':qa['WEBP_PREVIEW']}},'authority':{'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'spend_usd':0},'rights_runtime_state':'REVIEW_REQUIRED','canonical_truth':False,'state_manager_commit_required':True}
    atomic_json(w/'fa202-result.json',result);print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())