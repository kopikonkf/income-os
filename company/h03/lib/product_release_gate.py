from __future__ import annotations

from typing import Any

QC_SCHEMA='die.h03.founder-product-qc.v1'


def validate_founder_qc(qc:dict[str,Any], *, product_id:str, review_card_id:str)->dict[str,Any]:
    if not isinstance(qc,dict) or qc.get('schema_version')!=QC_SCHEMA or qc.get('holding_id')!='H03':
        raise ValueError('FOUNDER_QC_SCHEMA_INVALID')
    if qc.get('product_id')!=product_id or qc.get('review_card_id')!=review_card_id:
        raise ValueError('FOUNDER_QC_LINEAGE_MISMATCH')
    if qc.get('decision') not in {'PASS','REVISE','REJECT'}:
        raise ValueError('FOUNDER_QC_DECISION_INVALID')
    if qc.get('rights_release') not in {'APPROVED','HOLD','REJECTED'}:
        raise ValueError('FOUNDER_QC_RIGHTS_INVALID')
    if not isinstance(qc.get('reviewed_artifacts'),list) or not qc['reviewed_artifacts']:
        raise ValueError('FOUNDER_QC_ARTIFACTS_REQUIRED')
    if not isinstance(qc.get('publication_authorized'),bool):
        raise ValueError('FOUNDER_QC_PUBLICATION_FLAG_REQUIRED')
    if qc['decision']!='PASS' and qc['publication_authorized']:
        raise ValueError('FOUNDER_QC_NONPASS_CANNOT_AUTHORIZE_PUBLICATION')
    if qc['rights_release']!='APPROVED' and qc['publication_authorized']:
        raise ValueError('FOUNDER_QC_RIGHTS_HOLD_CANNOT_AUTHORIZE_PUBLICATION')
    return qc


def evaluate_release_gate(*, review_card:dict[str,Any], founder_qc:dict[str,Any]|None)->dict[str,Any]:
    if review_card.get('schema_version')!='die.h03.founder-review-card.v1':
        raise ValueError('RELEASE_REVIEW_CARD_INVALID')
    if review_card.get('decision_authority')!='INDEPENDENT_REVIEWER_NOT_FOUNDER':
        raise ValueError('RELEASE_REVIEW_AUTHORITY_AMBIGUOUS')
    if review_card.get('founder_action_required') is not True:
        raise ValueError('RELEASE_REVIEW_FOUNDER_GATE_MISSING')
    if review_card.get('external_publication_authorized') is not False:
        raise ValueError('RELEASE_REVIEW_PREMATURE_PUBLICATION_AUTH')
    if founder_qc is None:
        return {
            'state':'WAITING_FOUNDER_QC',
            'product_id':review_card['product_id'],
            'independent_review_decision':review_card['decision'],
            'founder_qc_decision':None,
            'publication_authorized':False,
        }
    validate_founder_qc(founder_qc,product_id=review_card['product_id'],review_card_id=review_card['review_card_id'])
    if founder_qc['decision']=='REJECT': state='REJECTED_BY_FOUNDER'
    elif founder_qc['decision']=='REVISE': state='REVISION_REQUIRED'
    elif founder_qc['rights_release']!='APPROVED': state='RIGHTS_HOLD'
    elif not founder_qc['publication_authorized']: state='QC_PASS_PUBLICATION_NOT_AUTHORIZED'
    else: state='READY_FOR_PUBLICATION_PREFLIGHT'
    return {
        'state':state,
        'product_id':review_card['product_id'],
        'independent_review_decision':review_card['decision'],
        'founder_qc_decision':founder_qc['decision'],
        'publication_authorized':bool(founder_qc['publication_authorized']),
    }
