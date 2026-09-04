from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
POLICY_PATH=ROOT/'company/factory-asset/registries/cognition-routing-policy.v1.json'

def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod
asset_expression=_load('fa134_asset_expression',ROOT/'company/factory-asset/lib/asset_expression_plan.py')

class CognitionRoutingError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def load_policy()->dict[str,Any]: return json.loads(POLICY_PATH.read_text(encoding='utf-8'))

def _expression(plan:dict[str,Any],semantic_asset_id:str)->dict[str,Any]:
    rows=[x for x in plan.get('expressions',[]) if x.get('semantic_asset_id')==semantic_asset_id]
    if len(rows)!=1: raise CognitionRoutingError('EXPRESSION_NOT_UNIQUE',semantic_asset_id)
    return rows[0]

def _bool_map(name:str,value:dict[str,Any],keys:list[str])->dict[str,bool]:
    if not isinstance(value,dict): raise CognitionRoutingError(f'{name.upper()}_INVALID','object required')
    unknown=sorted(set(value)-set(keys));missing=sorted(set(keys)-set(value))
    if unknown: raise CognitionRoutingError(f'{name.upper()}_UNKNOWN_FIELD',','.join(unknown))
    if missing: raise CognitionRoutingError(f'{name.upper()}_MISSING_FIELD',','.join(missing))
    if any(type(value[k]) is not bool for k in keys): raise CognitionRoutingError(f'{name.upper()}_BOOLEAN_REQUIRED',name)
    return {k:value[k] for k in keys}

def route_cognition(*,plan:dict[str,Any],semantic_asset_id:str,blueprint_state:dict[str,Any],signals:dict[str,Any],policy:dict[str,Any]|None=None)->dict[str,Any]:
    try: asset_expression.validate_asset_expression_plan(plan)
    except Exception as exc: raise CognitionRoutingError('EXPRESSION_PLAN_INVALID',f'{getattr(exc,"code","UNKNOWN")}:{exc}') from exc
    if plan.get('decision')!='SELECT': raise CognitionRoutingError('PLAN_NOT_SELECTABLE',str(plan.get('decision')))
    expression=_expression(plan,semantic_asset_id)
    p=policy or load_policy()
    reuse_keys=list(p['blueprint_reuse_checks'])
    state_keys=['exists','fixed','stale',*reuse_keys]
    state=_bool_map('blueprint_state',{k:v for k,v in blueprint_state.items() if k!='blueprint_sha256'},state_keys)
    sha=blueprint_state.get('blueprint_sha256')
    if state['exists']:
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha): raise CognitionRoutingError('BLUEPRINT_SHA256_REQUIRED','existing blueprint must be hash pinned')
    elif sha is not None: raise CognitionRoutingError('BLUEPRINT_SHA256_FORBIDDEN','missing blueprint cannot have hash')
    signal_keys=['qa_semantic_defect','family_overlap_requires_differentiation','bounded_semantic_question','new_family_promotion','material_product_expression_change','repeated_outcome_strategy_challenge','portfolio_cannibalization_material','explicit_executive_escalation']
    sig=_bool_map('signals',signals,signal_keys)

    incompat=[k for k in reuse_keys if not state[k]]
    division_reasons=[]
    if not state['exists']: division_reasons.append('BLUEPRINT_MISSING')
    elif not state['fixed']: division_reasons.append('BLUEPRINT_NOT_FIXED')
    if state['stale']: division_reasons.append('BLUEPRINT_STALE')
    if incompat: division_reasons.extend(f'BLUEPRINT_INCOMPATIBLE_{k.upper()}' for k in incompat)
    if sig['qa_semantic_defect']: division_reasons.append('QA_SEMANTIC_DEFECT')
    if sig['family_overlap_requires_differentiation']: division_reasons.append('FAMILY_DIFFERENTIATION_REQUIRED')
    if sig['bounded_semantic_question']: division_reasons.append('BOUNDED_SEMANTIC_QUESTION')
    if sig['material_product_expression_change']: division_reasons.append('MATERIAL_PRODUCT_EXPRESSION_CHANGE')

    executive_map={
      'new_family_promotion':'NEW_FAMILY_PROMOTION',
      'material_product_expression_change':'MATERIAL_PRODUCT_EXPRESSION_CHANGE',
      'repeated_outcome_strategy_challenge':'REPEATED_OUTCOME_STRATEGY_CHALLENGE',
      'portfolio_cannibalization_material':'PORTFOLIO_CANNIBALIZATION_MATERIAL',
      'explicit_executive_escalation':'EXPLICIT_EXECUTIVE_ESCALATION',
    }
    executive_reasons=[reason for key,reason in executive_map.items() if sig[key]]

    if division_reasons:
        division_action='AUTHOR' if not state['exists'] else 'REVISE'
    else: division_action='NONE'
    executive_action='CHALLENGE' if executive_reasons else 'NONE'
    reuse_allowed=state['exists'] and state['fixed'] and not state['stale'] and not incompat and not division_reasons
    if reuse_allowed and executive_action=='NONE': outcome='REUSE_FIXED_BLUEPRINT'
    elif division_action=='AUTHOR' and executive_action=='CHALLENGE': outcome='DIVISION01_AUTHOR_THEN_EXECUTIVE_CHALLENGE'
    elif division_action=='REVISE' and executive_action=='CHALLENGE': outcome='DIVISION01_REVISE_THEN_EXECUTIVE_CHALLENGE'
    elif division_action=='AUTHOR': outcome='DIVISION01_AUTHOR'
    elif division_action=='REVISE': outcome='DIVISION01_REVISE'
    elif executive_action=='CHALLENGE': outcome='EXECUTIVE_CHALLENGE_EXISTING_BLUEPRINT'
    else: raise CognitionRoutingError('COGNITION_ROUTE_INDETERMINATE','no valid outcome')

    sequence=[]
    if division_action!='NONE': sequence.append({'actor':'DIVISION01','action':division_action,'authority':'SEMANTIC_AUTHOR_ONLY'})
    if executive_action!='NONE': sequence.append({'actor':'EXECUTIVE','action':'CHALLENGE','authority':'STRATEGIC_REVIEW_ONLY'})
    sequence.append({'actor':'HERMES','action':'REUSE_FIXED_BLUEPRINT' if reuse_allowed else 'FREEZE_ACCEPTED_BLUEPRINT_AFTER_REQUIRED_COGNITION','authority':'ORCHESTRATION_ONLY'})
    result={
      'schema':'die.factory-asset.cognition-route.v1','result':'ROUTED','plan_id':plan['plan_id'],'semantic_asset_id':semantic_asset_id,'semantic_mode':expression['semantic_mode'],'producer_class':expression['producer_class'],
      'outcome':outcome,'reuse_allowed':reuse_allowed,'blueprint_sha256':sha if state['exists'] else None,'division01':{'action':division_action,'reasons':division_reasons},'executive':{'action':executive_action,'reasons':executive_reasons},'sequence':sequence,
      'per_image_cognition_gate':False,'worker_authority_granted':False,'provider_authority_granted':False,'submission_authority':'FOUNDER_CONTROLLED'
    }
    result['routing_key']=_sha({k:result[k] for k in ('plan_id','semantic_asset_id','outcome','blueprint_sha256','division01','executive')})
    return result