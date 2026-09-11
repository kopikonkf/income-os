from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'company/factory-asset'

def _load_module(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise RuntimeError(f'E_MODULE_LOAD:{path}')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

bridge=_load_module('pi2_bridge',BASE/'lib/dual_atlas_context_bridge.py')
planner=_load_module('pi2_planner',BASE/'lib/opportunity_planner.py')
expr=_load_module('pi2_expr',BASE/'lib/asset_expression_plan.py')
compiler=_load_module('pi2_compiler',BASE/'lib/blueprint_compiler.py')
router=_load_module('pi2_router',BASE/'lib/semantic_producer_router.py')
ledger=_load_module('pi2_ledger',ROOT/'company/die-agents/hermes/production_seed_ledger.py')

class ProductionIntelligenceV2Error(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def canon_sha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def safe(v:str)->str:return re.sub(r'[^A-Z0-9]+','_',str(v).upper()).strip('_')[:48] or 'ASSET'

def _context_by_id(contexts:list[dict[str,Any]])->dict[str,dict[str,Any]]:return {c['context_id']:c for c in contexts}
def _champion(plan:dict[str,Any])->dict[str,Any]:
    rows=[x for x in plan['candidates'] if x['candidate_lane']=='EXPLOITATION' and x['state']=='ELIGIBLE_BASELINE' and x['preset_id']=='ISOLATED_CARTOON_WATERCOLOR_L0']
    if not rows:raise ProductionIntelligenceV2Error('CHAMPION_MISSING','isolated baseline')
    return sorted(rows,key=lambda x:(-x['score'],x['candidate_id']))[0]

def _expression_plan(seed:dict[str,Any],candidate:dict[str,Any],contexts:list[dict[str,Any]],bridge_result:dict[str,Any])->dict[str,Any]:
    buyer='stock designer'
    use=f"reusable isolated {seed['canonical_name']} design component"
    product=f"isolated {seed['canonical_name']} stock design component"
    evidence=[{'evidence_id':'pi2-object-seed','kind':'OBJECT_ATLAS_SEED','source_ref':f"object-atlas://{seed['id']}",'source_sha256':'0'*64,'support':{'seed_noun':seed['canonical_name'],'buyer':buyer,'commercial_use_case':use,'product_expression':product,'semantic_mode':'ISOLATED_OBJECT','platform_id':'ADOBE_STOCK'},'rationale':'Approved Object Atlas seed supports the primitive and current accepted isolated-object champion exploitation lane. Human-context hypotheses remain research context only and do not become SELECT evidence.'}]
    plan={'schema':'die.factory-asset.asset-expression-plan.v1','plan_id':'FAEP-'+safe(seed['id']+'_PI2'),'seed':{'seed_id':seed['id'],'noun':seed['canonical_name']},'decision':'SELECT','decision_rationale':'Production Intelligence v2 selects one evidence-bounded champion expression while preserving Human-context and alternate-mode hypotheses as research-only exploration.','policy':{'expansion_rule':'EVIDENCE_SUPPORTED_ONLY','force_all_modes':False,'packaging_variants_create_new_semantic_asset':False,'derivative_planning_stage':'AFTER_VALIDATED_MASTER','submission_authority':'FOUNDER_CONTROLLED'},'evidence':evidence,'expressions':[{'semantic_asset_id':'FASA-'+safe(seed['id']+'_ISOLATED_OBJECT_PI2'),'buyer':buyer,'commercial_use_case':use,'product_expression':product,'semantic_mode':'ISOLATED_OBJECT','producer_class':'RASTER_GENERATIVE','candidate_marketplace_route':{'platform_id':'ADOBE_STOCK','listing_use':product,'state':'CANDIDATE_REQUIRES_POLICY_CHECK'},'evidence_refs':['pi2-object-seed'],'selection_rationale':'Current accepted isolated-object champion lane remains the deterministic exploitation path; alternate mode/preset candidates are not promoted by this selection.'}]}
    expr.validate_asset_expression_plan(plan);return plan

def _blueprint(seed:dict[str,Any],plan:dict[str,Any])->dict[str,Any]:
    e=plan['expressions'][0];sid=e['semantic_asset_id']
    bp={'schema':'die.factory-asset.asset-blueprint.v2','blueprint_id':'FABP-'+safe(seed['id']+'_ISOLATED_PI2'),'semantic_identity':{'semantic_asset_id':sid,'commercial_use_case':e['commercial_use_case'],'subject':seed['canonical_name'],'intent':'DESIGN_COMPONENT'},'asset_type':'ISOLATED_OBJECT','native_representation':'RASTER_PIXELS','producer_class':'RASTER_GENERATIVE','master_spec':{'format':'PNG','width_px':2000,'height_px':2000,'color_space':'SRGB','lineage_sha256_required':True},'derivatives':[{'derivative_id':'ADOBE_JPEG','purpose':'MARKETPLACE_DELIVERY','format':'JPEG','semantic_identity_effect':'NONE'},{'derivative_id':'WEB_PREVIEW','purpose':'PREVIEW','format':'WEBP','semantic_identity_effect':'NONE'}],'distinctness':{'identity_rule':'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT','packaging_variants_create_new_semantic_asset':False,'near_duplicate_action':'QUARANTINE'},'rights':{'commercial_use_cleared':True,'trademark_free':True,'recognizable_person_or_property':False,'release_state':'NOT_REQUIRED'},'quality':{'magic_mime_match':True,'decode_reopen':True,'lineage_sha256':True,'family_checks':['RASTER_DIMENSIONS','ALPHA_POLICY','COLOR_SPACE']},'policy':{'compatibility_state':'COMPATIBLE','marketplace_profiles':['ADOBE_STOCK'],'unknown_policy_action':'BLOCK_SUBMISSION','submission_authority':'FOUNDER_CONTROLLED'}}
    compiler.validate_blueprint(bp);return bp

def build_trace(*,seed:dict[str,Any],contexts:list[dict[str,Any]],object_evidence_refs:list[str]|None=None)->dict[str,Any]:
    obj={'seed_id':seed['id'],'noun':seed['canonical_name'],'object_class':seed.get('object_class','object'),'category_path':seed.get('category_path','Object'),'evidence_refs':object_evidence_refs or [f"object-atlas://{seed['id']}"]}
    bridged=bridge.supply_first(obj,contexts,limit=8)
    opp=planner.plan_seed_opportunities(seed=seed,bridge_result=bridged,limit=12)
    champion=_champion(opp);ep=_expression_plan(seed,champion,contexts,bridged);bp=_blueprint(seed,ep);bp_sha=router.canonical_sha256(bp)
    route=router.route_frozen_expression(plan=ep,semantic_asset_id=ep['expressions'][0]['semantic_asset_id'],blueprint=bp,frozen_blueprint_sha256=bp_sha)
    prod=compiler.compile_blueprint(bp)
    fa319=json.loads((BASE/'receipts/FA-319-baseline-package-acceptance.receipt.json').read_text(encoding='utf-8'))
    if fa319.get('status')!='DONE' or fa319.get('state_machine',{}).get('package_result')!='PACKAGE_READY':raise ProductionIntelligenceV2Error('POSTPRODUCTION_ACCEPTANCE_MISSING','FA-319')
    champion_identity=ledger.expression_identity(seed_id=seed['id'],noun=seed['canonical_name'],semantic_mode='ISOLATED_OBJECT',commercial_expression=ep['expressions'][0]['product_expression'],preset_id=champion['preset_id'],preset_revision=champion['preset_revision'])
    exploration=[]
    for c in opp['candidates']:
        if c['candidate_id']==champion['candidate_id']:continue
        exploration.append({k:c.get(k) for k in ('candidate_id','semantic_mode','preset_id','preset_revision','candidate_lane','state','score','engine_state','context_id')})
    return {'schema':'die.factory-asset.production-intelligence-v2-trace.v1','seed_selection':{'seed_id':seed['id'],'noun':seed['canonical_name'],'selection_basis':'APPROVED_OBJECT_ATLAS_INPUT','authority_effect':'NONE'},'dual_atlas_bridge':bridged,'opportunity_plan':opp,'selected_champion':champion,'expression_plan':ep,'production_preset':{'preset_id':champion['preset_id'],'revision':champion['preset_revision'],'lane':'EXPLOITATION'},'asset_blueprint_v2':bp,'producer_route':route,'production_plan':prod,'expression_identity':champion_identity,'exploration_candidates':exploration,'postproduction_acceptance':{'receipt':'company/factory-asset/receipts/FA-319-baseline-package-acceptance.receipt.json','result':fa319['result'],'package_result':fa319['state_machine']['package_result'],'final_state':fa319['canary']['final_state']},'authority':{'effect':'NONE','throughput_scale_authorized':False,'provider_call_authorized':False,'submission_authorized':False,'publication_authorized':False}}
