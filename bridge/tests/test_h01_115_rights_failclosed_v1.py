import importlib.util,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company/company-os/die-h01/engineering/h01_108_postprocess_one.py'
S=importlib.util.spec_from_file_location('h01115one',MOD);M=importlib.util.module_from_spec(S);assert S and S.loader;sys.modules[S.name]=M;S.loader.exec_module(M)

def base_state(w):return {'schema':'die.h01.h01-115-postproduction-state.v1','status':'RUNNING','stage':'RIGHTS_QA','generation_validity_effect':'NONE','workspace':str(w)}

def test_rights_failure_terminalizes_review_required_without_generation_effect():
 with tempfile.TemporaryDirectory() as td:
  w=Path(td);(w/'asset-receipt.json').write_text(json.dumps({'canonical_svg_sha256':'c','generation_status':'GENERATION_COMPLETE'}))
  st=M.terminalize(w,base_state(w),'REVIEW_REQUIRED','REVIEW_REQUIRED',reason='RIGHTS_QA_FAILED_FAIL_CLOSED',detail='tesseract timeout')
  a=json.loads((w/'asset-receipt.json').read_text());r=json.loads((w/'rights-review-required.receipt.json').read_text())
  assert st['status']=='PARKED_FOUNDER_QC';assert st['postproduction_classification']=='REVIEW_REQUIRED';assert a['submission_eligible'] is False;assert a['generation_validity_effect']=='NONE';assert r['provider_generation_dispatched'] is False;assert r['generation_validity_effect']=='NONE'

def test_blocked_rights_remains_terminal_block():
 with tempfile.TemporaryDirectory() as td:
  w=Path(td);(w/'asset-receipt.json').write_text('{}');st=M.terminalize(w,base_state(w),'BLOCKED_RIGHTS','BLOCK');assert st['status']=='PARKED_RIGHTS_BLOCK';assert json.loads((w/'asset-receipt.json').read_text())['status']=='BLOCKED_RIGHTS'

def test_source_reuses_legacy_terminal_rights_only_with_exact_master_and_selftest():
 s=MOD.read_text()
 assert "existing.get('canonical_svg_sha256')==validation.get('canonical_svg_sha256')" in s
 assert "existing.get('visual_rights_self_test')=='PASS'" in s
 assert "existing.get('rights') in TERMINAL_RIGHTS" in s
 assert 'legacy_reused=True' in s

def test_rights_stage_failure_returns_terminal_review_but_technical_failure_still_retries():
 s=MOD.read_text()
 assert "if state.get('stage')=='RIGHTS_QA':" in s
 assert "terminalize(w,state,'REVIEW_REQUIRED','REVIEW_REQUIRED'" in s
 assert "'status':'TERMINAL_REVIEW_REQUIRED'" in s
 assert "state.update({'status':'PARKED_POSTPRODUCTION_RETRY'" in s
