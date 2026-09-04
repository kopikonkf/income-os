import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def load(name,rel):
 s=importlib.util.spec_from_file_location(name,R/rel);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load('dash','company/factory-asset/lib/provider_dashboard.py');cap=load('dashcap','company/factory-asset/lib/capacity_ledger.py');pol=load('dashpol','company/factory-asset/lib/policy_gate.py');router=load('dashrouter','company/factory-asset/lib/provider_router.py');obs=load('dashobs','company/factory-asset/lib/observability.py')
REG=json.loads((R/'company/factory-asset/registries/provider-policy.v1.json').read_text());FIX=json.loads((R/'company/factory-asset/fixtures/provider-dashboard/synthetic-observed.v1.json').read_text())
def build():return m.build_provider_dashboard(policy_registry=REG,fixture=FIX,capacity_ledger_cls=cap.CapacityLedger,evaluate_policy=pol.evaluate_policy,route_provider=router.route_provider,observability=obs,today='2026-09-04',now='2026-09-04T03:15:00Z')
def test_dashboard_contains_five_allowed_plus_optional_grok():
 d=build();rows={x['provider_id']:x for x in d['providers']};assert set(rows)=={'qwen','chatgpt','gemini','manus','duckai','grok'};assert all(rows[p]['eligibility']=='ELIGIBLE' for p in ('qwen','chatgpt','gemini','manus','duckai'));assert rows['grok']['eligibility']=='DEFERRED_OPTIONAL'
def test_capacity_and_health_are_evidence_backed_fixture_states():
 d=build();rows={x['provider_id']:x for x in d['providers']};assert d['evidence_mode']=='SYNTHETIC_OBSERVED_FIXTURE';assert rows['gemini']['capacity']=='CONSTRAINED';assert rows['gemini']['health']=='DEGRADED';assert rows['qwen']['capacity']=='AVAILABLE'
def test_router_selects_only_available_policy_allowed_profile():
 d=build();assert d['selected_profile_id']=='qwen_a';rows={x['provider_id']:x for x in d['providers']};assert rows['gemini']['routing_reason'].startswith('REJECTED:CAPACITY_NOT_AVAILABLE');assert 'POLICY_BLOCKED' in rows['grok']['routing_reason']
def test_no_guessed_quota_or_secret_material():
 d=build();assert d['guessed_quota_present'] is False;obs.assert_secret_free(d);text=json.dumps(d).lower();assert 'session_token' not in text and 'cookie' not in text and 'cdp_url' not in text
def test_optional_grok_does_not_block_route():assert build()['selected_profile_id'] is not None