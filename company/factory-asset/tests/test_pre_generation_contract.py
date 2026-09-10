import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MOD = ROOT / "company/factory-asset/lib/pre_generation_contract.py"
spec = importlib.util.spec_from_file_location("fa318_pregen_test", MOD)
m = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(m)


def legacy(prompt="Create an isolated generic trophy on a clean white background with no logos, no trademarks and no watermark."):
    return {
        "schema_version": "die.production.family-blueprint.v1",
        "request_id": "COG-PROD_BP_AUTHOR_TEST_R00",
        "blueprint_id": "BP-PROD-TROPHY_0001",
        "task_id": "PRODSEED000027",
        "mission_id": "M-001",
        "repository_sha": "a" * 40,
        "principal": {"principal_id": "die-lnx-division-001", "role": "AUTHOR"},
        "seed": {"id": "SEED-000027", "canonical_name": "trophy", "object_class": "award", "category_path": "Business/Award", "demand_score": 0.812, "demand_status": "validated_high", "asset_tier": "U1-raster"},
        "family": {"family_id": "FAM-PROD-AWARD_001", "family_thesis": "Commercially useful generic award trophy imagery for business recognition communications.", "buyer_persona": ["business marketer"], "use_cases": ["employee recognition campaign"], "commercial_use_hypothesis": "A generic unbranded trophy can support business award and recognition communication needs.", "evidence_status": "OBJECT_ATLAS_ONLY_HYPOTHESIS"},
        "production": {"asset_type": "RASTER_IMAGE", "batch_size": 1, "engine": "MUXIA/chatgpt-linux-a", "master_prompt": prompt, "negative_constraints": ["no logos", "no trademarks", "no watermark"], "semantic_variation_plan": [{"variation_id": "VAR-USECASE_001", "dimension": "buyer_use_case", "instruction": "Frame for an employee recognition communication use case.", "commercial_rationale": "Tests generic business recognition utility."}]},
        "metadata_direction": {"title_direction": "Generic trophy award for business recognition communication", "primary_keywords": ["trophy award", "business recognition", "achievement"], "category_direction": ["business", "awards"]},
        "qa_requirements": {"required_checks": ["artifact integrity", "technical QA", "visual commercial QC"], "forbidden_elements": ["logos", "trademarks", "watermarks"]},
        "lineage": {"seed_snapshot_sha256": "b" * 64, "source_kind": "OBJECT_ATLAS_SEED", "external_market_evidence_claimed": False},
        "authority": {"effect": "NONE", "existing_production_authority_unchanged": True, "submission_authorized": False, "publication_authorized": False, "spend_authorized": False},
    }


def subject():
    return {
        "schema": "die.factory-asset.subject-spec.v1",
        "subject_spec_id": "FASS-SEED_000027_TROPHY",
        "seed_id": "SEED-000027",
        "canonical_name": "trophy",
        "subject_class": "DECOR",
        "primary_form": "one complete generic award trophy with a stable cup, stem and base silhouette",
        "essential_components": [
            {"name": "trophy cup", "description": "recognizable symmetric award cup", "placement": "above the central stem"},
            {"name": "supporting stem", "description": "simple centered trophy stem", "placement": "between cup and base"},
            {"name": "stable base", "description": "plain unbranded base", "placement": "below the stem"},
        ],
        "recognition_anchors": ["award-trophy cup silhouette", "centered stem and stable base"],
        "natural_attributes": ["generic unbranded award object", "balanced recognizable proportions"],
        "spatial_relationships": ["cup sits above the stem and the stem connects cleanly to the base"],
        "forbidden_subject_mutations": ["do not add readable engraving", "do not add brand marks", "do not crop the trophy"],
        "evidence": {"basis": "OBJECT_ATLAS_PLUS_COGNITION", "refs": ["SEED-000027", "BP-PROD-TROPHY_0001"]},
    }


def test_default_pre_generation_contract_uses_typed_prompt_authority_not_legacy_prose():
    bp = legacy("Legacy prose says put the trophy in an office scene with copy space and dramatic lighting, but this string is no longer prompt authority.")
    built = m.build_pre_generation_contract(legacy_blueprint=bp, legacy_blueprint_sha256=m.canonical_sha256(bp), subject_spec=subject())
    lock = built["lock"]
    prompt = built["compiled_prompt"]["provider_prompt"]
    assert lock["prompt_authority"] == "TYPED_VISUAL_CONTRACT_V1"
    assert lock["preset_id"] == "ISOLATED_CARTOON_WATERCOLOR_L0"
    assert built["blueprint"]["asset_type"] == "ISOLATED_OBJECT"
    assert "trophy cup" in prompt and "supporting stem" in prompt and "stable base" in prompt
    assert "complete subject fully visible with no crop" in prompt
    assert "pure white background" in prompt
    assert "office scene" not in prompt
    assert prompt != bp["production"]["master_prompt"]


def test_founder_design_candidate_cannot_become_default_before_activation():
    bp = legacy()
    with pytest.raises(m.PreGenerationContractError, match="PRESET_NOT_DISPATCH_ELIGIBLE"):
        m.build_pre_generation_contract(
            legacy_blueprint=bp,
            legacy_blueprint_sha256=m.canonical_sha256(bp),
            subject_spec=subject(),
            preset_id="ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0",
            preset_revision="1.0.0",
        )


def test_write_and_verify_pre_generation_contract_is_idempotent(tmp_path):
    bp = legacy()
    h = m.canonical_sha256(bp)
    first = m.write_pre_generation_contract(workspace=tmp_path, legacy_blueprint=bp, legacy_blueprint_sha256=h, subject_spec=subject())
    second = m.write_pre_generation_contract(workspace=tmp_path, legacy_blueprint=bp, legacy_blueprint_sha256=h, subject_spec=subject())
    assert first["lock"] == second["lock"]
    verified = m.verify_pre_generation_contract(workspace=tmp_path, legacy_blueprint=bp, legacy_blueprint_sha256=h)
    assert verified["compiled_prompt"]["provider_prompt_sha256"] == first["compiled_prompt"]["provider_prompt_sha256"]


def test_pre_generation_verifier_fails_on_semantic_sidecar_drift(tmp_path):
    bp = legacy(); h = m.canonical_sha256(bp)
    m.write_pre_generation_contract(workspace=tmp_path, legacy_blueprint=bp, legacy_blueprint_sha256=h, subject_spec=subject())
    p = tmp_path / "factory-v2/subject-spec.json"
    bad = json.loads(p.read_text()); bad["primary_form"] = "tampered subject form"; p.write_text(json.dumps(bad))
    with pytest.raises(m.PreGenerationContractError, match="PREGEN_HASH_DRIFT"):
        m.verify_pre_generation_contract(workspace=tmp_path, legacy_blueprint=bp, legacy_blueprint_sha256=h)


def test_subject_must_bind_exact_seed():
    bp = legacy(); s = subject(); s["canonical_name"] = "medal"
    with pytest.raises(m.PreGenerationContractError, match="SUBJECT_SEED_BINDING"):
        m.build_pre_generation_contract(legacy_blueprint=bp, legacy_blueprint_sha256=m.canonical_sha256(bp), subject_spec=s)
