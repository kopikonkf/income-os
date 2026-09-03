from __future__ import annotations
import hashlib,json
from copy import deepcopy
from dataclasses import dataclass,asdict
from typing import Any

class QueueError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(f"{code}: {message}");self.code=code

def _hash(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

TERMINAL={'SUCCEEDED','FAILED','CANCELLED'}
RETRYABLE_CODES={'CAPACITY_UNAVAILABLE','RATE_LIMITED','PROVIDER_TIMEOUT','PROVIDER_ERROR'}

@dataclass
class Job:
    job_id:str; idempotency_key:str; intent_hash:str; intent:dict[str,Any]; state:str='READY'; retries:int=0; attempts:int=0; owner:str|None=None; lease_token:str|None=None; failure_code:str|None=None; artifact_sha256:str|None=None; recovery_count:int=0
    def as_dict(self):return asdict(self)

class FactoryJobQueue:
    def __init__(self):self._jobs:dict[str,Job]={};self._by_key:dict[str,str]={}
    def submit(self,*,job_id:str,idempotency_key:str,intent:dict[str,Any])->Job:
        if not job_id or not idempotency_key:raise QueueError('INVALID_JOB','job_id/idempotency_key required')
        ih=_hash(intent); existing_id=self._by_key.get(idempotency_key)
        if existing_id:
            j=self._jobs[existing_id]
            if j.intent_hash!=ih:raise QueueError('IDEMPOTENCY_CONFLICT',idempotency_key)
            return j
        if job_id in self._jobs:raise QueueError('JOB_ID_CONFLICT',job_id)
        j=Job(job_id,idempotency_key,ih,deepcopy(intent));self._jobs[job_id]=j;self._by_key[idempotency_key]=job_id;return j
    def get(self,job_id:str)->Job:
        if job_id not in self._jobs:raise QueueError('JOB_NOT_FOUND',job_id)
        return self._jobs[job_id]
    def list(self)->list[dict[str,Any]]:return [self._jobs[k].as_dict() for k in sorted(self._jobs)]
    def start(self,job_id:str,*,owner:str,lease_token:str)->Job:
        j=self.get(job_id)
        if j.state=='RUNNING':
            if j.owner==owner and j.lease_token==lease_token:return j
            raise QueueError('DUPLICATE_OWNERSHIP',job_id)
        if j.state not in {'READY'}:raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->RUNNING')
        j.state='RUNNING';j.owner=owner;j.lease_token=lease_token;j.attempts+=1;j.failure_code=None;return j
    def pause(self,job_id:str)->Job:
        j=self.get(job_id)
        if j.state!='RUNNING':raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->PAUSED')
        j.state='PAUSED';j.owner=None;j.lease_token=None;return j
    def resume(self,job_id:str)->Job:
        j=self.get(job_id)
        if j.state!='PAUSED':raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->READY')
        j.state='READY';return j
    def cancel(self,job_id:str)->Job:
        j=self.get(job_id)
        if j.state in TERMINAL:raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->CANCELLED')
        j.state='CANCELLED';j.owner=None;j.lease_token=None;return j
    def fail(self,job_id:str,*,code:str,retryable:bool)->Job:
        j=self.get(job_id)
        if j.state!='RUNNING':raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->FAIL')
        j.owner=None;j.lease_token=None;j.failure_code=code
        eligible=retryable and code in RETRYABLE_CODES and j.retries<2
        j.state='RETRY_WAIT' if eligible else 'FAILED';return j
    def retry(self,job_id:str)->Job:
        j=self.get(job_id)
        if j.state!='RETRY_WAIT':raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->READY')
        if j.retries>=2:raise QueueError('RETRY_LIMIT_EXCEEDED',job_id)
        j.retries+=1;j.state='READY';return j
    def succeed(self,job_id:str,*,artifact_sha256:str)->Job:
        j=self.get(job_id)
        if j.state!='RUNNING':raise QueueError('INVALID_STATE_TRANSITION',f'{j.state}->SUCCEEDED')
        if len(artifact_sha256)!=64 or any(c not in '0123456789abcdef' for c in artifact_sha256):raise QueueError('INVALID_ARTIFACT_SHA256',artifact_sha256)
        j.state='SUCCEEDED';j.artifact_sha256=artifact_sha256;j.owner=None;j.lease_token=None;j.failure_code=None;return j
    def reconcile_after_crash(self)->list[str]:
        recovered=[]
        for j in self._jobs.values():
            if j.state=='RUNNING':
                j.state='READY';j.owner=None;j.lease_token=None;j.recovery_count+=1;recovered.append(j.job_id)
        return sorted(recovered)
    def snapshot(self)->dict[str,Any]:return {'schema':'die.factory-asset.job-queue.snapshot.v1','jobs':[deepcopy(x) for x in self.list()]}
    @classmethod
    def from_snapshot(cls,snapshot:dict[str,Any])->'FactoryJobQueue':
        if snapshot.get('schema')!='die.factory-asset.job-queue.snapshot.v1':raise QueueError('INVALID_SNAPSHOT','schema')
        q=cls()
        for row in snapshot.get('jobs',[]):
            j=Job(**deepcopy(row))
            if j.job_id in q._jobs or j.idempotency_key in q._by_key:raise QueueError('INVALID_SNAPSHOT','duplicate identity')
            if j.state=='SUCCEEDED' and not j.artifact_sha256:raise QueueError('FALSE_SUCCESS_IN_SNAPSHOT',j.job_id)
            q._jobs[j.job_id]=j;q._by_key[j.idempotency_key]=j.job_id
        q.reconcile_after_crash();return q