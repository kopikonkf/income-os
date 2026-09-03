import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('router',R/'company/factory-asset/lib/provider_router.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def c(profile,provider,**kw):
 x={'profile_id':profile,'provider_id':provider,'enabled':True,'policy_allowed':True,'capacity_state':'AVAILABLE','asset_types':['PHOTO','ISOLATED_OBJECT'],'quality_score':0.9,'unit_cost_micros':0,'priority':10};x.update(kw);return x
def test_deterministic_quality_then_cost_then_priority_then_id():
 rows=[c('qwen_b','qwen',quality_score=.8),c('qwen_a','qwen',quality_score=.9,unit_cost_micros=5),c('chatgpt_a','chatgpt',quality_score=.9,unit_cost_micros=0,priority=20)]
 d=m.route_provider(asset_type='PHOTO',candidates=rows);assert d.profile_id=='chatgpt_a'
def test_policy_capacity_and_capability_are_hard_gates():
 rows=[c('a','qwen',policy_allowed=False),c('b','chatgpt',capacity_state='CONSTRAINED'),c('c','gemini',asset_types=['ICON'])]
 with pytest.raises(m.RoutingBlocked) as e:m.route_provider(asset_type='PHOTO',candidates=rows)
 assert {r for x in e.value.reasons for r in x['reasons']}=={'POLICY_BLOCKED','CAPACITY_NOT_AVAILABLE','CAPABILITY_MISMATCH'}
def test_unknown_capacity_never_routes():
 with pytest.raises(m.RoutingBlocked):m.route_provider(asset_type='PHOTO',candidates=[c('a','qwen',capacity_state='UNKNOWN')])
def test_explanation_contains_rejections():
 d=m.route_provider(asset_type='PHOTO',candidates=[c('blocked','grok',policy_allowed=False),c('ok','qwen')]);assert d.profile_id=='ok';assert d.rejected[0]['profile_id']=='blocked'
def test_no_guessed_quota_input_is_needed():
 d=m.route_provider(asset_type='PHOTO',candidates=[c('ok','qwen')]);assert 'qwen'==d.provider_id