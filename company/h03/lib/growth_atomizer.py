from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path: sys.path.insert(0,str(_LIB))
import attribution
import cognition_work_card

BLUEPRINT_SCHEMA='die.h03.growth-blueprint.v1'
ATOM_SCHEMA='die.h03.growth-content-atom.v1'
EXECUTION_MODE='NONLIVE_ROLE_FIXTURE'


def load_registry()->dict[str,Any]:
    p=Path(__file__).resolve().parents[1]/'runtime'/'growth-channel-registry.v1.json'
    return json.loads(p.read_text(encoding='utf-8'))


def _claim_index(kp:dict[str,Any])->dict[str,dict[str,Any]]:
    if kp.get('schema_version')!='die.h03.knowledge-package.v1' or kp.get('holding_id')!='H03': raise ValueError('GROWTH_KP_INVALID')
    claims={c['claim_id']:c for c in kp.get('claims') or [] if c.get('claim_id')}
    if not claims: raise ValueError('GROWTH_KP_CLAIMS_REQUIRED')
    return claims


def build_work_cards(*, commerce_package:dict[str,Any], knowledge_package:dict[str,Any], campaign_key:str, listing_channel_id:str, registry:dict[str,Any]|None=None)->list[dict[str,Any]]:
    claims=_claim_index(knowledge_package)
    if commerce_package.get('schema_version')!='die.h03.commerce-package.v1': raise ValueError('GROWTH_COMMERCE_PACKAGE_INVALID')
    if commerce_package.get('publication_authority',{}).get('external_publication_authorized') is not False: raise ValueError('GROWTH_PUBLICATION_AUTHORITY_INVALID')
    registry=registry or load_registry(); channels=registry.get('channels') or []
    cards=[]
    for channel in channels:
        cid=channel['channel_id']
        card={
            'schema_version':cognition_work_card.CARD_SCHEMA,'work_card_id':f'H03-WC-GRW-{commerce_package["product_id"]}-{cid}','holding_id':'H03','task_id':'H03-GRW-001','role':'GROWTH_PRODUCER','queue':'growth','idempotency_key':f'h03-growth:{commerce_package["product_id"]}:{campaign_key}:{cid}',
            'input_artifacts':[
                {'artifact_id':commerce_package['commerce_package_id'],'kind':'commerce_package','ref':f'artifact://commerce/{commerce_package["commerce_package_id"]}','sha256':None},
                {'artifact_id':knowledge_package['knowledge_package_id'],'kind':'knowledge_package','ref':f'artifact://knowledge/{knowledge_package["knowledge_package_id"]}','sha256':None},
            ],
            'output_contract':{'artifact_kind':'growth_content_atom','schema_version':ATOM_SCHEMA},
            'capability_requirements':cognition_work_card.standard_web_ai_capabilities(),
            'terminal_policy':{'max_attempts':2,'retryable_failures':['PROVIDER_UNAVAILABLE','INVALID_OUTPUT']},
        }
        cards.append(cognition_work_card.validate_work_card(card))
    return cards


def normalize_atom(*, card:dict[str,Any], channel:dict[str,Any], commerce_package:dict[str,Any], knowledge_package:dict[str,Any], campaign_key:str, listing_channel_id:str, model_output:dict[str,Any])->dict[str,Any]:
    cognition_work_card.validate_work_card(card); claims=_claim_index(knowledge_package)
    ids=model_output.get('claim_ids') or []
    if not ids or len(ids)!=len(set(ids)) or any(cid not in claims for cid in ids): raise ValueError('GROWTH_CLAIM_SCOPE_INVALID')
    content=model_output.get('content')
    if not isinstance(content,dict) or not content: raise ValueError('GROWTH_CONTENT_REQUIRED')
    refs=[]
    for cid in ids:
        for ref in claims[cid].get('evidence_refs') or []:
            if ref not in refs: refs.append(ref)
    identity=attribution.build_identity(problem_seed_id=commerce_package['problem_seed_id'],product_id=commerce_package['product_id'],commerce_package_id=commerce_package['commerce_package_id'],channel_id=channel['channel_id'],listing_channel_id=listing_channel_id,campaign_key=campaign_key,creative_key=channel['surface'].lower())
    return {
        'schema_version':ATOM_SCHEMA,'holding_id':'H03','atom_id':f'H03-ATOM-{commerce_package["product_id"]}-{channel["channel_id"]}','product_id':commerce_package['product_id'],'channel_id':channel['channel_id'],'surface':channel['surface'],'campaign_id':identity['campaign_id'],'creative_id':identity['creative_id'],'attribution_identity':identity,'claim_ids':list(ids),'evidence_refs':refs,'content':content,'execution_mode':EXECUTION_MODE,'paid_ads':False,'publication_authorized':False,
    }


def build_blueprint(*, commerce_package:dict[str,Any], atoms:list[dict[str,Any]], objective:str)->dict[str,Any]:
    if not atoms: raise ValueError('GROWTH_ATOMS_REQUIRED')
    campaign_ids={a['campaign_id'] for a in atoms}
    if len(campaign_ids)!=1: raise ValueError('GROWTH_CAMPAIGN_ID_MISMATCH')
    channels=[]
    for atom in atoms:
        if atom.get('publication_authorized') is not False or atom.get('paid_ads') is not False: raise ValueError('GROWTH_SAFETY_BOUNDARY_INVALID')
        channels.append({'channel_id':atom['channel_id'],'surface':atom['surface'],'atom_id':atom['atom_id'],'creative_id':atom['creative_id'],'claim_ids':list(atom['claim_ids']),'evidence_refs':list(atom['evidence_refs'])})
    return {'schema_version':BLUEPRINT_SCHEMA,'holding_id':'H03','growth_blueprint_id':f'H03-GRW-BP-{commerce_package["product_id"]}','product_id':commerce_package['product_id'],'commerce_package_id':commerce_package['commerce_package_id'],'campaign_id':next(iter(campaign_ids)),'objective':objective,'paid_ads_enabled':False,'channels':channels,'publication_authorized':False}
