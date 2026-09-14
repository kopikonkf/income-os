from pathlib import Path
import ast
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'

def test_generation_runner_requires_technical_finalize_before_success():
 s=(H/'h01_108_run_one.py').read_text()
 assert 'h01_108_capture.py' in s
 assert 'h01_108_technical_finalize.py' in s
 assert s.index('h01_108_capture.py') < s.index('h01_108_technical_finalize.py')
 assert "'status':'GENERATION_COMPLETE'" in s
 assert 'h01_108_finalize.py' not in s
 assert 'run_visual_rights_detector.py' not in s

def test_capture_is_acquisition_boundary_only():
 s=(H/'h01_108_capture.py').read_text()
 assert "'status':'ARTIFACT_CREATED'" in s
 assert "'production_boundary':'ARTIFACT_CREATED'" in s
 assert 'validate_and_normalize' not in s
 assert 'postprocess_vector' not in s
 assert 'run_visual_rights_detector' not in s

def test_technical_finalize_is_generation_terminal_without_postproduction():
 s=(H/'h01_108_technical_finalize.py').read_text()
 assert 'validate_and_normalize' in s
 assert "'status': 'GENERATION_COMPLETE'" in s
 assert "'h01_103_status': 'PASS'" in s
 assert 'postprocess_vector' not in s
 assert 'run_visual_rights_detector' not in s
 assert 'rights_signal' not in s

def test_postproduction_requires_generation_complete_and_never_calls_provider():
 s=(H/'h01_108_postprocess_one.py').read_text();q=(H/'h01_108_postprocess_queue.py').read_text();f=(H/'h01_108_finalize.py').read_text()
 assert "E_GENERATION_COMPLETE_REQUIRED" in s
 assert "generation-complete.receipt.json" in s
 assert 'h01_108_capture.py' not in s
 assert 'h01_108_run_one.py' not in s
 assert 'provider_svg_playwright_strategy' not in s
 assert 'brave_udd_runtime' not in s
 assert "'provider_generation_dispatched':False" in q
 assert "generation_validity_effect':'NONE'" in s
 assert 'validate_and_normalize' not in f
 assert 'generation-complete.receipt.json' in f

def test_postproduction_queue_requires_h01_103_generation_terminal():
 s=(H/'h01_108_postprocess_queue.py').read_text()
 assert "generation-complete.receipt.json" in s
 assert "final/h01-103-validation.json" in s
 assert "MAX_TWO_LOCAL_RETRIES_NO_GENERATION" in s
 assert "PARKED_POSTPRODUCTION_RETRY" in s

def test_generation_cycle_counts_only_generation_complete_h01_103():
 s=(H/'h01_108_generation_cycle.py').read_text()
 start=s.index('def generated(');end=s.index('def next_attempt',start);block=s[start:end]
 assert 'generation-complete.receipt.json' in block
 assert 'h01-103-validation.json' in block
 assert 'artifact-created.receipt.json' not in block
 assert 'browser-job-result.json' not in block
 assert 'postproduction-state.json' not in s
 assert 'asset-receipt.json' not in s

def test_all_generation_and_postproduction_sources_parse():
 for name in ['h01_108_capture.py','h01_108_technical_finalize.py','h01_108_run_one.py','h01_108_finalize.py','h01_108_postprocess_one.py','h01_108_postprocess_queue.py','h01_108_generation_cycle.py','h01_108_seal_generation.py','h01_daily_selector.py']:
  ast.parse((H/name).read_text())
