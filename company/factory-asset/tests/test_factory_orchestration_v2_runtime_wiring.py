from pathlib import Path
R=Path(__file__).resolve().parents[3]
def test_live_runtime_uses_factory_v2_and_no_longer_hardcodes_asset_png():
 src=(R/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text();assert 'factory_orchestration_v2 as factory_v2' in src;assert 'postprocess_raster_workspace' in src;assert "out=final/'asset.png'" not in src;assert "('asset'+src.suffix.lower())" not in src
def test_active_resolver_recognizes_all_v2_postproduction_states():
 src=(R/'company/die-agents/hermes/production_active_card_resolver.py').read_text()
 for state in ('MASTER_VALIDATED','UPSCALE_DECIDED','DERIVATIVES_READY','TECHNICAL_QA_PASS','RIGHTS_SIGNAL_PASS_OR_REVIEW','METADATA_READY','PACKAGE_READY'):assert f'"{state}"' in src
def test_metadata_engine_emits_listing_and_submission_fields():
 src=(R/'company/factory-asset/lib/package_readiness.py').read_text();assert "'listing_filename':listing_filename" in src;assert "'submission_fields'" in src;assert "binary_injected=provenance.get('binary_metadata_injected',False)" in src;assert "'binary_metadata_injected':binary_injected" in src

def test_success_notification_surface_is_founder_simple():
 src=(R/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py').read_text()
 assert "allowed={'PRODUCTION_STARTED','ARTIFACT_CREATED','WAITING_FOUNDER_QC'}" in src
 assert "telegram_event(workspace,'QA_QC_UPDATE'" not in src
 assert "'backend_gate':'RIGHTS_REVIEW_REQUIRED'" in src
 assert "'submission_eligible':False" in src

def test_runtime_externalizes_backend_review_as_founder_qc_park():
 src=(R/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text()
 assert "progress_state='WAITING_FOUNDER_QC'" in src
 assert 'Backend rights/package eligibility remains governed separately' in src


def test_fa141_binary_metadata_is_rehashed_before_package_and_manifest():
 src=(R/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py').read_text()
 assert 'bmeta.inject_or_sidecar' in src
 assert "atomic_json(root/'binary-metadata-receipts.json'" in src
 assert "expected_sha256=br['output_sha256']" in src
 assert "'binary_metadata_injected':meta['binary_metadata_injected']" in src
