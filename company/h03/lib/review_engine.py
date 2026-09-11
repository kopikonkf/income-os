from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path: sys.path.insert(0,str(_LIB))
import cognition_work_card

SCHEMA='die.h03.founder-review-card.v1'


def build_reviewer_work_card(*, product_id:str, package_ref:str) -> dict[str,Any]:
    card={
        'schema_version':cognition_work_card.CARD_SCHEMA,'work_card_id':f'H03-WC-REV-{product_id}','holding_id':'H03','task_id':'H03-REV-001','role':'REVIEWER','queue':'review','idempotency_key':f'h03-review:{product_id}',
        'input_artifacts':[{'artifact_id':product_id,'kind':'local_product_package','ref':package_ref,'sha256':None}],
        'output_contract':{'artifact_kind':'founder_review_card','schema_version':SCHEMA},
        'capability_requirements':cognition_work_card.standard_web_ai_capabilities(),
        'terminal_policy':{'max_attempts':2,'retryable_failures':['PROVIDER_UNAVAILABLE','INVALID_OUTPUT']},
    }
    return cognition_work_card.validate_work_card(card)


def build_review_card(*, lineage:dict[str,Any], problem_seed:dict[str,Any], demand_packet:dict[str,Any], knowledge_package:dict[str,Any], blueprint:dict[str,Any], package_receipt:dict[str,Any], reviewer_provider_id:str, dominant_producer_provider_id:str, reviewer_fixture:dict[str,Any], execution_mode:str="NONLIVE_ROLE_FIXTURE") -> dict[str,Any]:
    if reviewer_provider_id==dominant_producer_provider_id:
        raise ValueError('REVIEWER_SEPARATION_REQUIRED_WHEN_CAPACITY_AVAILABLE')
    decision=reviewer_fixture.get('decision')
    if decision not in {'PASS','REVISE','REJECT'}: raise ValueError('REVIEW_DECISION_INVALID')
    risks=reviewer_fixture.get('risk_flags') or []
    rights=reviewer_fixture.get('rights_flags') or []
    reasons=reviewer_fixture.get('decision_reasons') or []
    if not reasons: raise ValueError('REVIEW_REASONS_REQUIRED')
    return {
        'schema_version':SCHEMA,'review_card_id':f'H03-RC-{blueprint["product_id"]}','holding_id':'H03','product_id':blueprint['product_id'],
        'reviewer_observation':{'provider_id':reviewer_provider_id,'execution_mode':execution_mode,'separated_from_dominant_producer':True},
        'buyer':problem_seed['persona']['actor'],'problem':problem_seed['pain']['statement'],'promise':problem_seed['desired_outcome'],
        'product_preview':{'title':blueprint['title'],'form':blueprint['form'],'sections':[s['heading'] for s in blueprint['sections']],'page_count':package_receipt['page_count'],'package_status':package_receipt['status']},
        'evidence_confidence':reviewer_fixture.get('evidence_confidence','MEDIUM'),
        'market_wtp_basis':{'wtp_assessment':demand_packet['wtp_assessment'],'evidence_ids':[e['evidence_id'] for e in demand_packet['evidence']]},
        'risk_flags':risks,'rights_flags':rights,'decision':decision,'decision_reasons':reasons,
        'review_layer':'INDEPENDENT_PRE_FOUNDER_REVIEW','decision_authority':'INDEPENDENT_REVIEWER_NOT_FOUNDER',
        'founder_action_required':True,'external_publication_authorized':False,
    }
