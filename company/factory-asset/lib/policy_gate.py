from __future__ import annotations
from datetime import date,datetime
from typing import Any

class PolicyError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f"{code}: {message}");self.code=code

ALLOWED='ALLOWED_EVIDENCED'
BLOCKING={'UNKNOWN','PROHIBITED','DEFERRED_PLATFORM_GATE','AUTH_ROUTE_UNKNOWN','AUTOMATION_ROUTE_UNKNOWN'}

def evaluate_policy(profile:dict[str,Any],*,today:str,max_age_days:int=30)->dict[str,Any]:
    required={'provider_id','profile_id','policy_state','automation_route','auth_route','evidence_date','evidence_ref'}
    missing=sorted(required-set(profile))
    if missing:return {'allowed':False,'code':'POLICY_EVIDENCE_INCOMPLETE','reasons':missing}
    try:
        observed=date.fromisoformat(str(profile['evidence_date'])); now=date.fromisoformat(today)
    except ValueError as exc: raise PolicyError('INVALID_POLICY_DATE','invalid date') from exc
    age=(now-observed).days
    if age<0:return {'allowed':False,'code':'FUTURE_POLICY_EVIDENCE','reasons':[str(profile['evidence_date'])]}
    if age>max_age_days:return {'allowed':False,'code':'STALE_POLICY_EVIDENCE','reasons':[f'age_days={age}']}
    if profile['policy_state']!=ALLOWED:return {'allowed':False,'code':str(profile['policy_state']),'reasons':['policy not allowed']}
    if profile['automation_route'] in ('UNKNOWN','PROHIBITED'):return {'allowed':False,'code':'AUTOMATION_ROUTE_BLOCKED','reasons':[str(profile['automation_route'])]}
    if profile['auth_route'] in ('UNKNOWN','PROHIBITED','PLAN_OR_PLATFORM_GATE'):return {'allowed':False,'code':'AUTH_ROUTE_BLOCKED','reasons':[str(profile['auth_route'])]}
    if not str(profile['evidence_ref']).strip():return {'allowed':False,'code':'POLICY_EVIDENCE_INCOMPLETE','reasons':['evidence_ref']}
    return {'allowed':True,'code':'ALLOWED_EVIDENCED','reasons':[],'evidence_age_days':age,'evidence_ref':profile['evidence_ref']}