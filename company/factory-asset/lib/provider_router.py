from __future__ import annotations
from dataclasses import dataclass
from typing import Any

class RoutingBlocked(RuntimeError):
    def __init__(self, reasons:list[dict[str,Any]]): super().__init__('NO_ELIGIBLE_PROVIDER'); self.code='NO_ELIGIBLE_PROVIDER'; self.reasons=reasons

@dataclass(frozen=True)
class RouteDecision:
    profile_id:str
    provider_id:str
    reasons:list[str]
    rejected:list[dict[str,Any]]
    def as_dict(self): return {'profile_id':self.profile_id,'provider_id':self.provider_id,'reasons':list(self.reasons),'rejected':[dict(x) for x in self.rejected]}

def route_provider(*,asset_type:str,candidates:list[dict[str,Any]])->RouteDecision:
    accepted=[]; rejected=[]
    for c in candidates:
        reasons=[]
        if not c.get('enabled',True): reasons.append('PROFILE_DISABLED')
        if not c.get('policy_allowed',False): reasons.append('POLICY_BLOCKED')
        if c.get('capacity_state')!='AVAILABLE': reasons.append('CAPACITY_NOT_AVAILABLE')
        if asset_type not in set(c.get('asset_types',[])): reasons.append('CAPABILITY_MISMATCH')
        if reasons:
            rejected.append({'profile_id':c.get('profile_id'),'provider_id':c.get('provider_id'),'reasons':reasons})
            continue
        q=float(c.get('quality_score',0)); cost=int(c.get('unit_cost_micros',0)); priority=int(c.get('priority',1000))
        accepted.append(( -q, cost, priority, str(c.get('profile_id')), c ))
    if not accepted: raise RoutingBlocked(rejected)
    accepted.sort(key=lambda x:x[:4]); c=accepted[0][4]
    return RouteDecision(str(c['profile_id']),str(c['provider_id']),['POLICY_ALLOWED','CAPACITY_AVAILABLE','CAPABILITY_MATCH',f"QUALITY_SCORE={c.get('quality_score',0)}",f"UNIT_COST_MICROS={c.get('unit_cost_micros',0)}"],rejected)