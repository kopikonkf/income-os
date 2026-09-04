from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]

def load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

raster = load('fa029_raster','company/factory-asset/lib/raster_derivative.py')
pdf = load('fa029_pdf','company/factory-asset/lib/pdf_preview.py')
qa = load('fa029_qa','company/factory-asset/lib/derivative_qa.py')
package = load('fa029_package','company/factory-asset/lib/package_composer.py')
vector = load('fa029_vector','company/factory-asset/lib/vectorizability.py')

TARGET_W=3072
TARGET_H=2048

def recipe(master_sha: str, semantic_id: str, fmt: str, purpose: str, alpha: str) -> dict[str, Any]:
    return {
      'schema':'die.factory-asset.derivative-recipe.v1','recipe_id':f'fa029-{fmt.lower()}-{purpose.lower().replace("_","-")}-v1','recipe_version':'1.0.0',
      'input':{'master_sha256':master_sha,'semantic_asset_id':semantic_id,'format':'PNG'},
      'output':{'format':fmt,'purpose':purpose,'width_px':TARGET_W,'height_px':TARGET_H,'color_space':'SRGB','alpha_policy':alpha,'quality':90,'semantic_identity_effect':'NONE'},
      'marketplace_profile':{'platform_id':'FACTORY_CANARY','profile_revision':'1.0'},
      'idempotency':{'key_material':['master_sha256','recipe_id','recipe_version','marketplace_profile.platform_id','marketplace_profile.profile_revision','output'],'output_collision_action':'VERIFY_HASH_AND_REUSE_OR_FAIL'},
      'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256':True,'dimensions_if_raster':True},
      'compatibility':{'unknown_action':'BLOCK_PACKAGE','require_profile_match':True},
    }

def vector_evidence(path: Path) -> dict[str, Any]:
    bgr=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if bgr is None: raise RuntimeError(f'decode failed: {path}')
    small=cv2.resize(bgr,(256,171),interpolation=cv2.INTER_AREA)
    quant=(small//32).astype(np.uint8)
    color_count=int(min(9999,len(np.unique(quant.reshape(-1,3),axis=0))))
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,80,160)
    edge_complexity=float(np.count_nonzero(edges)/edges.size)
    contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    estimated_path_count=int(len([c for c in contours if cv2.contourArea(c)>=2]))
    return {'source_representation':'RASTER_PIXELS','declared_mode':'NOT_VECTORIZABLE','raster_trace_allowed':False,'photorealistic':True,'color_count':color_count,'edge_complexity':round(edge_complexity,6),'estimated_path_count':estimated_path_count,'has_text_or_fonts':False}

def run(inventory: Path, master_dir: Path, output_root: Path) -> dict[str, Any]:
    inv=json.loads(inventory.read_text(encoding='utf-8'))
    masters=inv['masters']
    if len(masters)!=5: raise RuntimeError(f'expected exactly 5 masters, got {len(masters)}')
    if output_root.exists(): shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    results=[]
    for item in masters:
        task=item['task_id']; local=master_dir/f'{task}.png'
        if not local.is_file(): raise RuntimeError(f'missing local master {local}')
        local_sha=raster.sha256_file(local)
        if local_sha!=item['sha256']: raise RuntimeError(f'copy hash mismatch {task}')
        semantic_id='FASA-'+task.replace('PROD','')+'-MASTER'
        a_dir=output_root/task/'pass-a'; b_dir=output_root/task/'pass-b'; a_dir.mkdir(parents=True); b_dir.mkdir(parents=True)
        with Image.open(local) as source_img:
            source_img.load(); source_has_alpha='A' in source_img.getbands(); source_meaningful_alpha=False
            if source_has_alpha:
                source_meaningful_alpha=source_img.getchannel('A').getextrema()[0] < 255
        defs=[('JPEG','MARKETPLACE_DELIVERY','FLATTEN_WHITE','jpg','ABSENT'),('WEBP','PREVIEW','PRESERVE','webp','PRESERVE_SOURCE'),('TIFF','COMPATIBILITY_EXPORT','PRESERVE','tiff','PRESERVE_SOURCE'),('PDF','PREVIEW','FLATTEN_WHITE','pdf','ABSENT')]
        der=[]; hash_matches={}
        for fmt,purpose,alpha,ext,expected_alpha in defs:
            rec=recipe(local_sha,semantic_id,fmt,purpose,alpha)
            pa=a_dir/f'asset.{ext}'; pb=b_dir/f'asset.{ext}'
            if fmt=='PDF':
                ra=pdf.render_pdf_derivative(local,pa,rec); rb=pdf.render_pdf_derivative(local,pb,rec)
            else:
                ra=raster.render_raster_derivative(local,pa,rec); rb=raster.render_raster_derivative(local,pb,rec)
            if ra['result']!='PASS' or rb['result']!='PASS': raise RuntimeError(f'derivative failure {task} {fmt}')
            hash_matches[fmt]=ra['output']['sha256']==rb['output']['sha256']
            alpha_expectation=('PRESENT' if source_meaningful_alpha else 'ANY') if expected_alpha=='PRESERVE_SOURCE' else expected_alpha
            q=qa.inspect_derivative(pa,expected_format=fmt,expected_dimensions=(TARGET_W,TARGET_H),expected_alpha=alpha_expectation,allowed_formats={'JPEG','WEBP','TIFF','PDF'},expected_sha256=ra['output']['sha256'])
            if q['result']!='PASS': raise RuntimeError(f'qa failure {task} {fmt}: {q}')
            der.append({'format':fmt,'purpose':purpose,'recipe_id':rec['recipe_id'],'idempotency_key':ra['idempotency_key'],'sha256':ra['output']['sha256'],'bytes':ra['output']['bytes'],'path':str(pa),'qa':q})
        if not all(hash_matches.values()): raise RuntimeError(f'idempotency mismatch {task}: {hash_matches}')
        deliverables=[{'derivative_id':f'{task}-{d["format"]}','source_path':d['path'],'format':d['format'],'purpose':d['purpose'],'recipe_id':d['recipe_id'],'receipt_ref':f'canary://{task}/{d["format"]}','compatibility_state':'COMPATIBLE'} for d in der]
        pkg=package.compose_dry_run_package(package_dir=output_root/task/'package',semantic_asset_id=semantic_id,master_sha256=local_sha,deliverables=deliverables,metadata_ref=f'metadata://{task}',rights_ref=f'rights://{task}',compatibility_receipt_ref=f'compat://{task}')
        evidence=vector_evidence(local); decision=vector.classify_vectorizability(evidence).as_dict()
        if decision['state']!='NOT_VECTORIZABLE': raise RuntimeError(f'unsafe vector outcome {task}: {decision}')
        results.append({'task_id':task,'seed_id':item['seed_id'],'blueprint_id':item['blueprint_id'],'blueprint_sha256':item['blueprint_sha256'],'linux_master_path':item['final_path'],'master_sha256':local_sha,'master_bytes':item['bytes'],'master_dimensions':item['dimensions'],'copy_hash_match':True,'source_has_alpha_channel':source_has_alpha,'source_meaningful_alpha':source_meaningful_alpha,'derivatives':der,'rerun_hash_matches':hash_matches,'package':pkg,'vector_gate':decision})
    # explicit duplicate suppression probe using two different entries with the same WEBP bytes
    first=results[0]; webp=next(d for d in first['derivatives'] if d['format']=='WEBP')
    probe=package.compose_dry_run_package(package_dir=output_root/'duplicate-suppression-probe',semantic_asset_id='FASA-FA029-DEDUPE-PROBE',master_sha256=first['master_sha256'],deliverables=[
      {'derivative_id':'DUP-A','source_path':webp['path'],'format':'WEBP','purpose':'PREVIEW','recipe_id':'fa029-dedupe-a','receipt_ref':'probe://a','compatibility_state':'COMPATIBLE'},
      {'derivative_id':'DUP-B','source_path':webp['path'],'format':'WEBP','purpose':'THUMBNAIL','recipe_id':'fa029-dedupe-b','receipt_ref':'probe://b','compatibility_state':'COMPATIBLE'}],metadata_ref='metadata://probe',rights_ref='rights://probe',compatibility_receipt_ref='compat://probe')
    if not (probe['manifest_entry_count']==2 and probe['unique_file_count']==1): raise RuntimeError(f'dedupe probe failed: {probe}')
    receipt={'schema':'factory-asset.five-master-derivative-canary-receipt.v1','task_id':'FA-029','date':'2026-09-04','status':'DONE','result':'PASS','source_inventory_receipt':str(inventory),'master_count':5,'target_dimensions':[TARGET_W,TARGET_H],'formats':['JPEG','WEBP','TIFF','PDF'],'masters':results,'duplicate_suppression_probe':probe,'summary':{'copy_hash_match':'5/5','derivative_sets':'5/5','derivative_outputs':'20/20','rerun_idempotency':'20/20 hash match','qa':'20/20 PASS','package_manifests':'5/5 PASS','vector_gate':'5/5 NOT_VECTORIZABLE fail-closed','duplicate_suppression':'2 entries -> 1 physical file','linux_mutation_performed':False,'publication_action':'NONE','upload_action':'NONE'}}
    return receipt

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inventory',required=True);ap.add_argument('--master-dir',required=True);ap.add_argument('--output-root',required=True);ap.add_argument('--receipt',required=True);args=ap.parse_args()
    result=run(Path(args.inventory),Path(args.master_dir),Path(args.output_root));Path(args.receipt).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result['summary'],indent=2))
if __name__=='__main__':main()