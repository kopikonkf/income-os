from __future__ import annotations

import hashlib
from typing import Any

IDENTITY_SCHEMA='die.h03.attribution-identity.v1'
EVENT_SCHEMA='die.h03.attribution-event.v1'
EVENT_TYPES={'IMPRESSION','CLICK','PRODUCT_VIEW','ADD_TO_CART','ORDER','REVENUE','REFUND'}


def _slug(value:str)->str:
    out=''.join(c.lower() if c.isalnum() else '-' for c in value).strip('-')
    while '--' in out: out=out.replace('--','-')
    return out[:80] or 'h03'


def build_identity(*, problem_seed_id:str, product_id:str, commerce_package_id:str, channel_id:str, listing_channel_id:str, campaign_key:str, creative_key:str, destination_url:str|None=None) -> dict[str,Any]:
    listing_id=f'H03-LIST-{_slug(product_id)}-{_slug(listing_channel_id)}'
    campaign_id=f'H03-CAMP-{_slug(product_id)}-{_slug(campaign_key)}'
    creative_id=f'H03-CR-{_slug(product_id)}-{_slug(channel_id)}-{_slug(creative_key)}'
    state='PUBLISHED_URL_KNOWN' if destination_url else 'UNPUBLISHED'
    identity={
        'schema_version':IDENTITY_SCHEMA,'holding_id':'H03','problem_seed_id':problem_seed_id,'product_id':product_id,
        'commerce_package_id':commerce_package_id,'listing_id':listing_id,'listing_channel_id':listing_channel_id,'campaign_id':campaign_id,'creative_id':creative_id,'channel_id':channel_id,
        'utm':{'utm_source':channel_id,'utm_medium':'organic','utm_campaign':campaign_id,'utm_content':creative_id},
        'destination_state':state,'destination_url':destination_url,
    }
    return validate_identity(identity)


def validate_identity(identity:dict[str,Any])->dict[str,Any]:
    if identity.get('schema_version')!=IDENTITY_SCHEMA or identity.get('holding_id')!='H03': raise ValueError('ATTR_IDENTITY_SCHEMA_INVALID')
    for field in ('problem_seed_id','product_id','commerce_package_id','listing_id','listing_channel_id','campaign_id','creative_id','channel_id'):
        if not isinstance(identity.get(field),str) or not identity[field].strip(): raise ValueError(f'ATTR_IDENTITY_FIELD_REQUIRED:{field}')
    utm=identity.get('utm') or {}
    if set(utm)!={'utm_source','utm_medium','utm_campaign','utm_content'}: raise ValueError('ATTR_UTM_INVALID')
    if identity.get('destination_state')=='UNPUBLISHED' and identity.get('destination_url') is not None: raise ValueError('ATTR_UNPUBLISHED_URL_FORBIDDEN')
    if identity.get('destination_state')=='PUBLISHED_URL_KNOWN' and not identity.get('destination_url'): raise ValueError('ATTR_PUBLISHED_URL_REQUIRED')
    return identity


def build_observed_event(*, event_type:str, identity:dict[str,Any], observed_at:str, source_event_id:str, evidence_refs:list[str], order_id:str|None=None, money:dict[str,Any]|None=None) -> dict[str,Any]:
    validate_identity(identity)
    if event_type not in EVENT_TYPES: raise ValueError('ATTR_EVENT_TYPE_INVALID')
    if not evidence_refs or len(evidence_refs)!=len(set(evidence_refs)): raise ValueError('ATTR_EVENT_EVIDENCE_REQUIRED')
    if event_type in {'ORDER','REVENUE','REFUND'} and not order_id: raise ValueError('ATTR_ORDER_ID_REQUIRED')
    if event_type in {'REVENUE','REFUND'}:
        if not isinstance(money,dict) or not isinstance(money.get('amount_minor'),int) or money['amount_minor']<0 or not money.get('currency'): raise ValueError('ATTR_MONEY_REQUIRED')
    elif money is not None:
        raise ValueError('ATTR_MONEY_ONLY_FOR_REVENUE_REFUND')
    raw='|'.join([event_type,identity['creative_id'],observed_at,source_event_id])
    eid='H03-ATTR-EVT-'+hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
    return {'schema_version':EVENT_SCHEMA,'event_id':eid,'holding_id':'H03','observed_at':observed_at,'event_type':event_type,'observation_state':'OBSERVED','identity':identity,'source_event_id':source_event_id,'evidence_refs':list(evidence_refs),'order_id':order_id,'money':money}


def build_unobserved_funnel_state(*, identity:dict[str,Any]) -> dict[str,Any]:
    validate_identity(identity)
    return {'schema_version':'die.h03.unobserved-funnel-state.v1','identity':identity,'states':{k:'UNOBSERVED' for k in ('IMPRESSION','CLICK','PRODUCT_VIEW','ADD_TO_CART','ORDER','REVENUE','REFUND')}}
