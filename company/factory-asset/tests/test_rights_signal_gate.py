import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('rsg',R/'company/factory-asset/lib/rights_signal_gate.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();FIX=json.loads((R/'company/factory-asset/fixtures/rights-signal-gate/cases.v1.json').read_text())
@pytest.mark.parametrize('case',FIX['cases'],ids=lambda c:c['name'])
def test_rights_signal_cases(case):
 r=m.evaluate_rights_signals(master_path=R/case['master'],expected_sha256=FIX['master_sha256'],observation=case['observation']);assert r['result']==case['expected'];assert r['master_sha256']==FIX['master_sha256'];assert r['human_rights_clearance'] is False;assert r['founder_qc_required'] is True;assert r['submission_eligible'] is False;assert r['submission_authority']=='FOUNDER_CONTROLLED'
def test_clean_pass_is_only_signal_gate_pass_not_human_clearance():
 c=FIX['cases'][0];r=m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256=FIX['master_sha256'],observation=c['observation']);assert r['result']=='PASS';assert r['signal_gate_pass'] is True;assert r['human_rights_clearance'] is False;assert not r['qa_defects']
def test_stock_watermark_text_blocks_with_taxonomy_defect():
 c=next(x for x in FIX['cases'] if x['name']=='stock-watermark-text');r=m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256=FIX['master_sha256'],observation=c['observation']);assert r['result']=='BLOCK';assert 'WATERMARK_PRESENT' in r['qa_defects']
def test_confirmed_trademark_and_brand_logo_block_rights():
 for name in ('confirmed-trademark','confirmed-brand-logo'):
  c=next(x for x in FIX['cases'] if x['name']==name);r=m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256=FIX['master_sha256'],observation=c['observation']);assert r['result']=='BLOCK';assert 'RIGHTS_FAILED' in r['qa_defects']
def test_unresolved_text_logo_candidate_and_incomplete_detector_require_review():
 for name in ('unresolved-text','logo-candidate','text-detector-unavailable','watermark-unclear'):
  c=next(x for x in FIX['cases'] if x['name']==name);r=m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256=FIX['master_sha256'],observation=c['observation']);assert r['result']=='REVIEW_REQUIRED';assert r['signal_gate_pass'] is False
def test_hash_mismatch_fails_before_signal_evaluation():
 c=FIX['cases'][0]
 with pytest.raises(m.RightsSignalError) as e:m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256='0'*64,observation=c['observation'])
 assert e.value.code=='MASTER_HASH_MISMATCH'
def test_observation_bound_to_wrong_master_hash_rejected():
 c=json.loads(json.dumps(FIX['cases'][0]));c['observation']['master_sha256']='0'*64
 with pytest.raises(m.RightsSignalError) as e:m.evaluate_rights_signals(master_path=R/c['master'],expected_sha256=FIX['master_sha256'],observation=c['observation'])
 assert e.value.code=='OBSERVATION_MASTER_HASH_MISMATCH'
def test_default_policy_never_grants_human_clearance():
 p=m.load_policy();assert p['invariants']['human_rights_clearance_granted'] is False;assert p['invariants']['uncertainty_action']=='REVIEW_REQUIRED';assert p['invariants']['submission_authority']=='FOUNDER_CONTROLLED'