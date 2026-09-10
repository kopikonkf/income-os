import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
import sys
sys.path.insert(0, str(LIB))

from production_prompt_compiler import (  # noqa: E402
    ProductionPromptError,
    canonical_sha256,
    compile_provider_prompt,
    get_preset,
    load_preset_registry,
    resolve_visual_requirements,
    validate_compiled_prompt,
    validate_preset_registry,
    validate_subject_spec,
    validate_visual_spec,
)

BASE = ROOT / "company/factory-asset"
NASI_SUBJECT = json.loads((BASE / "fixtures/prompt-compiler/nasi-lemak-subject-spec.v1.json").read_text(encoding="utf-8"))
NASI_VISUAL = json.loads((BASE / "fixtures/prompt-compiler/nasi-lemak-visual-spec.v1.json").read_text(encoding="utf-8"))
NASI_COMPILED = json.loads((BASE / "fixtures/prompt-compiler/nasi-lemak-compiled-prompt.v1.json").read_text(encoding="utf-8"))
BOTTLE = json.loads((BASE / "fixtures/prompt-compiler/bottle-subject-spec.v1.json").read_text(encoding="utf-8"))


def test_preset_registry_valid_and_preserves_historical_truth():
    registry = load_preset_registry()
    validate_preset_registry(registry)
    legacy = get_preset("ISOLATED_CARTOON_WATERCOLOR_L0", registry=registry)
    assert legacy["status"] == "HISTORICAL_ACCEPTED"
    assert legacy["activation"] == "BASELINE_COMPATIBILITY_ONLY"
    assert legacy["style"]["family"] == "CARTOON"
    assert legacy["style"]["medium"] == "WATERCOLOR"


def test_source_aligned_candidate_is_not_falsely_labeled_cartoon_or_live():
    candidate = get_preset("ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0")
    assert candidate["status"] == "FOUNDER_DESIGN_CANDIDATE"
    assert candidate["activation"] == "NOT_LIVE"
    assert candidate["style"]["family"] == "ILLUSTRATIVE_CLIPART"
    assert candidate["style"]["variant"] == "PREMIUM_SEMI_REALISTIC_VECTOR_LIKE"
    assert candidate["composition_defaults"]["background_mode"] == "TRANSPARENT"
    assert all("cartoon" not in x.casefold() for x in candidate["prompt_descriptors"])


def test_nasi_subject_and_visual_specs_validate():
    validate_subject_spec(NASI_SUBJECT)
    validate_visual_spec(NASI_VISUAL)
    assert NASI_VISUAL["asset_type"] == "ISOLATED_OBJECT"
    assert len(NASI_VISUAL["subject"]["essential_components"]) == 5
    assert NASI_VISUAL["composition"]["background_mode"] == "TRANSPARENT"
    assert NASI_VISUAL["view"]["instruction"] == "slightly elevated three-quarter angle"


def test_nasi_compilation_is_deterministic_and_matches_acceptance_fixture():
    a = compile_provider_prompt(subject_spec=NASI_SUBJECT, visual_spec=NASI_VISUAL)
    b = compile_provider_prompt(subject_spec=copy.deepcopy(NASI_SUBJECT), visual_spec=copy.deepcopy(NASI_VISUAL))
    assert a == b == NASI_COMPILED
    assert a["provider_prompt_sha256"] == "b644dd32fc40c31e1a07c290c92cf5bf82f3d8b12c64b9d393bce25a0e48a457"
    assert a["compiled_contract_sha256"] == "2d11d24d09d34a3ebda587d5d114a919fad0c6c3b9baea3f070465ac592cd5be"


def test_nasi_compiled_prompt_carries_real_subject_and_art_direction_requirements():
    p = NASI_COMPILED["provider_prompt"].casefold()
    required = [
        "fluffy white steamed coconut rice",
        "banana leaf",
        "white ceramic plate",
        "halved hard-boiled egg",
        "crispy fried anchovies",
        "roasted peanuts",
        "rich red sambal chili paste",
        "thin fresh cucumber slices",
        "clearly separated",
        "slightly elevated three-quarter angle",
        "clean premium digital illustration",
        "semi-realistic vector-like rendering",
        "realistic proportions",
        "detailed textures",
        "vibrant but realistic colors",
        "crisp clean edges",
        "complete subject fully visible with no crop",
        "clean separable silhouette",
        "transparent background with no background elements",
        "reusable standalone stock design component",
        "readable text",
        "logo",
        "trademark",
        "watermark",
    ]
    for term in required:
        assert term in p


def test_resolver_rejects_background_outside_preset_contract():
    with pytest.raises(ProductionPromptError, match="BACKGROUND_NOT_ALLOWED_BY_PRESET"):
        resolve_visual_requirements(
            subject_spec=BOTTLE,
            semantic_asset_id="FASA-BOTTLE_001",
            preset_id="ISOLATED_CARTOON_WATERCOLOR_L0",
            overrides={"background_mode": "TRANSPARENT"},
        )


def test_resolver_requires_custom_view_instruction():
    with pytest.raises(ProductionPromptError, match="CUSTOM_VIEW_INSTRUCTION_REQUIRED"):
        resolve_visual_requirements(
            subject_spec=BOTTLE,
            semantic_asset_id="FASA-BOTTLE_001",
            preset_id="ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0",
            overrides={"viewpoint": "CUSTOM"},
        )


def test_simple_object_can_compile_without_invented_components():
    visual = resolve_visual_requirements(
        subject_spec=BOTTLE,
        semantic_asset_id="FASA-BOTTLE_001",
        preset_id="ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0",
        overrides={"viewpoint": "FRONT"},
    )
    compiled = compile_provider_prompt(subject_spec=BOTTLE, visual_spec=visual)
    assert compiled["required_component_names"] == []
    assert "distinct bottle body, shoulder, neck and opening or closure" in compiled["provider_prompt"]
    assert "front view" in compiled["provider_prompt"]
    assert compiled["subject_spec_sha256"] == canonical_sha256(BOTTLE)


def test_compiled_validator_detects_prompt_tamper():
    bad = copy.deepcopy(NASI_COMPILED)
    bad["provider_prompt"] = bad["provider_prompt"].replace("roasted peanuts", "")
    # Re-hash the prompt to prove the semantic coverage gate catches tampering beyond a simple hash mismatch.
    import hashlib
    bad["provider_prompt_sha256"] = hashlib.sha256(bad["provider_prompt"].encode("utf-8")).hexdigest()
    bad["compiled_contract_sha256"] = canonical_sha256({k: v for k, v in bad.items() if k != "compiled_contract_sha256"})
    with pytest.raises(ProductionPromptError, match="COMPILED_COMPONENT_OMITTED"):
        validate_compiled_prompt(compiled=bad, subject_spec=NASI_SUBJECT, visual_spec=NASI_VISUAL)


def test_visual_contract_has_no_provider_or_publication_authority():
    assert NASI_VISUAL["authority"] == {
        "effect": "NONE",
        "provider_call_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
    }
