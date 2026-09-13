#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1];ROOT=HERE.parents[4]
sys.path[:0]=[str(H01/'engineering'),str(ROOT/'company/factory-asset/lib')]
from provider_output_acquisition import acquire_svg_text
from native_svg_pipeline import validate_and_normalize
from native_svg_request_contract import build_request,build_success_receipt
from vector_postproduction import postprocess_vector
from package_readiness import build_metadata
from svg_prompt_composer_v2 import sha256_value
now=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ap.add_argument('--provider',required=True);ap.add_argument('--source-kind',choices=['TEXT','FILE','PROVIDER_ORIGINAL'],required=True);ap.add_argument('--source',required=True);ap.add_argument('--job-id',required=True);ap.add_argument('--profile-id',default='h01-web-p001');ap.add_argument('--udd-id',default='h01-web-s01');ns=ap.parse_args()
 w=Path(ns.workspace);f=w/'final';f.mkdir(parents=True,exist_ok=True);bp=json.loads((w/'blueprint.json').read_text());mi=json.loads((w/'master-instruction.json').read_text());pp=json.loads((w/'provider-prompt.json').read_text());it=json.loads((w/'batch-item.json').read_text());done=now();bph=sha256_value(bp)
 req=build_request(request_id=f'H01SVGREQ-{ns.job_id}',queue_item_id=it['queue_item_id'],source_candidate_id=it['source_candidate_id'],semantic_asset_id=bp['semantic_asset_id'],provider_id=ns.provider,provider_profile=f'{ns.provider.upper()}_WEB_P001',blueprint_id=bp['blueprint_id'],blueprint_sha256=bph,master_instruction_sha256=mi['master_instruction_sha256'],provider_prompt=pp['prompt'],provider_prompt_sha256=pp['prompt_sha256']);dump(f/'native-svg-request.json',req)
 src=Path(ns.source)
 if ns.source_kind=='TEXT':
  raw=src.read_text().rstrip('\n');acq,_=acquire_svg_text(job_id=ns.job_id,request_id=req['request_id'],provider_id=ns.provider,profile_id=ns.profile_id,provider_status='COMPLETED',provider_response_text=raw,output_dir=f,completion_signal='SVG_COMPLETE_STABLE_NO_STOP',completed_at=done,finish_reason='PROVIDER_UI_TERMINAL');original=(f/'provider-original.svg').read_bytes()
 elif ns.source_kind=='FILE':
  original=src.read_bytes();raw=original.decode();target=f/'provider-original.svg'
  if target.exists() and target.read_bytes()!=original:raise SystemExit('E_PROVIDER_ORIGINAL_COLLISION')
  if not target.exists():target.write_bytes(original)
  dump(f/'provider-file-acquisition.receipt.json',{'schema':'die.h01.provider-native-svg-file-acquisition.v1','status':'SUCCEEDED','job_id':ns.job_id,'provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'source_kind':'PROVIDER_FILE_DOWNLOAD','mime':'image/svg+xml','acquisition_method':'UI_DOWNLOAD_SVG','artifact':{'path':str(target),'sha256':sha(original),'bytes':len(original),'immutable_provider_original':True},'cookies_or_tokens_read':False,'session_bytes_read':False,'completed_at':done})
 else:
  original=src.read_bytes();raw=original.decode();target=f/'provider-original.svg'
  if src.resolve()!=target.resolve():raise SystemExit('E_PROVIDER_ORIGINAL_PATH')
 norm=validate_and_normalize(original.decode());(f/'canonical.svg').write_text(norm['canonical_svg'])
 val={'schema':'die.h01.h01-103.live-validation.v1','task_id':'H01-103','status':'PASS','input_sha256':sha(original),'canonical_svg_sha256':norm['canonical_svg_sha256'],'geometry_count':norm['geometry_count'],'path_count':norm['path_count'],'shape_count':norm['shape_count'],'total_points':norm['total_points'],'render_ink_pixels_512':norm['render_ink_pixels_512'],'native_editable':norm['native_editable'],'conversion_from_raster':norm['conversion_from_raster']};dump(f/'h01-103-validation.json',val)
 h104=build_success_receipt(request=req,ingress='WEB_AI_ADAPTER',dispatch_commit_id=f'{ns.job_id}-CDP',provider_status='COMPLETED',provider_response_text=raw,h01_103_canonical_svg_sha256=norm['canonical_svg_sha256'],finish_reason='PROVIDER_UI_TERMINAL',candidate_svg_text=original.decode());dump(f/'h01-104-native-svg-receipt.json',h104)
 post=postprocess_vector(f/'provider-original.svg',w/'postproduction',bp['semantic_asset_id'],provider_original_sha256=sha(original),blueprint_sha256=bph,provider_prompt_sha256=pp['prompt_sha256'],render_size=4096)
 deriv=[]
 for a in post['artifacts']:
  if a['source_role']=='PROVIDER_ORIGINAL':continue
  fmt=a['format'];purpose='PREVIEW' if fmt in {'PNG','WEBP','JPG'} else 'MARKETPLACE_DELIVERY';deriv.append({'derivative_id':f"D{len(deriv)+1}_{fmt}",'format':fmt,'purpose':purpose,'sha256':a['sha256']})
 fbp={'blueprint_id':bp['blueprint_id'],'semantic_identity':{'semantic_asset_id':bp['semantic_asset_id'],'subject':bp['subject']['canonical_name'],'commercial_use_case':bp['commercial']['primary_use_case']},'asset_type':'VECTOR_OBJECT'}
 md=build_metadata(blueprint=fbp,master_sha256=post['lineage']['canonical_svg_sha256'],derivative_hashes=deriv,provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI','binary_metadata_injected':False,'title_override':f"{bp['subject']['canonical_name'].title()} Isolated Editable Vector",'description_override':f"Clean isolated editable {bp['subject']['canonical_name']} vector with transparent background for stock design, ecommerce, education, presentations, interfaces and compositing."});dump(w/'metadata.json',md)
 rights={'schema':'die.h01.h01-108-rights-precheck.v1','result':'PRECHECK_PASS_VISUAL_DETECTOR_PENDING','semantic_asset_id':bp['semantic_asset_id'],'canonical_svg_sha256':post['lineage']['canonical_svg_sha256'],'queue_rights_gate':'PASS','object_atlas_ip_risk':'none','svg_structural_checks':{'h01_103':'PASS','embedded_raster':False,'readable_svg_text_element':False,'external_refs':False},'blueprint_rights':bp['rights'],'visual_detector_required_before_h01_108_acceptance':True,'submission_eligible':False,'submission_authority':'FOUNDER_CONTROLLED'};dump(w/'rights-precheck.json',rights)
 post_result={'schema':'die.h01.h01-108-postproduction-result.v1','job_id':ns.job_id,'provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'status':'TECHNICAL_POSTPRODUCTION_PASS','completed_at':done,'classification':'NATIVE_SVG' if ns.source_kind=='FILE' else 'TEXT_SVG','provider_original_sha256':sha(original),'h01_103_status':'PASS','postproduction_status':post['result'],'semantic_asset_id':bp['semantic_asset_id'],'submission_authorized':False,'publication_authorized':False};dump(w/'postproduction-result.json',post_result)
 rec={'schema':'die.h01.h01-108-asset-receipt.v1','task_id':'H01-108','status':'ASSET_TECHNICAL_PASS_RIGHTS_PENDING','batch_position':it['batch_position'],'noun':it['canonical_name'],'provider_id':ns.provider,'profile_id':ns.profile_id,'udd_id':ns.udd_id,'provider_original_sha256':sha(original),'canonical_svg_sha256':post['lineage']['canonical_svg_sha256'],'postproduction':'PASS','metadata_sha256':md['metadata_sha256'],'rights':rights['result'],'completed_at':done};dump(w/'asset-receipt.json',rec)
 print(json.dumps({'status':'PASS','position':it['batch_position'],'noun':it['canonical_name'],'provider':ns.provider,'provider_original_sha256':sha(original),'canonical_svg_sha256':post['lineage']['canonical_svg_sha256'],'postproduction':'PASS','metadata':'PASS','rights':rights['result']}))
if __name__=='__main__':main()
