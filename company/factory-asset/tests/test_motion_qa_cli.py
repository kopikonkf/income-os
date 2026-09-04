import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];p=R/'company/factory-asset/bin/run_motion_qa.py';s=importlib.util.spec_from_file_location('mqa_cli',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_expected_contract_projection_is_exact():
 c=json.loads((R/'company/factory-asset/native-producers/remotion-fixture/src/composition-contract.json').read_text());e=m.expected_from_contract(c);assert e=={'container':'MP4','codec':'H264','pixel_format':'YUV420P','width':1080,'height':1080,'fps':30,'frame_count':180,'duration_seconds':6,'audio_policy':'NONE'}
def test_cli_has_no_provider_or_publication_authority():
 src=p.read_text().lower();
 for marker in ('session_token','cdp_url','marketplace upload','publish(','provider generate'):
  assert marker not in src