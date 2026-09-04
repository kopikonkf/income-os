from pathlib import Path
R=Path(__file__).resolve().parents[3]
def test_live_runtime_uses_factory_v2_and_no_longer_hardcodes_asset_png():
 src=(R/'company/die-agents/hermes/production-runtime/production_runtime_tick.py').read_text();assert 'factory_orchestration_v2 as factory_v2' in src;assert 'postprocess_raster_workspace' in src;assert "out=final/'asset.png'" not in src;assert "('asset'+src.suffix.lower())" not in src
def test_active_resolver_recognizes_all_v2_postproduction_states():
 src=(R/'company/die-agents/hermes/production_active_card_resolver.py').read_text()
 for state in ('MASTER_VALIDATED','UPSCALE_DECIDED','DERIVATIVES_READY','TECHNICAL_QA_PASS','RIGHTS_SIGNAL_PASS_OR_REVIEW','METADATA_READY','PACKAGE_READY'):assert f'"{state}"' in src
def test_metadata_engine_emits_listing_and_submission_fields():
 src=(R/'company/factory-asset/lib/package_readiness.py').read_text();assert "'listing_filename':listing_filename" in src;assert "'submission_fields'" in src;assert "'binary_metadata_injected':False" in src