import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('mc',R/'company/factory-asset/lib/motion_capability.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m)
CASES=json.loads((R/'company/factory-asset/fixtures/motion-capability/cases.v1.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_motion_cases(case):
 r=m.evaluate_motion_capability(case['candidate']);assert r['result']==case['expected'];assert r['automatic_animation_of_static_asset'] is False;assert r['motion_production_authorized']==(case['expected']=='MOTION_ELIGIBLE')
def test_motion_decision_deterministic():
 c=CASES[0]['candidate'];assert m.evaluate_motion_capability(c)==m.evaluate_motion_capability(c)
def test_unknown_temporal_verb_requires_research_not_guess():
 c=json.loads(json.dumps(CASES[0]['candidate']));c['temporal_verbs']=['teleport'];assert m.evaluate_motion_capability(c)['result']=='RESEARCH'
def test_static_equivalent_blocks_even_with_temporal_verbs():
 c=json.loads(json.dumps(CASES[0]['candidate']));c['static_equivalent_sufficient']=True;assert m.evaluate_motion_capability(c)['result']=='STATIC_ONLY'