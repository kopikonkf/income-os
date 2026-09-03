import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('cap',R/'company/factory-asset/lib/capacity_ledger.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def ev(kind,ts='2026-09-03T20:00:00Z',**extra):return {'profile_id':'qwen_a','provider_id':'qwen','event':kind,'observed_at':ts,'evidence_ref':'receipt://test',**extra}
def test_profiles_start_unknown(): assert m.CapacityLedger().snapshot('qwen_a',now='2026-09-03T20:01:00Z').state=='UNKNOWN'
@pytest.mark.parametrize('kind,state',[('SUCCESS','AVAILABLE'),('RATE_LIMITED','CONSTRAINED'),('CAPACITY_UNAVAILABLE','UNAVAILABLE'),('AUTH_REQUIRED','UNAVAILABLE'),('PROTECTION_CHALLENGE','UNAVAILABLE'),('PROVIDER_ERROR','CONSTRAINED')])
def test_observed_events_map_to_state(kind,state):
 l=m.CapacityLedger();l.record(ev(kind));s=l.snapshot('qwen_a',now='2026-09-03T20:05:00Z');assert s.state==state;assert not s.stale
def test_stale_evidence_returns_unknown():
 l=m.CapacityLedger();l.record(ev('SUCCESS','2026-09-03T10:00:00Z'));s=l.snapshot('qwen_a',now='2026-09-03T20:00:00Z');assert s.state=='UNKNOWN' and s.stale
def test_guessed_quotas_forbidden():
 l=m.CapacityLedger();x=ev('SUCCESS');x['quota_remaining']=999
 with pytest.raises(m.CapacityError) as e:l.record(x)
 assert e.value.code=='GUESSED_QUOTA_FORBIDDEN'
def test_latest_dated_evidence_wins_and_history_preserved():
 l=m.CapacityLedger();l.record(ev('RATE_LIMITED','2026-09-03T19:00:00Z',retry_after_seconds=60));l.record(ev('SUCCESS','2026-09-03T19:10:00Z'));assert l.snapshot('qwen_a',now='2026-09-03T19:11:00Z').state=='AVAILABLE';assert len(l.history('qwen_a'))==2