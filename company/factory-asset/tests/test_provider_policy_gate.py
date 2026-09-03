import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('pg',R/'company/factory-asset/lib/policy_gate.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);D=json.loads((R/'company/factory-asset/registries/provider-policy.v1.json').read_text());P={x['provider_id']:x for x in D['profiles']}
def test_current_proven_pool_allowed_by_dated_route_evidence():
 for provider in ('qwen','chatgpt','gemini','manus','duckai'):
  r=m.evaluate_policy(P[provider],today='2026-09-03');assert r['allowed'] and r['code']=='ALLOWED_EVIDENCED'
def test_grok_deferred_gate_blocks_without_bypass():
 r=m.evaluate_policy(P['grok'],today='2026-09-03');assert not r['allowed'] and r['code']=='DEFERRED_PLATFORM_GATE'
def test_stale_evidence_blocks():
 x=dict(P['qwen']);x['evidence_date']='2026-01-01';r=m.evaluate_policy(x,today='2026-09-03');assert not r['allowed'] and r['code']=='STALE_POLICY_EVIDENCE'
def test_unknown_automation_route_blocks():
 x=dict(P['qwen']);x['automation_route']='UNKNOWN';r=m.evaluate_policy(x,today='2026-09-03');assert not r['allowed'] and r['code']=='AUTOMATION_ROUTE_BLOCKED'
def test_missing_evidence_blocks():
 x=dict(P['qwen']);x.pop('evidence_ref');r=m.evaluate_policy(x,today='2026-09-03');assert not r['allowed'] and r['code']=='POLICY_EVIDENCE_INCOMPLETE'