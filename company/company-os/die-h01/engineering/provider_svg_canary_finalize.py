from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve(); H01=HERE.parents[1]; ROOT=HERE.parents[4]
sys.path.insert(0,str(H01/'engineering')); sys.path.insert(0,str(ROOT/'company/factory-asset/lib'))
from provider_output_acquisition import acquire_svg_text
from native_svg_pipeline import validate_and_normalize
from native_svg_request_contract import build_request, build_success_receipt

def dump(path:Path,value): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def main():
 p=argparse.ArgumentParser(); p.add_argument('--provider',required=True); p.add_argument('--job-id',required=True); p.add_argument('--canary-id',required=True); p.add_argument('--output-dir',required=True); p.add_argument('--profile-id',default='h01-web-p001'); p.add_argument('--udd-id',default='h01-web-s01'); p.add_argument('--cdp-port',type=int,default=9201); p.add_argument('--completion-signal',default='SVG_COMPLETE_STABLE_NO_STOP'); p.add_argument('--prompt-file',default=''); a=p.parse_args()
 out=Path(a.output_dir); final=out/'final'; raw=(out/'raw-provider-response.txt').read_text(encoding='utf-8').rstrip('\n'); completed=now()
 base=json.loads((H01/'fixtures/h01-104/request.web-ai-adapter.json').read_text()); provider_prompt=Path(a.prompt_file).read_text(encoding='utf-8') if a.prompt_file else base['prompt']['text']
 req=build_request(request_id=f'H01SVGREQ-{a.job_id}',queue_item_id=base['queue_item_id'],source_candidate_id=base['source_candidate_id'],semantic_asset_id=base['semantic_asset_id'],provider_id=a.provider,provider_profile=f'{a.provider.upper()}_WEB_P001',blueprint_id=base['blueprint']['blueprint_id'],blueprint_sha256=base['blueprint']['sha256'],master_instruction_sha256=base['master_instruction_sha256'],provider_prompt=provider_prompt,provider_prompt_sha256=None)
 dump(final/'native-svg-request.json',req)
 acq,_=acquire_svg_text(job_id=a.job_id,request_id=req['request_id'],provider_id=a.provider,profile_id=a.profile_id,provider_status='COMPLETED',provider_response_text=raw,output_dir=final,completion_signal=a.completion_signal,completed_at=completed,finish_reason='PROVIDER_UI_TERMINAL')
 svg=(final/'provider-original.svg').read_text(); norm=validate_and_normalize(svg); (final/'canonical.svg').write_text(norm['canonical_svg'],encoding='utf-8')
 val={'schema':'die.h01.h01-103.live-validation.v1','task_id':'H01-103','status':'PASS','input_sha256':hashlib.sha256(svg.encode()).hexdigest(),'canonical_svg_sha256':norm['canonical_svg_sha256'],'geometry_count':norm['geometry_count'],'path_count':norm['path_count'],'shape_count':norm['shape_count'],'total_points':norm['total_points'],'render_ink_pixels_512':norm['render_ink_pixels_512'],'native_editable':norm['native_editable'],'conversion_from_raster':norm['conversion_from_raster']}; dump(final/'h01-103-validation.json',val)
 h104=build_success_receipt(request=req,ingress='WEB_AI_ADAPTER',dispatch_commit_id=f'{a.job_id}-CDP',provider_status='COMPLETED',provider_response_text=raw,h01_103_canonical_svg_sha256=norm['canonical_svg_sha256'],finish_reason='PROVIDER_UI_TERMINAL',candidate_svg_text=svg); dump(final/'h01-104-native-svg-receipt.json',h104)
 can={'schema':'die.h01.provider-native-svg-canary.v1','task_id':'H01-107','canary_id':a.canary_id,'status':'PASS','provider_id':a.provider,'profile_id':a.profile_id,'udd_id':a.udd_id,'cdp':f'127.0.0.1:{a.cdp_port}','classification':'TEXT_SVG','completed_at':completed,'completion_signal':a.completion_signal,'prompt_sha256':req['prompt']['sha256'],'provider_original_sha256':acq['artifact']['sha256'],'provider_original_bytes':acq['artifact']['bytes'],'h01_103':val,'h01_104_receipt_status':'SUCCEEDED','provider_promoted':False,'cookies_or_tokens_read':False,'session_bytes_read':False,'submission_authorized':False,'publication_authorized':False}; cp=final/f'{a.canary_id}-{a.provider}-canary.receipt.json'; dump(cp,can)
 job={'schema':'die.h01.browser-job-result.v1','job_id':a.job_id,'job_kind':'H01_107_PROVIDER_CANARY','provider_id':a.provider,'profile_id':a.profile_id,'udd_id':a.udd_id,'terminal_state':'SUCCEEDED','completed_at':completed,'classification':'TEXT_SVG','provider_original_sha256':acq['artifact']['sha256'],'h01_103_status':'PASS','canary_receipt':str(cp),'authority':{'provider_generation_dispatched':True,'submission_authorized':False,'publication_authorized':False}}; dump(out/'browser-job-result.json',job)
 print(json.dumps({'provider':a.provider,'classification':'TEXT_SVG','bytes':acq['artifact']['bytes'],'sha256':acq['artifact']['sha256'],'geometry_count':norm['geometry_count'],'total_points':norm['total_points'],'render_ink_pixels_512':norm['render_ink_pixels_512']}))
if __name__=='__main__': main()
