from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

SECRET_KEYS={
    'password','credential','credentials','cookie','cookies','session_token','access_token','refresh_token',
    'authorization','auth_header','raw_auth_body','api_key','secret','client_secret','cdp_url','browser_profile'
}

class ObservabilityError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f"{code}: {message}");self.code=code

def _walk(value:Any,path:str='$'):
    if isinstance(value,dict):
        for k,v in value.items():
            yield f'{path}.{k}',str(k).lower(),v
            yield from _walk(v,f'{path}.{k}')
    elif isinstance(value,list):
        for i,v in enumerate(value):
            yield from _walk(v,f'{path}[{i}]')

def assert_secret_free(value:Any)->None:
    for path,key,_ in _walk(value):
        if key in SECRET_KEYS or key.endswith('_token') or key.endswith('_secret'):
            raise ObservabilityError('SECRET_FIELD_FORBIDDEN',path)

def sanitize_event(event:dict[str,Any])->dict[str,Any]:
    assert_secret_free(event)
    allowed={'kind','provider_id','profile_id','job_id','semantic_asset_id','artifact_sha256','state','failure_code','retryable','attempts','retries','bytes','duration_ms','cpu_seconds','memory_mb_seconds','unit_cost_micros','quantity','timestamp','evidence_ref','capacity','policy','routing_reason'}
    unknown=sorted(set(event)-allowed)
    if unknown: raise ObservabilityError('UNKNOWN_OBSERVABILITY_FIELD',','.join(unknown))
    return dict(event)

@dataclass
class MetricsLedger:
    attempts:int=0
    unique_masters:set[str]=field(default_factory=set)
    qa_assets:int=0
    derivatives:int=0
    packages:int=0
    failures:int=0
    resource_cpu_seconds:float=0.0
    resource_memory_mb_seconds:float=0.0
    economics_unit_cost_micros:int=0
    events:list[dict[str,Any]]=field(default_factory=list)

    def record(self,event:dict[str,Any])->None:
        e=sanitize_event(event)
        kind=e.get('kind')
        if kind=='ATTEMPT': self.attempts+=1
        elif kind=='MASTER':
            sha=e.get('artifact_sha256')
            if not isinstance(sha,str) or len(sha)!=64: raise ObservabilityError('MASTER_SHA256_REQUIRED',str(sha))
            self.unique_masters.add(sha)
        elif kind=='QA_ASSET': self.qa_assets+=int(e.get('quantity',1))
        elif kind=='DERIVATIVE': self.derivatives+=int(e.get('quantity',1))
        elif kind=='PACKAGE': self.packages+=int(e.get('quantity',1))
        elif kind=='FAILURE': self.failures+=1
        elif kind=='RESOURCE':
            self.resource_cpu_seconds+=float(e.get('cpu_seconds',0.0)); self.resource_memory_mb_seconds+=float(e.get('memory_mb_seconds',0.0))
        elif kind=='ECONOMICS': self.economics_unit_cost_micros+=int(e.get('unit_cost_micros',0))
        else: raise ObservabilityError('OBSERVABILITY_KIND_UNKNOWN',str(kind))
        self.events.append(e)

    def snapshot(self)->dict[str,Any]:
        return {
            'schema':'die.factory-asset.observability.snapshot.v1',
            'attempts':self.attempts,
            'unique_masters':len(self.unique_masters),
            'qa_assets':self.qa_assets,
            'derivatives':self.derivatives,
            'packages':self.packages,
            'failures':self.failures,
            'resources':{'cpu_seconds':self.resource_cpu_seconds,'memory_mb_seconds':self.resource_memory_mb_seconds},
            'economics':{'unit_cost_micros':self.economics_unit_cost_micros},
            'events':list(self.events),
        }