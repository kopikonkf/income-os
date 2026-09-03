from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

class CapacityError(ValueError):
    def __init__(self, code:str, message:str): super().__init__(f"{code}: {message}"); self.code=code

EVENT_TO_STATE={
    'SUCCESS':'AVAILABLE',
    'RATE_LIMITED':'CONSTRAINED',
    'CAPACITY_UNAVAILABLE':'UNAVAILABLE',
    'AUTH_REQUIRED':'UNAVAILABLE',
    'PROTECTION_CHALLENGE':'UNAVAILABLE',
    'PROVIDER_ERROR':'CONSTRAINED',
}
ALLOWED_KEYS={'profile_id','provider_id','event','observed_at','evidence_ref','retry_after_seconds'}
FORBIDDEN_GUESS_KEYS={'quota','quota_remaining','requests_remaining','daily_limit','estimated_limit','guessed_capacity','guessed_quota'}

def _parse(ts:str)->datetime:
    try:
        value=datetime.fromisoformat(ts.replace('Z','+00:00'))
    except Exception as exc: raise CapacityError('INVALID_OBSERVED_AT',ts) from exc
    if value.tzinfo is None: raise CapacityError('INVALID_OBSERVED_AT','timezone required')
    return value.astimezone(timezone.utc)

@dataclass(frozen=True)
class CapacitySnapshot:
    profile_id:str; provider_id:str; state:str; observed_at:str|None; evidence_ref:str|None; retry_after_seconds:int|None; stale:bool
    def as_dict(self): return self.__dict__.copy()

class CapacityLedger:
    def __init__(self): self._events:dict[str,list[dict[str,Any]]]={}
    def record(self,event:dict[str,Any])->None:
        keys=set(event)
        if keys & FORBIDDEN_GUESS_KEYS: raise CapacityError('GUESSED_QUOTA_FORBIDDEN',','.join(sorted(keys&FORBIDDEN_GUESS_KEYS)))
        if keys-ALLOWED_KEYS: raise CapacityError('UNKNOWN_CAPACITY_FIELD',','.join(sorted(keys-ALLOWED_KEYS)))
        for key in ('profile_id','provider_id','event','observed_at','evidence_ref'):
            if not event.get(key): raise CapacityError('CAPACITY_EVIDENCE_INCOMPLETE',key)
        if event['event'] not in EVENT_TO_STATE: raise CapacityError('CAPACITY_EVENT_UNKNOWN',str(event['event']))
        _parse(str(event['observed_at']))
        retry=event.get('retry_after_seconds')
        if retry is not None and (not isinstance(retry,int) or isinstance(retry,bool) or retry<0): raise CapacityError('INVALID_RETRY_AFTER',str(retry))
        self._events.setdefault(str(event['profile_id']),[]).append(dict(event))
        self._events[str(event['profile_id'])].sort(key=lambda x:_parse(str(x['observed_at'])))
    def snapshot(self,profile_id:str,*,now:str,max_age_seconds:int=21600)->CapacitySnapshot:
        events=self._events.get(profile_id,[])
        if not events: return CapacitySnapshot(profile_id,'UNKNOWN','UNKNOWN',None,None,None,True)
        latest=events[-1]; age=(_parse(now)-_parse(str(latest['observed_at']))).total_seconds()
        if age<0: raise CapacityError('FUTURE_EVIDENCE_FORBIDDEN',str(latest['observed_at']))
        stale=age>max_age_seconds
        return CapacitySnapshot(profile_id,str(latest['provider_id']),'UNKNOWN' if stale else EVENT_TO_STATE[str(latest['event'])],str(latest['observed_at']),str(latest['evidence_ref']),latest.get('retry_after_seconds'),stale)
    def history(self,profile_id:str)->list[dict[str,Any]]: return [dict(x) for x in self._events.get(profile_id,[])]