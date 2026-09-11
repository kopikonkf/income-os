from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'company/factory-asset'
MODE_SIGNALS=BASE/'registries/opportunity-mode-signals.v1.json'
PRESETS=BASE/'registries/production-presets.v1.json'
ASSET_TYPES=BASE/'registries/asset-types.v1.json'
DISPATCH=BASE/'registries/producer-dispatch.v1.json'
TOKEN_RE=re.compile(r'[a-z0-9]+')

class OpportunityPlannerError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def _load(p:Path):return json.loads(p.read_text(encoding='utf-8'))
def _tokens(s:str)->set[str]:return set(TOKEN_RE.findall(str(s).casefold()))
def _norm_score(v:Any)->float:
    try:x=float(v)
    except Exception:return 0.0
    return max(0.0,min(1.0,x))
def _preset_rank(p:dict[str,Any])->float:
    return {'PRODUCTION_CHAMPION':1.0,'CANARY_ACCEPTED':0.9,'BASELINE_COMPATIBILITY_ONLY':0.85,'NOT_LIVE':0.45}.get(str(p.get('activation')),0.25)
def _engine_state(mode:str,producer:str)->str:
    reg=_load(DISPATCH)
    for row in reg['routes']:
        if row['producer_class']==producer and mode in row['semantic_modes']:return row['engine_state']
    return 'UNAVAILABLE'
def _context_text(c:dict[str,Any])->str:
    return ' '.join(str(c.get(k,'')) for k in ('human','activity','problem','industry','commercial_intent','use_case'))
def _hits(text:str,terms:list[str])->list[str]:
    low=text.casefold(); return sorted({t for t in terms if t.casefold() in low})
def plan_seed_opportunities(*,seed:dict[str,Any],bridge_result:dict[str,Any],limit:int=12)->dict[str,Any]:
    if not 1<=limit<=12:raise OpportunityPlannerError('LIMIT_INVALID',str(limit))
    if bridge_result.get('schema')!='die.factory-asset.dual-atlas-context-bridge.v1':raise OpportunityPlannerError('BRIDGE_SCHEMA_INVALID',str(bridge_result.get('schema')))
    if bridge_result.get('policy',{}).get('authority_effect')!='NONE':raise OpportunityPlannerError('BRIDGE_AUTHORITY_INVALID','must be NONE')
    for k in ('id','canonical_name','demand_status','demand_score','status'):
        if k not in seed:raise OpportunityPlannerError('SEED_FIELD_REQUIRED',k)
    if seed['status']!='approved':raise OpportunityPlannerError('SEED_NOT_APPROVED',str(seed['id']))
    signals=_load(MODE_SIGNALS); presets=_load(PRESETS)['presets']; types={x['asset_type']:x for x in _load(ASSET_TYPES)['asset_types']}
    candidates=[]
    demand=_norm_score(seed.get('demand_score'))
    # Champion exploitation candidate remains available from Object Atlas validation even if Human Atlas has no matching context.
    baseline_presets=[p for p in presets if p['asset_type']=='ISOLATED_OBJECT' and p['activation']=='BASELINE_COMPATIBILITY_ONLY']
    if seed.get('demand_status') in {'validated_high','validated_medium'}:
        for p in baseline_presets:
            score=0.25*demand+0.20+0.10*_preset_rank(p)+0.10+0.10+0.10
            candidates.append({'candidate_id':f"OPP-{seed['id']}-ISOLATED_OBJECT-{p['preset_id']}",'semantic_mode':'ISOLATED_OBJECT','producer_class':'RASTER_GENERATIVE','preset_id':p['preset_id'],'preset_revision':p['revision'],'candidate_lane':'EXPLOITATION','state':'ELIGIBLE_BASELINE','score':round(score,6),'score_components':{'object_demand':round(0.25*demand,6),'human_context':0.0,'commercial_utility':0.20,'platform_fit':0.10,'feasibility':0.10,'differentiation':0.10,'preset_readiness':round(0.10*_preset_rank(p),6)},'evidence':[{'kind':'OBJECT_ATLAS_VALIDATED_BASELINE','ref':str(seed['id']),'claim':'Object Atlas validates the primitive for current isolated-object champion exploitation only; no alternate mode demand is inherited.'},{'kind':'PRESET_EVIDENCE','ref':p['preset_id'],'claim':p['evidence']['basis']}],'production_authorized':False})
    # Human-context-backed exploration candidates. A context is a hypothesis unless its evidence label says otherwise.
    for ctx in bridge_result.get('candidates',[]):
        text=_context_text(ctx); coherence=_norm_score(ctx.get('coherence_score'))
        for mode,cfg in signals['modes'].items():
            terms=_hits(text,cfg['signal_terms'])
            if len(terms)<int(cfg['minimum_signal_hits']):continue
            producer=cfg['producer_class']; maturity=types[mode]['maturity']['state']; engine=_engine_state(mode,producer)
            mode_presets=[p for p in presets if p['asset_type']==mode]
            rows=mode_presets or [None]
            for pr in rows:
                preset_ready=_preset_rank(pr) if pr else 0.0
                feasibility=1.0 if engine=='ACCEPTED' else (0.55 if engine=='UNAVAILABLE_NOT_ACCEPTED' else 0.35)
                utility=min(1.0,0.45+0.08*len(terms)); platform=0.65; differentiation=0.60 if mode!='ISOLATED_OBJECT' else 0.50
                score=0.25*demand+0.25*coherence+0.20*utility+0.10*platform+0.10*feasibility+0.05*differentiation+0.05*preset_ready
                if pr and pr['activation']=='BASELINE_COMPATIBILITY_ONLY' and mode=='ISOLATED_OBJECT': lane='EXPLOITATION'
                else: lane='EXPLORATION'
                state='RESEARCH_NO_GOVERNED_PRESET' if pr is None else ('ELIGIBLE_EXPLORATION' if pr['activation']!='NOT_LIVE' and engine=='ACCEPTED' else 'RESEARCH_ONLY')
                candidates.append({'candidate_id':f"OPP-{seed['id']}-{mode}-{pr['preset_id'] if pr else 'NO_PRESET'}-{ctx.get('context_id','CTX')}",'semantic_mode':mode,'producer_class':producer,'preset_id':pr['preset_id'] if pr else None,'preset_revision':pr['revision'] if pr else None,'candidate_lane':lane,'state':state,'score':round(score,6),'score_components':{'object_demand':round(0.25*demand,6),'human_context':round(0.25*coherence,6),'commercial_utility':round(0.20*utility,6),'platform_fit':round(0.10*platform,6),'feasibility':round(0.10*feasibility,6),'differentiation':round(0.05*differentiation,6),'preset_readiness':round(0.05*preset_ready,6)},'context_id':ctx.get('context_id'),'signal_terms':terms,'engine_state':engine,'asset_type_maturity':maturity,'evidence':[{'kind':'HUMAN_CONTEXT_INFERENCE','ref':ctx.get('context_id'),'label':ctx.get('evidence_label','UNKNOWN'),'claim':'Mode relevance is inferred from bounded context terms; it is not observed market demand.'},{'kind':'OBJECT_ATLAS_SEED','ref':str(seed['id']),'claim':'Seed demand evidence does not automatically transfer to this semantic mode.'}]+([{'kind':'PRESET_EVIDENCE','ref':pr['preset_id'],'claim':pr['evidence']['basis']}] if pr else []),'production_authorized':False})
    # Deduplicate candidate IDs by best score and impose sparse bound.
    best={}
    for c in candidates:
        old=best.get(c['candidate_id'])
        if old is None or c['score']>old['score']:best[c['candidate_id']]=c
    ranked=sorted(best.values(),key=lambda x:(-x['score'],x['candidate_id']))[:limit]
    return {'schema':'die.factory-asset.seed-mode-preset-opportunity-plan.v1','seed':{'seed_id':seed['id'],'noun':seed['canonical_name'],'demand_status':seed['demand_status'],'demand_score':seed['demand_score']},'selection_policy':'SPARSE_EVIDENCE_BOUNDED_V1','force_all_modes':False,'cartesian_enumeration':False,'candidate_count':len(ranked),'candidates':ranked,'authority':{'effect':'NONE','production_authorized':False,'provider_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False}}
