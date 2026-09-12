from __future__ import annotations

import json, os, tempfile, time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from architect_browser_dispatcher import BrowserBinding, DispatchError, DispatchRequest, NodeCdpSession, ProfileLease, build_bootstrap

SCHEMA='die.h01.architect-worker-completion.v1'
SUCCESS_TERMINAL={'DONE','VERIFYING'}
FAILURE_TERMINAL={'BLOCKED','READY','FAILED','CANCELLED'}
ACTIVE={'LEASED','RUNNING'}
FORBIDDEN_RESULT_KEYS={'mission_lease_token','leasetoken','review_token','reviewtoken','access_token','refresh_token','authorization','cookie','cookies','credential','credentials','session_bytes'}

class CompletionError(RuntimeError):
    def __init__(self, code:str, detail:str=''):
        super().__init__(f'{code}:{detail}' if detail else code); self.code=code

def _parse_time(value:Any)->float|None:
    if not value: return None
    try: return datetime.fromisoformat(str(value).replace('Z','+00:00')).timestamp()
    except Exception: return None

def _owned_checkpoints(task:dict[str,Any], principal_id:str)->list[dict[str,Any]]:
    rows=[c for c in (task.get('checkpoints') or []) if c.get('principal_id')==principal_id]
    return sorted(rows,key=lambda c:(int(c.get('id') or 0),str(c.get('created_at') or '')))

def _attempt_for_dispatch(task:dict[str,Any], req:DispatchRequest)->dict[str,Any]|None:
    attempts=task.get('owner_attempts') or []
    matches=[a for a in attempts if a.get('dispatch_id')==req.dispatch_id]
    if len(matches)>1: raise CompletionError('E_DUPLICATE_DISPATCH_ATTEMPT',req.dispatch_id)
    if matches:
        if matches[0].get('owner_principal_id')!=req.principal_id: raise CompletionError('E_ATTEMPT_PRINCIPAL_MISMATCH')
        return matches[0]
    if attempts: raise CompletionError('E_STALE_DISPATCH',req.dispatch_id)
    return None

def _validate_identity(task:dict[str,Any], req:DispatchRequest)->dict[str,Any]|None:
    if task.get('id')!=req.task_id: raise CompletionError('E_TASK_ID_MISMATCH')
    if task.get('owner_principal_id') not in (None,req.principal_id): raise CompletionError('E_OWNER_PRINCIPAL_MISMATCH')
    return _attempt_for_dispatch(task,req)

def marker_correlation(observation:dict[str,Any]|None, req:DispatchRequest)->str:
    if not observation: return 'UNOBSERVED'
    if observation.get('marker_found'): return 'MATCH'
    if observation.get('marker_candidates'): return 'FOREIGN_MARKER'
    return 'MISSING'

def _terminal_checkpoint(task:dict[str,Any], req:DispatchRequest)->dict[str,Any]:
    finals=[c for c in _owned_checkpoints(task,req.principal_id) if int(c.get('progress') or -1)==100]
    if not finals: raise CompletionError('E_DURABLE_RESULT_MISSING')
    final=finals[-1]; payload=final.get('payload') or {}
    if not isinstance(payload,dict) or 'result' not in payload or 'artifacts' not in payload: raise CompletionError('E_DURABLE_RESULT_PAYLOAD')
    return final

def ingest_terminal_result(task:dict[str,Any], req:DispatchRequest, observation:dict[str,Any]|None=None)->dict[str,Any]:
    attempt=_validate_identity(task,req); status=str(task.get('status') or ''); correlation=marker_correlation(observation,req)
    if status in SUCCESS_TERMINAL:
        if task.get('lease'): raise CompletionError('E_TERMINAL_LEASE_STILL_PRESENT',status)
        final=_terminal_checkpoint(task,req); payload=final.get('payload') or {}
        return {'schema':SCHEMA,'classification':'SUCCESS' if status=='DONE' else 'REVIEW_PENDING','task_id':req.task_id,'principal_id':req.principal_id,'dispatch_id':req.dispatch_id,'durable_status':status,'terminal_checkpoint_id':final.get('id'),'summary':final.get('summary') or '','result':payload.get('result'),'artifacts':payload.get('artifacts') or [],'marker_correlation':correlation,'attempt_no':attempt.get('attempt_no') if attempt else None,'completion_authority':'MISSION_CONTROL_DURABLE_STATE'}
    if status in FAILURE_TERMINAL:
        if task.get('lease'): raise CompletionError('E_TERMINAL_LEASE_STILL_PRESENT',status)
        mapping={'BLOCKED':'BLOCKED','READY':'REQUEUED','FAILED':'FAILED','CANCELLED':'CANCELLED'}
        return {'schema':SCHEMA,'classification':mapping[status],'task_id':req.task_id,'principal_id':req.principal_id,'dispatch_id':req.dispatch_id,'durable_status':status,'blocked_reason':task.get('blocked_reason'),'marker_correlation':correlation,'attempt_no':attempt.get('attempt_no') if attempt else None,'completion_authority':'MISSION_CONTROL_DURABLE_STATE'}
    raise CompletionError('E_NOT_TERMINAL',status)

def _sanitize_for_persistence(value:Any)->Any:
    if isinstance(value,dict):
        out={}
        for key,item in value.items():
            if str(key).lower() in FORBIDDEN_RESULT_KEYS: raise CompletionError('E_RESULT_SECRET_FIELD',str(key))
            out[str(key)]=_sanitize_for_persistence(item)
        return out
    if isinstance(value,list): return [_sanitize_for_persistence(x) for x in value]
    return value

class ResultJournal:
    """Idempotent local ingestion cache. Mission Control remains durable authority."""
    def __init__(self, root:str|Path): self.root=Path(root)
    def commit(self, record:dict[str,Any])->tuple[str,Path]:
        safe=_sanitize_for_persistence(record); dispatch_id=str(safe.get('dispatch_id') or '')
        if not dispatch_id: raise CompletionError('E_RESULT_DISPATCH_ID')
        self.root.mkdir(parents=True,exist_ok=True); path=self.root/f'{dispatch_id}.json'
        data=(json.dumps(safe,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
        if path.exists():
            if path.read_bytes()==data: return 'UNCHANGED',path
            raise CompletionError('E_RESULT_INGEST_CONFLICT',dispatch_id)
        fd,tmp=tempfile.mkstemp(prefix=f'.{dispatch_id}.',dir=self.root)
        try:
            with os.fdopen(fd,'wb') as h: h.write(data); h.flush(); os.fsync(h.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        return 'CREATED',path

@dataclass(frozen=True)
class CompletionPolicy:
    poll_seconds:float=2.0
    stall_seconds:float=5400.0
    mission_error_grace_seconds:float=300.0
    marker_reconcile_seconds:float=30.0
    minimum_stall_seconds:float=300.0
    def __post_init__(self)->None:
        if self.poll_seconds<=0: raise CompletionError('E_POLICY_POLL')
        if self.stall_seconds<self.minimum_stall_seconds: raise CompletionError('E_POLICY_STALL_TOO_AGGRESSIVE')
        if self.mission_error_grace_seconds<60: raise CompletionError('E_POLICY_MISSION_GRACE')

class ProgressTracker:
    def __init__(self, started_monotonic:float):
        self.last_progress_monotonic=started_monotonic
        self.last_durable_fingerprint=None
        self.last_ui_fingerprint=None
        self.marker_seen_monotonic=None
    def observe(self, task:dict[str,Any], req:DispatchRequest, observation:dict[str,Any]|None, now_monotonic:float)->bool:
        checkpoints=_owned_checkpoints(task,req.principal_id); last_cp=checkpoints[-1] if checkpoints else {}
        attempt=_attempt_for_dispatch(task,req); lease=task.get('lease') or {}
        durable=(last_cp.get('id'),last_cp.get('progress'),last_cp.get('created_at'),lease.get('heartbeat_at'),lease.get('expires_at'),attempt.get('status') if attempt else None,attempt.get('updated_at') if attempt else None)
        progressed=False
        if durable!=self.last_durable_fingerprint:
            self.last_durable_fingerprint=durable; progressed=True
        if observation and not observation.get('observation_error'):
            ui=(int(observation.get('assistant_nodes') or 0),int(observation.get('assistant_chars') or 0),bool(observation.get('stop_visible')),bool(observation.get('composer_ready')),bool(observation.get('marker_found')))
            if ui!=self.last_ui_fingerprint:
                self.last_ui_fingerprint=ui; progressed=True
            if observation.get('stop_visible'): progressed=True
            if observation.get('marker_found') and self.marker_seen_monotonic is None:
                self.marker_seen_monotonic=now_monotonic; progressed=True
        if progressed: self.last_progress_monotonic=now_monotonic
        return progressed

def evaluate_snapshot(task:dict[str,Any], req:DispatchRequest, observation:dict[str,Any]|None, tracker:ProgressTracker, policy:CompletionPolicy, *, browser_alive:bool, now_monotonic:float, now_epoch:float)->dict[str,Any]:
    attempt=_validate_identity(task,req); status=str(task.get('status') or '')
    if status in SUCCESS_TERMINAL|FAILURE_TERMINAL:
        record=ingest_terminal_result(task,req,observation)
        return {'action':'TERMINAL','reason':record['classification'],'record':record}
    if status not in ACTIVE: return {'action':'RECOVERY_REQUIRED','reason':'UNKNOWN_DURABLE_STATUS','durable_status':status}
    if not browser_alive: return {'action':'RECOVERY_REQUIRED','reason':'BROWSER_EXITED','durable_status':status}
    lease=task.get('lease') or {}
    if not lease: return {'action':'RECOVERY_REQUIRED','reason':'ACTIVE_WITHOUT_LEASE','durable_status':status}
    expires=_parse_time(lease.get('expires_at'))
    if expires is not None and expires<now_epoch: return {'action':'RECOVERY_REQUIRED','reason':'LEASE_EXPIRED','durable_status':status}
    if attempt and attempt.get('ended_at'): return {'action':'RECOVERY_REQUIRED','reason':'OWNER_ATTEMPT_ENDED_WHILE_ACTIVE','durable_status':status}
    if observation and observation.get('auth_required'): return {'action':'RECOVERY_REQUIRED','reason':'AUTH_REQUIRED','durable_status':status}
    tracker.observe(task,req,observation,now_monotonic)
    idle=max(0.0,now_monotonic-tracker.last_progress_monotonic); correlation=marker_correlation(observation,req)
    if correlation=='MATCH' and tracker.marker_seen_monotonic is not None:
        marker_age=now_monotonic-tracker.marker_seen_monotonic
        if marker_age>=policy.marker_reconcile_seconds:
            return {'action':'WAIT','reason':'MARKER_AHEAD_OF_PROTOCOL','idle_seconds':idle,'marker_age_seconds':marker_age}
    if idle>=policy.stall_seconds:
        return {'action':'RECOVERY_REQUIRED','reason':'STALLED_NO_DURABLE_OR_UI_PROGRESS','idle_seconds':idle,'durable_status':status}
    return {'action':'WAIT','reason':'ACTIVE_PROGRESS_AWARE','idle_seconds':idle,'marker_correlation':correlation}

def monitor_worker(req:DispatchRequest, binding:BrowserBinding, mission_get:Callable[[],dict[str,Any]], *, result_journal:ResultJournal|None=None, policy:CompletionPolicy|None=None, session_factory:Callable[[BrowserBinding],Any]=NodeCdpSession, monotonic:Callable[[],float]=time.monotonic, epoch:Callable[[],float]=time.time, sleep:Callable[[float],None]=time.sleep)->dict[str,Any]:
    """Own one browser until durable terminal state or bounded recovery is required."""
    policy=policy or CompletionPolicy(); lease=ProfileLease(binding.lease_root,binding.resource_id)
    session=None; receipt=None; closed=False; released=False; mission_error_since=None
    tracker=ProgressTracker(monotonic())
    lease.acquire(task_id=req.task_id,dispatch_id=req.dispatch_id,principal_id=req.principal_id)
    try:
        session=session_factory(binding); submit=session.open_and_submit(build_bootstrap(req))
        while True:
            now_mono=monotonic(); now_wall=epoch()
            observation=session.poll_observation() if hasattr(session,'poll_observation') else None
            alive=session.is_alive() if hasattr(session,'is_alive') else True
            try:
                raw=mission_get(); task=raw.get('task',raw)
                decision=evaluate_snapshot(task,req,observation,tracker,policy,browser_alive=alive,now_monotonic=now_mono,now_epoch=now_wall)
                mission_error_since=None
            except CompletionError:
                raise
            except Exception as exc:
                if mission_error_since is None: mission_error_since=now_mono
                outage=now_mono-mission_error_since
                if alive and observation and not observation.get('observation_error'):
                    ui=(int(observation.get('assistant_nodes') or 0),int(observation.get('assistant_chars') or 0),bool(observation.get('stop_visible')),bool(observation.get('composer_ready')),bool(observation.get('marker_found')))
                    if ui!=tracker.last_ui_fingerprint or observation.get('stop_visible'):
                        tracker.last_ui_fingerprint=ui; tracker.last_progress_monotonic=now_mono
                idle=max(0.0,now_mono-tracker.last_progress_monotonic)
                if outage<policy.mission_error_grace_seconds or (alive and idle<policy.stall_seconds):
                    sleep(policy.poll_seconds); continue
                decision={'action':'RECOVERY_REQUIRED','reason':'MISSION_OBSERVER_UNAVAILABLE','error':str(exc)[:500],'outage_seconds':outage,'idle_seconds':idle}
            if decision['action']=='WAIT':
                sleep(policy.poll_seconds); continue
            if decision['action']=='TERMINAL':
                record=decision['record']; journal_status=None; journal_path=None
                if result_journal is not None:
                    journal_status,path=result_journal.commit(record); journal_path=str(path)
                receipt={'schema':SCHEMA,'status':'TERMINAL_INGESTED','task_id':req.task_id,'dispatch_id':req.dispatch_id,'browser_resource_id':binding.resource_id,'browser_submit':{k:submit.get(k) for k in ('status','browser_pid','debug_host','debug_port','url')},'result':record,'journal_status':journal_status,'journal_path':journal_path}
                break
            receipt={'schema':SCHEMA,'status':'RECOVERY_REQUIRED','task_id':req.task_id,'dispatch_id':req.dispatch_id,'browser_resource_id':binding.resource_id,'recovery':decision,'completion_inferred':False,'scheduler_action_taken':False}
            break
    finally:
        if session is not None: closed=bool(session.close())
        try:
            lease.release(); released=True
        finally:
            if receipt is not None:
                receipt['browser_closed']=closed; receipt['profile_lease_released']=released
    if receipt is None: raise DispatchError('E_COMPLETION_RECEIPT_MISSING')
    return receipt
