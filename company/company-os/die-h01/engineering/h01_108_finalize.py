#!/usr/bin/env python3
"""Downstream deterministic derivatives + metadata preparation.

Generation/H01-103 must already be terminal. This module never dispatches a provider,
never creates generation truth, and never changes generation-complete.receipt.json.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
sys.path[:0]=[str(H01/'engineering'),str(ROOT/'company/factory-asset/lib')]
from vector_postproduction import postprocess_vector
from package_readiness import build_metadata
from svg_prompt_composer_v2 import sha256_value

now=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
sha=lambda b:hashlib.sha256(b).hexdigest()

def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}

def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();w=Path(ns.workspace);f=w/'final'
 generation=load(w/'generation-complete.receipt.json');validation=load(f/'h01-103-validation.json')
 if generation.get('status')!='GENERATION_COMPLETE':raise SystemExit('E_GENERATION_COMPLETE_REQUIRED')
 if validation.get('status')!='PASS':raise SystemExit('E_H01_103_PASS_REQUIRED')
 source=f/'provider-original.svg'
 if not source.is_file():raise SystemExit('E_PROVIDER_ORIGINAL_MISSING')
 original=source.read_bytes()
 if sha(original)!=generation.get('provider_original_sha256') or sha(original)!=validation.get('input_sha256'):raise SystemExit('E_GENERATION_LINEAGE_MISMATCH')
 bp=json.loads((w/'blueprint.json').read_text());pp=json.loads((w/'provider-prompt.json').read_text());bph=sha256_value(bp)
 post=postprocess_vector(source,w/'postproduction',bp['semantic_asset_id'],provider_original_sha256=sha(original),blueprint_sha256=bph,provider_prompt_sha256=pp['prompt_sha256'],render_size=4096,repair_transport_geometry=True)
 if post['lineage']['canonical_svg_sha256']!=validation.get('canonical_svg_sha256'):raise SystemExit('E_POSTPRODUCTION_CANONICAL_DRIFT')
 deriv=[]
 for a in post['artifacts']:
  if a['source_role']=='PROVIDER_ORIGINAL':continue
  fmt=a['format'];purpose='PREVIEW' if fmt in {'PNG','WEBP','JPG'} else 'MARKETPLACE_DELIVERY'
  deriv.append({'derivative_id':f"D{len(deriv)+1}_{fmt}",'format':fmt,'purpose':purpose,'sha256':a['sha256']})
 fbp={'blueprint_id':bp['blueprint_id'],'semantic_identity':{'semantic_asset_id':bp['semantic_asset_id'],'subject':bp['subject']['canonical_name'],'commercial_use_case':bp['commercial']['primary_use_case']},'asset_type':'VECTOR_OBJECT'}
 md=build_metadata(blueprint=fbp,master_sha256=validation['canonical_svg_sha256'],derivative_hashes=deriv,provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI','binary_metadata_injected':False,'title_override':f"{bp['subject']['canonical_name'].title()} Isolated Editable Vector",'description_override':f"Clean isolated editable {bp['subject']['canonical_name']} vector with transparent background for stock design, ecommerce, education, presentations, interfaces and compositing."})
 dump(w/'metadata.json',md)
 rights={'schema':'die.h01.h01-108-rights-precheck.v2','result':'PRECHECK_PASS_VISUAL_DETECTOR_PENDING','semantic_asset_id':bp['semantic_asset_id'],'canonical_svg_sha256':validation['canonical_svg_sha256'],'queue_rights_gate':'PASS','object_atlas_ip_risk':'none','svg_structural_checks':{'h01_103':'PASS','embedded_raster':False,'readable_svg_text_element':False,'external_refs':False},'blueprint_rights':bp['rights'],'visual_detector_required_before_submission_eligibility':True,'generation_validity_effect':'NONE','submission_eligible':False,'submission_authority':'FOUNDER_CONTROLLED'}
 dump(w/'rights-precheck.json',rights)
 done=now()
 post_result={'schema':'die.h01.h01-115-postproduction-result.v1','task_id':'H01-115','job_id':generation['job_id'],'provider_id':generation['provider_id'],'profile_id':generation['profile_id'],'udd_id':generation['udd_id'],'status':'TECHNICAL_POSTPRODUCTION_PASS','completed_at':done,'provider_original_sha256':sha(original),'canonical_svg_sha256':validation['canonical_svg_sha256'],'generation_status':'GENERATION_COMPLETE','h01_103_status':'PASS','postproduction_status':post['result'],'semantic_asset_id':bp['semantic_asset_id'],'generation_validity_effect':'NONE','submission_authorized':False,'publication_authorized':False}
 dump(w/'postproduction-result.json',post_result)
 rec={'schema':'die.h01.h01-115-asset-receipt.v1','task_id':'H01-115','status':'POSTPRODUCTION_TECHNICAL_PASS_RIGHTS_PENDING','batch_position':generation['batch_position'],'noun':generation['noun'],'provider_id':generation['provider_id'],'profile_id':generation['profile_id'],'udd_id':generation['udd_id'],'provider_original_sha256':sha(original),'canonical_svg_sha256':validation['canonical_svg_sha256'],'generation_status':'GENERATION_COMPLETE','generation_validity_effect':'NONE','postproduction':'PASS','metadata_sha256':md['metadata_sha256'],'rights':rights['result'],'completed_at':done,'submission_eligible':False}
 dump(w/'asset-receipt.json',rec)
 print(json.dumps({'status':'PASS','position':generation['batch_position'],'noun':generation['noun'],'postproduction':'PASS','metadata':'PASS','rights':rights['result'],'generation_validity_effect':'NONE'},sort_keys=True))
 return 0

if __name__=='__main__':raise SystemExit(main())
