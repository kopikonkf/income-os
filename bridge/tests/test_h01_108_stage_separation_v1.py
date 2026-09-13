from pathlib import Path
import ast
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'
def test_generation_runner_ends_at_artifact_created_without_postproduction():
 s=(H/'h01_108_run_one.py').read_text()
 assert 'h01_108_capture.py' in s
 assert 'h01_108_finalize.py' not in s
 assert 'run_visual_rights_detector.py' not in s
 assert "'status':'ARTIFACT_CREATED'" in s
 assert "'postproduction_state':'PENDING'" in s
def test_capture_is_generation_boundary_and_writes_browser_terminal():
 s=(H/'h01_108_capture.py').read_text()
 assert "'status':'ARTIFACT_CREATED'" in s
 assert "'production_boundary':'ARTIFACT_CREATED'" in s
 assert "'postproduction_required':True" in s
 assert 'validate_and_normalize' not in s
 assert 'postprocess_vector' not in s
 assert 'run_visual_rights_detector' not in s
def test_postproduction_is_separate_and_parks_retry_instead_of_generation_failure():
 s=(H/'h01_108_postprocess_one.py').read_text()
 assert 'h01_108_finalize.py' in s
 assert 'run_visual_rights_detector.py' in s
 assert "'PARKED_POSTPRODUCTION_RETRY'" in s
 assert 'h01_108_rights_finalize.py' in s
def test_postproduction_queue_continues_across_parked_failures():
 s=(H/'h01_108_postprocess_queue.py').read_text()
 assert "TERMINAL={'PARKED_FOUNDER_QC','PARKED_RIGHTS_BLOCK'}" in s
 assert "status=='PARKED_POSTPRODUCTION_RETRY' and not retry_parked" in s
 assert 'for w in rows:' in s
 assert "ACCEPTED_SEMANTIC_MASTER" in s
def test_generation_cycle_does_not_read_postproduction_status():
 s=(H/'h01_108_generation_cycle.py').read_text()
 assert 'artifact-created.receipt.json' in s
 assert 'postproduction-state.json' not in s
 assert 'asset-receipt.json' not in s
def test_all_new_python_sources_parse():
 for name in ['h01_108_capture.py','h01_108_run_one.py','h01_108_finalize.py','h01_108_postprocess_one.py','h01_108_postprocess_queue.py','h01_108_generation_cycle.py']:
  ast.parse((H/name).read_text())

def test_postproduction_consumes_immutable_provider_original_without_reacquisition():
 s=(H/'h01_108_postprocess_one.py').read_text(); f=(H/'h01_108_finalize.py').read_text()
 assert "kind='PROVIDER_ORIGINAL'" in s
 assert "choices=['TEXT','FILE','PROVIDER_ORIGINAL']" in f
 assert "E_PROVIDER_ORIGINAL_PATH" in f
