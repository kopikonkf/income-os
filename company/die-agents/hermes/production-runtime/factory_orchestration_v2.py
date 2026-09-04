#!/usr/bin/env python3
from __future__ import annotations

import hashlib, importlib.util, json, os, re, shutil, sys
from pathlib import Path
from typing import Any, Callable

HERE=Path(__file__).resolve().parent
REPO_ROOT=HERE.parents[3]
FA_LIB=REPO_ROOT/'company/factory-asset/lib'

def _load(name:str,filename:str):
    spec=importlib.util.spec_from_file_location(name,FA_LIB/filename);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod

expr=_load('fa139_expr','asset_expression_plan.py')
compiler=_load('fa139_compiler','blueprint_compiler.py')
router=_load('fa139_router','semantic_producer_router.py')
intake=_load('fa139_intake','provider_original.py')
planner=_load('fa139_planner','derivative_delivery_planner.py')
raster=_load('fa139_raster','raster_derivative.py')
derivqa=_load('fa139_dqa','derivative_qa.py')
rights=_load('fa139_rights','rights_signal_gate.py')
ready=_load('fa139_ready','package_readiness.py')
state=_load('fa139_state','postproduction_state.py')

class FactoryOrchestrationError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def csha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def atomic_json(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(tmp,path)
def safe_id(text:str)->str:
    s=re.sub(r'[^A-Z0-9_]+','_',str(text).upper()).strip('_')
    return (s[:48] or 'ASSET')
def slug(text:str)->str:
    s=re.sub(r'[^a-z0-9]+','-',str(text).casefold()).strip('-')
    return s[:72] or 'asset'

def project_legacy_raster_blueprint(*,legacy_blueprint:dict[str,Any],blueprint_sha256:str,workspace:Path)->tuple[dict[str,Any],dict[str,Any]]:
    seed=legacy_blueprint['seed'];family=legacy_blueprint['family'];prod=legacy_blueprint['production'];meta=legacy_blueprint['metadata_direction']
    prompt=str(prod.get('master_prompt','')).casefold()
    mode='ISOLATED_OBJECT' if ('isolated' in prompt and ('white background' in prompt or 'transparent background' in prompt or 'white' in prompt)) else 'PHOTO'
    buyer=str((family.get('buyer_persona') or ['Stock designer'])[0]);use=str((family.get('use_cases') or ['Commercial stock design composition'])[0]);product=str(meta.get('title_direction') or f"{seed['canonical_name']} stock image")
    sid='FASA-'+safe_id(seed['id']+'_'+mode);bid='FABP-'+safe_id(seed['id']+'_'+mode)
    snap_path=workspace/'cognition'/'seed-snapshot.json'
    snap_sha=sha(snap_path) if snap_path.is_file() else str(legacy_blueprint.get('lineage',{}).get('seed_snapshot_sha256') or blueprint_sha256)
    evidence_id='object-atlas-'+seed['id'].casefold()
    support={'seed_noun':seed['canonical_name'],'buyer':buyer,'commercial_use_case':use,'product_expression':product,'semantic_mode':mode,'platform_id':'ADOBE_STOCK'}
    plan={'schema':'die.factory-asset.asset-expression-plan.v1','plan_id':'FAEP-'+safe_id(seed['id']+'_'+mode),'seed':{'seed_id':seed['id'],'noun':seed['canonical_name']},'decision':'SELECT','decision_rationale':'Current approved Object Atlas production seed and fixed family Blueprint support exactly one bounded L0 raster expression for the active production card.','policy':{'expansion_rule':'EVIDENCE_SUPPORTED_ONLY','force_all_modes':False,'packaging_variants_create_new_semantic_asset':False,'derivative_planning_stage':'AFTER_VALIDATED_MASTER','submission_authority':'FOUNDER_CONTROLLED'},'evidence':[{'evidence_id':evidence_id,'kind':'OBJECT_ATLAS_SEED','source_ref':str(snap_path if snap_path.is_file() else workspace/'blueprint.json'),'source_sha256':snap_sha,'support':support,'rationale':'Approved Object Atlas seed plus the exact fixed production family Blueprint define the bounded active raster expression without claiming external buyer evidence.'}],'expressions':[{'semantic_asset_id':sid,'buyer':buyer,'commercial_use_case':use,'product_expression':product,'semantic_mode':mode,'producer_class':'RASTER_GENERATIVE','candidate_marketplace_route':{'platform_id':'ADOBE_STOCK','listing_use':product,'state':'CANDIDATE_REQUIRES_POLICY_CHECK'},'evidence_refs':[evidence_id],'selection_rationale':'The current production lane is a single bounded raster product expression derived from the approved Object Atlas seed and fixed family Blueprint.'}]}
    expr.validate_asset_expression_plan(plan)
    bp={'schema':'die.factory-asset.asset-blueprint.v2','blueprint_id':bid,'semantic_identity':{'semantic_asset_id':sid,'commercial_use_case':use,'subject':seed['canonical_name'],'intent':'DESIGN_COMPONENT' if mode=='ISOLATED_OBJECT' else 'COMMERCIAL_STOCK'},'asset_type':mode,'native_representation':'RASTER_PIXELS','producer_class':'RASTER_GENERATIVE','master_spec':{'format':'PNG','width_px':2000,'height_px':2000,'color_space':'SRGB','lineage_sha256_required':True},'derivatives':[{'derivative_id':'ADOBE_JPEG','purpose':'MARKETPLACE_DELIVERY','format':'JPEG','semantic_identity_effect':'NONE'},{'derivative_id':'WEB_PREVIEW','purpose':'PREVIEW','format':'WEBP','semantic_identity_effect':'NONE'}],'distinctness':{'identity_rule':'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT','packaging_variants_create_new_semantic_asset':False,'near_duplicate_action':'QUARANTINE'},'rights':{'commercial_use_cleared':True,'trademark_free':True,'recognizable_person_or_property':False,'release_state':'NOT_REQUIRED'},'quality':{'magic_mime_match':True,'decode_reopen':True,'lineage_sha256':True,'family_checks':['RASTER_DIMENSIONS','ALPHA_POLICY','COLOR_SPACE']},'policy':{'compatibility_state':'COMPATIBLE','marketplace_profiles':['ADOBE_STOCK'],'unknown_policy_action':'BLOCK_SUBMISSION','submission_authority':'FOUNDER_CONTROLLED'}}
    compiler.validate_blueprint(bp)
    return plan,bp

def write_bridge_artifacts(workspace:Path,legacy_blueprint:dict[str,Any],lock:dict[str,Any])->dict[str,Any]:
    root=workspace/'factory-v2';root.mkdir(parents=True,exist_ok=True)
    plan,bp=project_legacy_raster_blueprint(legacy_blueprint=legacy_blueprint,blueprint_sha256=lock['blueprint_sha256'],workspace=workspace)
    atomic_json(root/'asset-expression-plan.json',plan);atomic_json(root/'asset-blueprint-v2.json',bp)
    route=router.route_frozen_expression(plan=plan,semantic_asset_id=bp['semantic_identity']['semantic_asset_id'],blueprint=bp,frozen_blueprint_sha256=router.canonical_sha256(bp))
    atomic_json(root/'producer-route.json',route)
    cognition={'schema':'die.factory-asset.cognition-provenance.v1','result':'LEGACY_AUTHOR_REVIEW_ACCEPTED','legacy_blueprint_id':legacy_blueprint['blueprint_id'],'legacy_blueprint_sha256':lock['blueprint_sha256'],'asset_blueprint_id':bp['blueprint_id'],'repeated_cognition_per_image':False,'division01_worker_authority':False,'executive_worker_authority':False}
    atomic_json(root/'cognition-provenance.json',cognition)
    return {'root':root,'plan':plan,'blueprint':bp,'route':route,'cognition':cognition}

def telegram_event(workspace:Path,kind:str,payload:dict[str,Any],send_fn:Callable[[str],None]|None=None)->dict[str,Any]:
    allowed={'PRODUCTION_STARTED','ARTIFACT_CREATED','QA_QC_UPDATE','WAITING_FOUNDER_QC'}
    if kind not in allowed:raise FactoryOrchestrationError('TELEGRAM_KIND_INVALID',kind)
    event={'schema':'die.factory-asset.telegram-milestone.v1','task_id':workspace.name,'kind':kind,'payload':payload}
    event['event_id']=csha(event)
    ledger=workspace/'factory-v2'/'telegram-events.jsonl';ledger.parent.mkdir(parents=True,exist_ok=True)
    if ledger.is_file():
        for line in ledger.read_text(encoding='utf-8').splitlines():
            if line.strip() and json.loads(line).get('event_id')==event['event_id']:return {**event,'delivery':'IDEMPOTENT_REUSE'}
    message=' | '.join([kind,workspace.name,*[f'{k}={v}' for k,v in sorted(payload.items()) if v is not None]])
    if send_fn is not None:send_fn(message);delivery='SENT'
    else:delivery='DRY_RUN'
    with ledger.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps({**event,'message':message,'delivery':delivery},sort_keys=True)+'\n')
    return {**event,'message':message,'delivery':delivery}

def _master_facts(path:Path,*,semantic_asset_id:str,blueprint_id:str,source_kind:str='POSTPROCESS_MASTER')->dict[str,Any]:
    data=path.read_bytes();media=intake.sniff_media(data,filename=path.name)
    return {'schema':'die.factory-asset.master-facts.v1','source_kind':source_kind,'provider_id':None,'semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,'sha256':hashlib.sha256(data).hexdigest(),'format':media['format'],'width_px':media['width_px'],'height_px':media['height_px'],'has_alpha_channel':media['has_alpha_channel'],'has_transparency_metadata':media['has_transparency_metadata'],'has_transparency':media['has_transparency'],'provider_original_lineage':None}

def _recipe(plan_row:dict[str,Any],facts:dict[str,Any])->dict[str,Any]:
    return {'schema':'die.factory-asset.derivative-recipe.v1','recipe_id':'fa139-'+plan_row['derivative_id'].casefold().replace('_','-'),'recipe_version':'1.0.0','input':{'master_sha256':facts['sha256'],'semantic_asset_id':facts['semantic_asset_id'],'format':facts['format']},'output':{'format':plan_row['format'],'purpose':plan_row['purpose'],'width_px':facts['width_px'],'height_px':facts['height_px'],'color_space':'SRGB','alpha_policy':plan_row['alpha_policy'],'quality':92,'semantic_identity_effect':'NONE'},'marketplace_profile':{'platform_id':'ADOBE_STOCK','profile_revision':'1.0'},'idempotency':{'key_material':['master_sha256','recipe_id','recipe_version','marketplace_profile.platform_id','marketplace_profile.profile_revision','output'],'output_collision_action':'VERIFY_HASH_AND_REUSE_OR_FAIL'},'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256':True,'dimensions_if_raster':True},'compatibility':{'unknown_action':'BLOCK_PACKAGE','require_profile_match':True}}

def _default_rights_observation(master_sha:str)->dict[str,Any]:
    return {'schema':'die.factory-asset.rights-observation.v1','master_sha256':master_sha,'detectors':{'text':{'state':'UNAVAILABLE','detected_strings':[],'confirmed_trademark_terms':[],'trademark_candidates':[],'unresolved_strings':[]},'logo':{'state':'UNAVAILABLE','candidates':[]},'watermark':{'state':'UNAVAILABLE','candidates':[]},'safety':{'state':'UNAVAILABLE','flags':[]}}}

def postprocess_raster_workspace(*,workspace:Path,source_path:Path,provider_id:str,expected_source_sha256:str,upscale_fn:Callable[[Path,Path],dict[str,Any]],send_fn:Callable[[str],None]|None=None)->dict[str,Any]:
    legacy=json.loads((workspace/'blueprint.json').read_text());lock=json.loads((workspace/'blueprint.lock.json').read_text());bridge=write_bridge_artifacts(workspace,legacy,lock);bp=bridge['blueprint'];root=bridge['root'];sid=bp['semantic_identity']['semantic_asset_id']
    if bridge['route']['route_kind']!='PROVIDER_ROUTER':raise FactoryOrchestrationError('LIVE_RASTER_ROUTE_EXPECTED',bridge['route']['route_kind'])
    ingest=intake.intake_provider_original(source_path=source_path,staging_root=root/'master-staging',attempt_id=workspace.name+'-provider-original',semantic_asset_id=sid,blueprint_id=bp['blueprint_id'],provider_id=provider_id,expected_sha256=expected_source_sha256)
    atomic_json(root/'provider-original-intake.json',ingest)
    sm_path=root/'postproduction-state.json';d=state.create_state(sm_path,job_id=workspace.name,semantic_asset_id=sid,blueprint_id=bp['blueprint_id'],source_master_sha256=ingest['source_sha256'])
    d=state.advance(sm_path,target_state='MASTER_VALIDATED',evidence={'result':'PASS','master_sha256':ingest['source_sha256'],'receipt_ref':'factory-v2/provider-original-intake.json'},event_id='MASTER-'+ingest['source_sha256'][:16],expected_revision=d['revision'])
    upscale_out=root/'upscale'/'active-master.png';upscale_out.parent.mkdir(parents=True,exist_ok=True);ur=upscale_fn(source_path,upscale_out)
    normalized={'schema':'die.factory-asset.upscale-recovery-receipt.v1','result':'NOOP' if ur['action']=='NO_OP' else 'PASS','decision_state':'NOOP_SUFFICIENT' if ur['action']=='NO_OP' else 'UPSCALE_REQUIRED','source_sha256':ur['source']['sha256'],'source_dimensions':[ur['source']['width'],ur['source']['height']],'final_sha256':ur['output']['sha256'],'final_dimensions':[ur['output']['width'],ur['output']['height']],'output_path':ur['output']['path'],'source_unchanged':True,'partial_output':False,'engine':ur.get('model')}
    atomic_json(root/'upscale-normalized.json',normalized);d=state.advance(sm_path,target_state='UPSCALE_DECIDED',evidence=normalized,event_id='UPSCALE-'+csha(normalized)[:16],expected_revision=d['revision'])
    active=Path(normalized['output_path'])
    if not active.is_file() or sha(active)!=normalized['final_sha256']:raise FactoryOrchestrationError('UPSCALE_OUTPUT_HASH_MISMATCH',str(active))
    facts=_master_facts(active,semantic_asset_id=sid,blueprint_id=bp['blueprint_id'])
    req_w=int(bp['master_spec'].get('width_px',0));req_h=int(bp['master_spec'].get('height_px',0))
    if facts['width_px']<req_w or facts['height_px']<req_h:raise FactoryOrchestrationError('ACTIVE_MASTER_DIMENSIONS_BELOW_BLUEPRINT',f"{facts['width_px']}x{facts['height_px']}<{req_w}x{req_h}")
    plan=planner.plan_derivatives(blueprint=bp,master=facts);atomic_json(root/'derivative-plan.json',plan)
    derivdir=root/'derivatives';derivdir.mkdir(parents=True,exist_ok=True);evidence=[]
    for row in plan['entries']:
        ext={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp','TIFF':'.tiff'}[row['format']];out=derivdir/(row['derivative_id'].casefold()+ext)
        if row['action']=='REUSE_MASTER_BYTES':
            if not out.exists():shutil.copy2(active,out)
            rec={'output':{'sha256':sha(out)},'result':'PASS','recipe_id':'reuse-master-bytes'}
        else:
            if out.exists():out.unlink()
            rec=raster.render_raster_derivative(active,out,_recipe(row,facts))
        q=derivqa.inspect_derivative(out,expected_format=row['format'],expected_dimensions=(facts['width_px'],facts['height_px']),expected_alpha='ABSENT' if row['format']=='JPEG' else 'ANY',expected_sha256=rec['output']['sha256'])
        if q['result']!='PASS':raise FactoryOrchestrationError('DERIVATIVE_QA_FAILED',row['derivative_id'])
        evidence.append({'derivative_id':row['derivative_id'],'format':row['format'],'purpose':row['purpose'],'sha256':q['sha256'],'qa_sha256':q['sha256'],'sha256_verified':True,'master_sha256':facts['sha256'],'qa_result':'PASS','path':str(out),'qa':q})
    d=state.advance(sm_path,target_state='DERIVATIVES_READY',evidence={'master_sha256':facts['sha256'],'derivatives':evidence},event_id='DERIV-'+csha([(x['derivative_id'],x['sha256']) for x in evidence])[:16],expected_revision=d['revision'])
    d=state.advance(sm_path,target_state='TECHNICAL_QA_PASS',evidence={'result':'PASS','derivatives':[{'derivative_id':x['derivative_id'],'sha256':x['sha256'],'result':'PASS'} for x in evidence]},event_id='QA-'+csha(evidence)[:16],expected_revision=d['revision'])
    obs_path=workspace/'rights-observation.json';obs=json.loads(obs_path.read_text()) if obs_path.is_file() else _default_rights_observation(facts['sha256']);rs=rights.evaluate_rights_signals(master_path=active,expected_sha256=facts['sha256'],observation=obs);atomic_json(root/'rights-signal.json',rs)
    current=state.load_state(sm_path)
    if state.STATES.index(current['state']) < state.STATES.index('RIGHTS_SIGNAL_PASS_OR_REVIEW'):
        d=state.advance(sm_path,target_state='RIGHTS_SIGNAL_PASS_OR_REVIEW',evidence=rs,event_id='RIGHTS-'+csha(rs)[:16],expected_revision=current['revision'])
    elif current.get('rights_disposition')=='REVIEW_REQUIRED' and rs['result']=='PASS':
        d=state.resolve_rights_review(sm_path,evidence=rs,event_id='RIGHTS-RESOLVE-'+csha(rs)[:16],expected_revision=current['revision'])
    else:
        d=current
    meta=ready.build_metadata(blueprint=bp,master_sha256=facts['sha256'],derivative_hashes=evidence,provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI'});atomic_json(root/'metadata.json',meta);atomic_json(root/'submission-fields.json',meta['submission_fields'])
    d=state.advance(sm_path,target_state='METADATA_READY',evidence={'master_sha256':facts['sha256'],'metadata_sha256':meta['metadata_sha256'],'derivative_hashes':meta['derivative_hashes']},event_id='META-'+meta['metadata_sha256'][:16],expected_revision=d['revision'])
    pkg=ready.evaluate_package_readiness(blueprint=bp,derivative_plan=plan,rights_signal=rs,derivative_evidence=evidence,provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI'},master_technical_qa={'result':'PASS','master_sha256':facts['sha256']});atomic_json(root/'package-readiness.json',pkg)
    telegram_event(workspace,'QA_QC_UPDATE',{'postproduction_state':d['state'],'rights':rs['result'],'package':pkg['result']},send_fn)
    if pkg['result']!='PACKAGE_READY':return {'status':'RIGHTS_REVIEW_REQUIRED' if rs['result']=='REVIEW_REQUIRED' else 'PACKAGE_BLOCKED','task_id':workspace.name,'state':d['state'],'rights':rs['result'],'metadata':str(root/'metadata.json'),'submission_fields':str(root/'submission-fields.json')}
    d=state.advance(sm_path,target_state='PACKAGE_READY',evidence=pkg,event_id='PACKAGE-'+pkg['package_plan']['package_plan_sha256'][:16],expected_revision=d['revision'])
    delivery=next(x for x in evidence if x['purpose']=='MARKETPLACE_DELIVERY');final=workspace/'final';final.mkdir(exist_ok=True);alias=final/meta['listing_filename']
    if alias.exists() and sha(alias)!=delivery['sha256']:raise FactoryOrchestrationError('LISTING_ALIAS_CONFLICT',str(alias))
    if not alias.exists():shutil.copy2(Path(delivery['path']),alias)
    final_manifest={'schema':'die.production.final-artifact.v2','task_id':workspace.name,'seed_noun':bp['semantic_identity']['subject'],'semantic_asset_id':sid,'blueprint_id':bp['blueprint_id'],'source_master_sha256':d['source_master_sha256'],'active_master_sha256':d['active_master_sha256'],'listing_filename':alias.name,'listing_path':str(alias),'listing_sha256':sha(alias),'metadata_ref':str(root/'metadata.json'),'submission_fields_ref':str(root/'submission-fields.json'),'binary_metadata_injected':False,'package_plan_sha256':pkg['package_plan']['package_plan_sha256'],'founder_qc':'PENDING','submission_authorized':False,'publication_authorized':False}
    atomic_json(final/'final-artifact.json',final_manifest)
    d=state.advance(sm_path,target_state='WAITING_FOUNDER_QC',evidence={'founder_qc_required':True,'human_rights_clearance':False,'package_plan_sha256':pkg['package_plan']['package_plan_sha256']},event_id='FOUNDER-'+pkg['package_plan']['package_plan_sha256'][:16],expected_revision=d['revision'])
    telegram_event(workspace,'WAITING_FOUNDER_QC',{'seed':bp['semantic_identity']['subject'],'filename':alias.name,'sha256':sha(alias)[:12]+'...','state':d['state']},send_fn)
    return {'status':'WAITING_FOUNDER_QC','task_id':workspace.name,'listing_path':str(alias),'metadata':str(root/'metadata.json'),'submission_fields':str(root/'submission-fields.json'),'state_path':str(sm_path)}
