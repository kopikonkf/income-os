from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0,str(_LIB))
import demand_wtp
import analytics

SCHEMA='die.h03.demand-feedback-calibration.v1'
_INTENT_RANK={'UNKNOWN':0,'WEAK':1,'MEDIUM':2,'STRONG':3}
_WTP_RANK={'UNKNOWN':0,'WEAK':1,'MEDIUM':2,'STRONG':3}


def _max_level(current:str, candidate:str, ranks:dict[str,int])->str:
    return candidate if ranks[candidate] > ranks[current] else current


def _evidence_refs_for_metric(obs:dict[str,Any], metric_name:str)->list[str]:
    metric=(obs.get('metrics') or {}).get(metric_name) or {}
    if metric.get('state')!='OBSERVED': return []
    return list(metric.get('evidence_refs') or [])


def _metric_value(obs:dict[str,Any], metric_name:str)->int|None:
    metric=(obs.get('metrics') or {}).get(metric_name) or {}
    if metric.get('state')!='OBSERVED': return None
    return metric.get('value')


def _validate_inputs(demand_packet:dict[str,Any], observations:list[dict[str,Any]], product_id:str)->None:
    demand_wtp.validate_demand_packet(demand_packet)
    if not isinstance(product_id,str) or not product_id.strip(): raise ValueError('DEMAND_FEEDBACK_PRODUCT_ID_REQUIRED')
    for obs in observations:
        if obs.get('schema_version')!=analytics.OBS_SCHEMA: raise ValueError('DEMAND_FEEDBACK_ANALYTICS_SCHEMA_INVALID')
        identity=obs.get('identity') or {}
        if identity.get('problem_seed_id')!=demand_packet['problem_seed_id']: raise ValueError('DEMAND_FEEDBACK_PROBLEM_SEED_MISMATCH')
        if identity.get('product_id')!=product_id: raise ValueError('DEMAND_FEEDBACK_PRODUCT_MISMATCH')


def build_calibration(*, demand_packet:dict[str,Any], observations:list[dict[str,Any]], product_id:str)->dict[str,Any]:
    _validate_inputs(demand_packet,observations,product_id)
    feedback=[]
    observed_counts={name:0 for name in analytics.METRICS}
    observed_values={name:0 for name in analytics.METRICS}
    currencies:set[str]=set()
    source_ids=[]
    for obs in observations:
        if obs['source_id'] not in source_ids: source_ids.append(obs['source_id'])
        for name in analytics.METRICS:
            metric=obs['metrics'][name]
            if metric['state']=='OBSERVED':
                observed_counts[name]+=1
                observed_values[name]+=int(metric['value'])
                if metric.get('currency'): currencies.add(metric['currency'])

    intent=demand_packet['buyer_intent_state']
    state='INSUFFICIENT_OBSERVED_OUTCOMES'
    # Revealed spend is the strongest signal and requires both observed orders and observed revenue.
    spend_obs=[o for o in observations if _metric_value(o,'ORDER') and _metric_value(o,'REVENUE')]
    if spend_obs:
        if len(currencies)>1: raise ValueError('DEMAND_FEEDBACK_MIXED_CURRENCY_REQUIRES_SEPARATE_CALIBRATION')
        refs=[]; total_revenue=0; total_orders=0
        for obs in spend_obs:
            total_orders += int(_metric_value(obs,'ORDER') or 0)
            total_revenue += int(_metric_value(obs,'REVENUE') or 0)
            for name in ('ORDER','REVENUE'):
                for ref in _evidence_refs_for_metric(obs,name):
                    if ref not in refs: refs.append(ref)
        feedback.append({'evidence_id':'H03-FB-REVEALED-SPEND','signal_type':'REVEALED_SPEND','evidence_refs':refs,'money':{'currency':next(iter(currencies)) if currencies else 'UNKNOWN','amount_minor':total_revenue},'observed_orders':total_orders,'interpretation':'Observed paid orders/revenue associated with this product establish revealed spend for the problem/product pair; they do not prove which channel or creative caused purchase.'})
        intent=_max_level(intent,'STRONG',_INTENT_RANK); state='REVEALED_SPEND_OBSERVED'
    else:
        sale_obs=[o for o in observations if (_metric_value(o,'ORDER') or 0)>0]
        if sale_obs:
            refs=[]; total_orders=0
            for obs in sale_obs:
                total_orders += int(_metric_value(obs,'ORDER') or 0)
                for ref in _evidence_refs_for_metric(obs,'ORDER'):
                    if ref not in refs: refs.append(ref)
            feedback.append({'evidence_id':'H03-FB-SALE-PROXY','signal_type':'MARKETPLACE_SALE_PROXY','evidence_refs':refs,'money':None,'observed_orders':total_orders,'interpretation':'Observed orders are a sale proxy; revenue/spend magnitude remains unknown.'})
            intent=_max_level(intent,'STRONG',_INTENT_RANK); state='SALE_PROXY_OBSERVED'
        else:
            cart_obs=[o for o in observations if (_metric_value(o,'ADD_TO_CART') or 0)>0]
            if cart_obs:
                refs=[]; total=0
                for obs in cart_obs:
                    total += int(_metric_value(obs,'ADD_TO_CART') or 0)
                    for ref in _evidence_refs_for_metric(obs,'ADD_TO_CART'):
                        if ref not in refs: refs.append(ref)
                feedback.append({'evidence_id':'H03-FB-PURCHASE-INTENT','signal_type':'PURCHASE_INTENT_SEARCH','evidence_refs':refs,'money':None,'observed_add_to_cart':total,'interpretation':'Add-to-cart is treated as bounded purchase-intent evidence, not payment or revealed spend.'})
                intent=_max_level(intent,'STRONG',_INTENT_RANK); state='PURCHASE_INTENT_OBSERVED'
            else:
                engagement_obs=[o for o in observations if any((_metric_value(o,n) or 0)>0 for n in ('IMPRESSION','CLICK','PRODUCT_VIEW'))]
                if engagement_obs:
                    refs=[]; total=0
                    for obs in engagement_obs:
                        for name in ('IMPRESSION','CLICK','PRODUCT_VIEW'):
                            value=_metric_value(obs,name)
                            if value:
                                total += int(value)
                                for ref in _evidence_refs_for_metric(obs,name):
                                    if ref not in refs: refs.append(ref)
                    feedback.append({'evidence_id':'H03-FB-ENGAGEMENT','signal_type':'ENGAGEMENT_ONLY','evidence_refs':refs,'money':None,'observed_engagement_units':total,'interpretation':'Observed reach/traffic indicates attention only; it is not willingness-to-pay evidence.'})
                    intent=_max_level(intent,'MEDIUM',_INTENT_RANK); state='ENGAGEMENT_ONLY'

    combined=copy.deepcopy(demand_packet['evidence'])+feedback
    recommended_wtp=demand_wtp.derive_wtp_assessment(combined)
    candidate=None
    if feedback:
        candidate=copy.deepcopy(demand_packet)
        candidate['packet_id']=demand_packet['packet_id']+'-CALIBRATION-CANDIDATE'
        candidate['evidence']=combined
        candidate['buyer_intent_state']=intent
        candidate['wtp_assessment']=recommended_wtp
        candidate['truth_status']='CANDIDATE'
        demand_wtp.validate_demand_packet(candidate)

    digest=hashlib.sha256((demand_packet['packet_id']+'|'+product_id+'|'+state+'|'+','.join(sorted(source_ids))).encode()).hexdigest()[:20].upper()
    return {
        'schema_version':SCHEMA,'holding_id':'H03','calibration_id':'H03-DMD-CAL-'+digest,'problem_seed_id':demand_packet['problem_seed_id'],'product_id':product_id,
        'source_demand_packet_id':demand_packet['packet_id'],'source_wtp_assessment':demand_packet['wtp_assessment'],'calibration_state':state,
        'observed_outcome_summary':{'observation_count':len(observations),'source_ids':source_ids,'observed_metric_record_counts':observed_counts,'observed_metric_totals':observed_values},
        'feedback_signals':feedback,'recommended_wtp_assessment':recommended_wtp,'recommended_buyer_intent_state':intent,
        'causal_claim':False,'causal_policy':'Observed outcomes are associated with the attributed product/channel/creative identity; calibration does not assert that a channel or creative caused the outcome.',
        'canonical_mutation_authorized':False,'calibrated_demand_packet_candidate':candidate,
    }
