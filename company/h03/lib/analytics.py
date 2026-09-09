from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path: sys.path.insert(0,str(_LIB))
import attribution

OBS_SCHEMA='die.h03.analytics-observation.v1'
AGG_SCHEMA='die.h03.analytics-aggregate.v1'
METRICS=('IMPRESSION','CLICK','PRODUCT_VIEW','ADD_TO_CART','ORDER','REVENUE','REFUND')


def load_source_registry()->dict[str,Any]:
    p=Path(__file__).resolve().parents[1]/'runtime'/'analytics-source-registry.v1.json'
    return json.loads(p.read_text(encoding='utf-8'))


def _metric_unknown()->dict[str,Any]:
    return {'state':'UNKNOWN','value':None,'currency':None,'evidence_refs':[]}


def _metric_observed(value:int, evidence_refs:list[str], currency:str|None=None)->dict[str,Any]:
    if not isinstance(value,int) or value<0 or not evidence_refs: raise ValueError('ANALYTICS_METRIC_OBSERVED_INVALID')
    return {'state':'OBSERVED','value':value,'currency':currency,'evidence_refs':list(dict.fromkeys(evidence_refs))}


def build_unknown_observation(*, source_id:str, source_family:str, observed_at:str, identity:dict[str,Any], source_record_ref:str)->dict[str,Any]:
    attribution.validate_identity(identity)
    return {'schema_version':OBS_SCHEMA,'observation_id':'H03-ANL-UNK-'+hashlib.sha256((source_id+'|'+identity['creative_id']+'|'+observed_at).encode()).hexdigest()[:16].upper(),'holding_id':'H03','source_id':source_id,'source_family':source_family,'observed_at':observed_at,'identity':identity,'metrics':{m:_metric_unknown() for m in METRICS},'referrer':{'state':'UNKNOWN','value':None,'evidence_refs':[]},'source_record_ref':source_record_ref}


def normalize_snapshot(*, source_id:str, source_family:str, observed_at:str, identity:dict[str,Any], source_record_ref:str, metrics:dict[str,Any], referrer:dict[str,Any]|None=None)->dict[str,Any]:
    obs=build_unknown_observation(source_id=source_id,source_family=source_family,observed_at=observed_at,identity=identity,source_record_ref=source_record_ref)
    for name,payload in (metrics or {}).items():
        if name not in METRICS: raise ValueError(f'ANALYTICS_METRIC_UNKNOWN:{name}')
        if payload is None or payload.get('state')=='UNKNOWN':
            continue
        if payload.get('state')!='OBSERVED': raise ValueError('ANALYTICS_METRIC_STATE_INVALID')
        currency=payload.get('currency')
        if name in {'REVENUE','REFUND'} and not currency: raise ValueError('ANALYTICS_MONEY_CURRENCY_REQUIRED')
        if name not in {'REVENUE','REFUND'} and currency is not None: raise ValueError('ANALYTICS_CURRENCY_NONMONEY_FORBIDDEN')
        obs['metrics'][name]=_metric_observed(payload.get('value'),payload.get('evidence_refs') or [],currency)
    if referrer and referrer.get('state')=='OBSERVED':
        if not referrer.get('value') or not referrer.get('evidence_refs'): raise ValueError('ANALYTICS_REFERRER_EVIDENCE_REQUIRED')
        obs['referrer']={'state':'OBSERVED','value':str(referrer['value']),'evidence_refs':list(dict.fromkeys(referrer['evidence_refs']))}
    return obs


def to_attribution_events(observation:dict[str,Any])->list[dict[str,Any]]:
    if observation.get('schema_version')!=OBS_SCHEMA: raise ValueError('ANALYTICS_OBSERVATION_SCHEMA_INVALID')
    events=[]
    identity=observation['identity']
    for name in METRICS:
        metric=observation['metrics'][name]
        if metric['state']!='OBSERVED': continue
        # Aggregate counts are analytics observations. Attribution events represent evidence-bearing source events;
        # only one event is emitted per observed metric snapshot, carrying the source snapshot as evidence.
        order_id=None; money=None
        if name in {'ORDER','REVENUE','REFUND'}:
            order_id=f"AGGREGATE:{observation['source_event_id']}" if observation.get('source_event_id') else f"AGGREGATE:{observation['observation_id']}"
        if name in {'REVENUE','REFUND'}:
            money={'currency':metric['currency'],'amount_minor':metric['value']}
        events.append(attribution.build_observed_event(event_type=name,identity=identity,observed_at=observation['observed_at'],source_event_id=f"{observation['source_id']}:{observation['observation_id']}:{name}",evidence_refs=metric['evidence_refs'],order_id=order_id,money=money))
    return events


def aggregate(observations:list[dict[str,Any]], *, group_by:str)->list[dict[str,Any]]:
    if group_by not in {'channel_id','listing_channel_id','campaign_id','creative_id','product_id'}: raise ValueError('ANALYTICS_GROUP_BY_INVALID')
    if not observations: return []
    groups:dict[str,list[dict[str,Any]]]={}
    for obs in observations:
        if obs.get('schema_version')!=OBS_SCHEMA: raise ValueError('ANALYTICS_OBSERVATION_SCHEMA_INVALID')
        key=obs['identity'][group_by]
        groups.setdefault(key,[]).append(obs)
    out=[]
    for key,rows in groups.items():
        metrics={}
        for name in METRICS:
            observed=[r['metrics'][name] for r in rows if r['metrics'][name]['state']=='OBSERVED']
            if not observed:
                metrics[name]={'state':'UNKNOWN','value':None,'currency':None}
                continue
            state='OBSERVED' if len(observed)==len(rows) else 'PARTIAL'
            currencies={m['currency'] for m in observed if m['currency']}
            if name in {'REVENUE','REFUND'} and len(currencies)>1: raise ValueError('ANALYTICS_MIXED_CURRENCY_REQUIRES_SEPARATE_AGGREGATION')
            metrics[name]={'state':state,'value':sum(m['value'] for m in observed),'currency':next(iter(currencies)) if currencies else None}
        denominator_name=None
        if metrics['PRODUCT_VIEW']['state']=='OBSERVED' and metrics['ORDER']['state']=='OBSERVED': denominator_name='PRODUCT_VIEW'
        elif metrics['CLICK']['state']=='OBSERVED' and metrics['ORDER']['state']=='OBSERVED': denominator_name='CLICK'
        if denominator_name and metrics[denominator_name]['value']>0:
            conversion={'state':'OBSERVED','numerator':'ORDER','denominator':denominator_name,'value':metrics['ORDER']['value']/metrics[denominator_name]['value']}
        else:
            conversion={'state':'UNKNOWN','numerator':'ORDER','denominator':denominator_name,'value':None}
        referrers=[]
        for r in rows:
            if r['referrer']['state']=='OBSERVED' and r['referrer']['value'] not in referrers: referrers.append(r['referrer']['value'])
        out.append({'schema_version':AGG_SCHEMA,'holding_id':'H03','group_by':group_by,'group_key':key,'record_count':len(rows),'metrics':metrics,'conversion':conversion,'referrers':referrers})
    out.sort(key=lambda x:x['group_key'])
    return out
