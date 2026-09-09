from __future__ import annotations

from typing import Any

SCHEMA='die.h03.first-dollar-canary.v1'
SELLER_READY={'AUTHENTICATED','READY'}
SOCIAL_READY={'AUTHENTICATED','READY'}


def build_canary(*, product_id:str, price_hypothesis:dict[str,Any], seller_preflight:dict[str,str], social_preflight:dict[str,str], phase_authorized:bool, founder_qc_state:str, product_release_authorized:bool, runtime_boundary_state:str, primary_checkout:str='gumroad', backup_checkout:str='payhip', promotion_cohort:list[str]|None=None, listing_published:bool=False, promotions_published:bool=False, observed_revenue_minor:int|None=None)->dict[str,Any]:
    if not phase_authorized:
        raise ValueError('FIRST_DOLLAR_PHASE_AUTH_REQUIRED')
    if founder_qc_state not in {'PENDING','PASS','REVISE','REJECT'}:
        raise ValueError('FIRST_DOLLAR_FOUNDER_QC_STATE_INVALID')
    if product_release_authorized and founder_qc_state!='PASS':
        raise ValueError('FIRST_DOLLAR_RELEASE_REQUIRES_FOUNDER_QC_PASS')
    if runtime_boundary_state not in {'UNPROVEN','VALID_H03_DEDICATED','INVALID_FOREIGN_PROFILE_EVIDENCE'}:
        raise ValueError('FIRST_DOLLAR_RUNTIME_BOUNDARY_STATE_INVALID')
    if listing_published and not product_release_authorized:
        raise ValueError('FIRST_DOLLAR_PUBLICATION_WITHOUT_PRODUCT_RELEASE_AUTH')
    if not product_id or not isinstance(price_hypothesis,dict):
        raise ValueError('FIRST_DOLLAR_PRODUCT_OR_PRICE_INVALID')
    cohort=promotion_cohort or ['facebook_page','facebook_group','pinterest','reddit','youtube']
    if primary_checkout not in seller_preflight or backup_checkout not in seller_preflight:
        raise ValueError('FIRST_DOLLAR_SELLER_PREFLIGHT_INCOMPLETE')
    if any(c not in social_preflight for c in cohort):
        raise ValueError('FIRST_DOLLAR_SOCIAL_PREFLIGHT_INCOMPLETE')

    if founder_qc_state!='PASS':
        distribution_state='BLOCKED_FOUNDER_QC'
        growth_state='BLOCKED_FOUNDER_QC'
        next_action='Founder must inspect the actual product package and issue a Founder Product QC decision. Independent reviewer PASS is not Founder QC.'
    elif not product_release_authorized:
        distribution_state='BLOCKED_PRODUCT_RELEASE_AUTH'
        growth_state='BLOCKED_DISTRIBUTION_NOT_LIVE'
        next_action='Founder QC passed, but explicit product release/publication authorization is still required.'
    elif runtime_boundary_state!='VALID_H03_DEDICATED':
        distribution_state='BLOCKED_RUNTIME_BOUNDARY'
        growth_state='BLOCKED_RUNTIME_BOUNDARY'
        next_action='Provision and validate H03-dedicated Commerce/Growth browser profiles; foreign Mission Control/principal profiles cannot satisfy H03 readiness.'
    else:
        primary_ready=seller_preflight[primary_checkout] in SELLER_READY
        if listing_published:
            distribution_state='PUBLISHED'
        elif primary_ready:
            distribution_state='READY_FOR_BOUNDED_PUBLICATION'
        else:
            distribution_state='BLOCKED_SELLER_ACCOUNT_PREFLIGHT'
        ready_social=[c for c in cohort if social_preflight[c] in SOCIAL_READY]
        if distribution_state!='PUBLISHED':
            growth_state='BLOCKED_DISTRIBUTION_NOT_LIVE'
        elif not ready_social:
            growth_state='BLOCKED_SOCIAL_ACCOUNT_PREFLIGHT'
        elif promotions_published:
            growth_state='PROMOTED'
        else:
            growth_state='READY_FOR_BOUNDED_ORGANIC_PROMOTION'
        if distribution_state=='BLOCKED_SELLER_ACCOUNT_PREFLIGHT':
            next_action=f'Complete one-time seller authentication/onboarding for {primary_checkout} inside the H03-dedicated Commerce profile.'
        elif distribution_state=='READY_FOR_BOUNDED_PUBLICATION':
            next_action=f'Publish exactly one bounded {primary_checkout} listing using the Founder-approved product package.'
        elif growth_state=='BLOCKED_SOCIAL_ACCOUNT_PREFLIGHT':
            next_action='Authenticate at least one bounded organic acquisition channel inside the H03-dedicated Growth profile.'
        elif growth_state=='READY_FOR_BOUNDED_ORGANIC_PROMOTION':
            next_action='Publish the bounded organic promotion cohort with existing campaign/creative attribution IDs.'
        elif observed_revenue_minor is None:
            next_action='Collect read-only analytics and wait for evidence-backed traffic/order/revenue observations.'
        elif observed_revenue_minor >= 100:
            next_action='FIRST_DOLLAR_MILESTONE_OBSERVED: feed evidence to ANL-001/ANL-002 and preserve receipts.'
        else:
            next_action='Continue bounded observation until cumulative evidence-backed revenue reaches at least USD 1 equivalent.'
    return {
        'schema_version':SCHEMA,'holding_id':'H03','canary_id':f'H03-FIRST-DOLLAR-{product_id}','product_id':product_id,
        'phase_authorized':True,'founder_qc_state':founder_qc_state,'product_release_authorized':bool(product_release_authorized),'runtime_boundary_state':runtime_boundary_state,
        'price_hypothesis':price_hypothesis,'primary_checkout':primary_checkout,'backup_checkout':backup_checkout,'promotion_cohort':cohort,
        'seller_preflight':dict(seller_preflight),'social_preflight':dict(social_preflight),'distribution_state':distribution_state,'growth_state':growth_state,
        'paid_ads':False,'external_publication_occurred':bool(listing_published or promotions_published),'observed_revenue_minor':observed_revenue_minor,'next_required_action':next_action,
    }
