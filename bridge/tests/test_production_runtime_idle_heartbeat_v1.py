from pathlib import Path
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'company/die-agents/hermes/production-runtime/production_runtime_tick.py'


def load_runtime(name='prod_hb001_runtime'):
    sys.path.insert(0,str(RUNTIME.parent))
    spec=importlib.util.spec_from_file_location(name,RUNTIME)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_no_eligible_seed_emits_actionable_idle_heartbeat(monkeypatch):
    rt=load_runtime()
    monkeypatch.setattr(rt,'resolve_active_card',lambda _: {'status':'NO_ACTIVE_CARD','parked_card_count':17})
    monkeypatch.setattr(rt,'start_seed',lambda: {'status':'IDLE','reason':'NO_ELIGIBLE_SEED'})
    out=rt.tick()
    assert out['status']=='IDLE'
    assert out['reason']=='NO_ELIGIBLE_SEED'
    assert out['heartbeat']=='PRODUCTION_RUNTIME_IDLE'
    assert out['parked_card_count']==17
    assert out['provider_call_performed'] is False
    assert out['next_action']=='REPLENISH_APPROVED_U1_VALIDATED_SEED_POOL'
    assert out['observed_at'].endswith('Z')


def test_main_prints_idle_result_instead_of_silencing_cron(tmp_path,monkeypatch,capsys):
    rt=load_runtime('prod_hb001_runtime_main')
    monkeypatch.setattr(rt,'LOCK',tmp_path/'tick.lock')
    monkeypatch.setattr(rt,'tick',lambda: {'status':'IDLE','reason':'NO_ELIGIBLE_SEED','heartbeat':'PRODUCTION_RUNTIME_IDLE','provider_call_performed':False})
    assert rt.main()==0
    payload=json.loads(capsys.readouterr().out.strip())
    assert payload['status']=='IDLE'
    assert payload['heartbeat']=='PRODUCTION_RUNTIME_IDLE'
    assert payload['provider_call_performed'] is False


def test_existing_three_hour_schedule_is_unchanged():
    installer=(ROOT/'company/die-agents/hermes/linux/install-production-cycle-v1.sh').read_text()
    assert "SCHEDULE='0 */3 * * *'" in installer