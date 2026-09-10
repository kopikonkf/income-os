import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COG = ROOT / "company/die-agents/hermes/production-cognition/production_cognition_tick.py"
DISPATCH = ROOT / "company/factory-asset/bin/production_multi_cluster_dispatch.mjs"
ORCH = ROOT / "company/die-agents/hermes/production-runtime/factory_orchestration_v2.py"
RUNTIME = ROOT / "company/die-agents/hermes/production-runtime/production_runtime_tick.py"
POLICY = ROOT / "company/factory-asset/contracts/production-prompt-policy.v1.json"


def test_prompt_policy_preserves_current_baseline_and_blocks_founder_candidate_from_live_default():
    p = json.loads(POLICY.read_text(encoding="utf-8"))
    assert p["new_card_prompt_authority"] == "TYPED_VISUAL_CONTRACT_V1"
    assert p["current_live_compatibility_preset"]["preset_id"] == "ISOLATED_CARTOON_WATERCOLOR_L0"
    assert p["founder_design_candidate"]["preset_id"] == "ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0"
    assert p["founder_design_candidate"]["activation_required_before_default"] == "CANARY_OR_LIVE_ACCEPTANCE"
    assert p["authority"] == {"provider_call_authorized_by_policy": False, "submission_authorized": False, "publication_authorized": False, "scale_authorized": False}


def test_cognition_requires_subject_spec_after_executive_no_veto_before_ready():
    s = COG.read_text(encoding="utf-8")
    assert "state['stage']='NEED_SUBJECT'" in s
    assert "PRODUCTION_SUBJECT_SPEC_AUTHOR" in s
    assert "die.factory-asset.subject-spec.v1" in s
    assert "pregen.write_pre_generation_contract" in s
    assert "PRE_GENERATION_CONTRACT_LOCKED" in s
    assert "provider_prompt_sha256" in s
    assert "subject_receipt_sha256" in s


def test_dispatcher_uses_compiled_prompt_when_pre_generation_lock_exists_and_keeps_legacy_resume_fallback():
    s = DISPATCH.read_text(encoding="utf-8")
    assert "function resolvePromptContract" in s
    assert "TYPED_VISUAL_CONTRACT_V1" in s
    assert "LEGACY_MASTER_PROMPT" in s
    assert "E_PREGEN_HASH_DRIFT" in s
    assert "E_PREGEN_PROMPT_HASH_DRIFT" in s
    assert "compiled.provider_prompt" in s
    assert "provider_prompt_sha256:pc.provider_prompt_sha256" in s
    assert "idempotency_key:shaValue({task_id:task,blueprint_sha256:lock.blueprint_sha256,provider_prompt_sha256:pc.provider_prompt_sha256})" in s


def test_postproduction_reuses_verified_pre_generation_asset_blueprint_instead_of_reprojecting_when_present():
    s = ORCH.read_text(encoding="utf-8")
    assert "def resolve_bridge_artifacts" in s
    assert "pre-generation-lock.json" in s
    assert "pregen.verify_pre_generation_contract" in s
    assert "TYPED_PRE_GENERATION_CONTRACT_ACCEPTED" in s
    assert "bridge=resolve_bridge_artifacts(workspace,legacy,lock)" in s


def test_worker_cannot_rewrite_typed_prompt_authority():
    s = RUNTIME.read_text(encoding="utf-8")
    assert "must not rewrite the locked prompt authority or any factory-v2 pre-generation sidecar" in s
