from __future__ import annotations
import datetime as dt,json,urllib.request
from pathlib import Path
from typing import Any

BLOCKING={'AUTH_REQUIRED','CHECKPOINT','UNAVAILABLE'}

def _read(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding='utf-8'))
def _fetch(url:str,timeout:float=2.0)->dict[str,Any]:
    with urllib.request.urlopen(url,timeout=timeout) as r:return json.loads(r.read())
def _now()->str:return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')

def build_cluster_topology(repo_root:Path,*,fetch_json=_fetch,observed_at:str|None=None)->dict[str,Any]:
    reg=_read(Path(repo_root)/'company/factory-asset/registries/web-ai-clusters.v1.json');clusters=[]
    for cfg in reg['clusters']:
        cid=cfg['cluster_id'];base=f"http://127.0.0.1:{int(cfg['broker_control_port'])}"
        try:
            live=fetch_json(base+'/v1/status');snap=live.get('tab_leases') or fetch_json(base+'/v1/leases');reachable=True;err=None
        except Exception as e:
            live={};snap={};reachable=False;err=type(e).__name__
        max_tabs=int(snap.get('max_tabs') or cfg.get('max_tabs') or 0);open_pages=int(snap.get('open_pages') or 0);active=int(snap.get('active_leases') or 0)
        leases=[]
        for x in snap.get('leases') or []:
            leases.append({'provider_id':x.get('provider_id'),'job_id':x.get('job_id'),'state':x.get('state'),'acquired_at':x.get('acquired_at'),'expires_at':x.get('expires_at'),'provider_limit':x.get('provider_limit')})
        states=snap.get('provider_states') or {};providers=[]
        for p in cfg.get('providers') or []:
            pid=p['provider_id'];membership=p.get('membership','UNKNOWN')
            state=states.get(pid)
            if membership!='ACTIVE':state='UNAVAILABLE'
            elif not reachable:state='UNKNOWN'
            else:state=state or 'UNKNOWN'
            jobs=[x for x in leases if x.get('provider_id')==pid]
            providers.append({'provider_id':pid,'membership':membership,'readiness':state,'capacity':'UNAVAILABLE' if state in BLOCKING or state=='UNKNOWN' else ('BUSY' if jobs else ('DEGRADED' if state=='DEGRADED' else 'AVAILABLE')),'preferred_transport':p.get('preferred_transport','UNKNOWN'),'tab_limit':(cfg.get('provider_tab_limits') or {}).get(pid),'active_jobs':jobs,'human_action_required':state in {'AUTH_REQUIRED','CHECKPOINT'},'safe_reason':'HUMAN_AUTH_REPAIR_REQUIRED' if state=='AUTH_REQUIRED' else ('PROVIDER_CHECKPOINT_REVIEW_REQUIRED' if state=='CHECKPOINT' else ('READINESS_DEGRADED' if state=='DEGRADED' else None))})
        broker_state=live.get('state','OFFLINE' if not reachable else 'UNKNOWN')
        clusters.append({'cluster_id':cid,'display_name':cfg.get('display_name',cid),'profile_id':cfg.get('profile_id'),'lifecycle_state':cfg.get('lifecycle_state'),'health':'HEALTHY' if broker_state=='READY' else ('OFFLINE' if not reachable else 'DEGRADED'),'broker_state':broker_state,'profile_owner':{'lock_state':'OWNED' if live.get('browser_owner_pid') else 'UNKNOWN','owner_pid':live.get('browser_owner_pid'),'owner_model':live.get('browser_owner_model') or cfg.get('browser_owner_model'),'browser_service':cfg.get('browser_lifecycle_service'),'broker_service':cfg.get('broker_service')},'tab_occupancy':{'max_tabs':max_tabs,'open_pages':open_pages,'active_leases':active,'free_tab_slots':max(0,max_tabs-open_pages),'max_active_browser_generations':cfg.get('max_active_browser_generations'),'generation_slots_available':max(0,int(cfg.get('max_active_browser_generations') or 0)-active),'reserved_recovery_tabs':cfg.get('reserved_recovery_tabs')},'active_jobs':leases,'provider_sessions':providers,'reachable':reachable,'error_code':err})
    return {'schema':'die.factory-asset.console-cluster-topology.v1','observed_at':observed_at or _now(),'evidence_mode':'LIVE_BROKER_SANITIZED','production_cadence_changed':False,'scale_100_per_day_authorized':False,'provider_calls_performed':False,'browser_owner_actions_performed':False,'clusters':clusters}
