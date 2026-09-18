from __future__ import annotations
import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py'
spec=importlib.util.spec_from_file_location('fa318_committed_guard',P); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_committed_unresolved_receipt_parks_without_provider_call(tmp_path:Path):
    p=tmp_path/'provider';p.mkdir()
    (p/'multi-cluster-dispatch.receipt.json').write_text(json.dumps({'schema':'die.production.multi-cluster-dispatch.v1','status':'FAILED','dispatch_committed':True,'retry_allowed':False,'provider_id':'duckai','failure_code':'CHECKPOINT'})+'\n')
    out=m.committed_unresolved_state(tmp_path)
    assert out['status']=='IDLE' and out['reason']=='COMMITTED_UNRESOLVED'
    assert out['provider_call_performed'] is False and out['retry_allowed'] is False
    assert out['provider_id']=='duckai' and out['failure_code']=='CHECKPOINT'
    assert out['next_action']=='FOUNDER_RECONCILIATION_REQUIRED_NO_AUTOMATIC_REDISPATCH'

def test_uncommitted_or_success_receipt_does_not_park(tmp_path:Path):
    p=tmp_path/'provider';p.mkdir();f=p/'multi-cluster-dispatch.receipt.json'
    for v in [
        {'status':'FAILED','dispatch_committed':False},
        {'status':'SUCCEEDED','dispatch_committed':True},
    ]:
        f.write_text(json.dumps(v)+'\n'); assert m.committed_unresolved_state(tmp_path) is None
