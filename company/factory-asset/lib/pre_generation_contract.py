from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "company/factory-asset"
POLICY_PATH = BASE / "contracts/production-prompt-policy.v1.json"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_MODULE_LOAD:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prompt_compiler = _load_module("fa318_prompt_compiler", BASE / "lib/production_prompt_compiler.py")
asset_expression = _load_module("fa318_asset_expression", BASE / "lib/asset_expression_plan.py")
blueprint_compiler = _load_module("fa318_blueprint_compiler", BASE / "lib/blueprint_compiler.py")
producer_router = _load_module("fa318_producer_router", BASE / "lib/semantic_producer_router.py")


class PreGenerationContractError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "die.factory-asset.production-prompt-policy.v1":
        raise PreGenerationContractError("PROMPT_POLICY_SCHEMA", str(path))
    return value


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")[:72] or "ASSET"


def _atomic_or_verify(path: Path, value: dict[str, Any]) -> None:
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != value:
            raise PreGenerationContractError("PREGEN_ARTIFACT_DRIFT", path.name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_pre_generation_contract(
    *, legacy_blueprint: dict[str, Any], legacy_blueprint_sha256: str, subject_spec: dict[str, Any],
    preset_id: str | None = None, preset_revision: str | None = None,
    visual_overrides: dict[str, Any] | None = None, policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or load_policy()
    seed = legacy_blueprint["seed"]
    family = legacy_blueprint["family"]
    meta = legacy_blueprint["metadata_direction"]
    if subject_spec.get("seed_id") != seed["id"] or subject_spec.get("canonical_name") != seed["canonical_name"]:
        raise PreGenerationContractError("SUBJECT_SEED_BINDING", seed["id"])
    prompt_compiler.validate_subject_spec(subject_spec)

    selected = policy["current_live_compatibility_preset"]
    preset_id = preset_id or selected["preset_id"]
    preset_revision = preset_revision or selected["revision"]
    preset = prompt_compiler.get_preset(preset_id, preset_revision)
    if preset["activation"] not in set(policy["allowed_default_preset_activations"]):
        raise PreGenerationContractError("PRESET_NOT_DISPATCH_ELIGIBLE", f"{preset_id}:{preset['activation']}")
    if preset["asset_type"] not in {"PHOTO", "ISOLATED_OBJECT"} or preset["media_family"] != "RASTER":
        raise PreGenerationContractError("BASELINE_PRESET_NOT_RASTER", preset_id)

    overrides = copy.deepcopy(policy.get("default_visual_overrides") or {})
    overrides.update(copy.deepcopy(visual_overrides or {}))
    mode = preset["asset_type"]
    sid = "FASA-" + _safe_id(seed["id"] + "_" + mode)
    bid = "FABP-" + _safe_id(seed["id"] + "_" + mode)
    visual = prompt_compiler.resolve_visual_requirements(
        subject_spec=subject_spec, semantic_asset_id=sid, preset_id=preset_id,
        preset_revision=preset_revision, overrides=overrides,
    )
    compiled = prompt_compiler.compile_provider_prompt(subject_spec=subject_spec, visual_spec=visual)

    buyer = str((family.get("buyer_persona") or ["Stock designer"])[0])
    use = str((family.get("use_cases") or ["Reusable stock design composition"])[0])
    product = str(meta.get("title_direction") or f"{seed['canonical_name']} stock asset")
    evidence_id = "subject-contract-" + seed["id"].casefold()
    support = {"seed_noun": seed["canonical_name"], "buyer": buyer, "commercial_use_case": use,
               "product_expression": product, "semantic_mode": mode, "platform_id": "ADOBE_STOCK"}
    plan = {
        "schema": "die.factory-asset.asset-expression-plan.v1",
        "plan_id": "FAEP-" + _safe_id(seed["id"] + "_" + mode),
        "seed": {"seed_id": seed["id"], "noun": seed["canonical_name"]},
        "decision": "SELECT",
        "decision_rationale": "Approved Object Atlas seed plus reviewed family Blueprint and typed subject/preset contract define one bounded baseline expression without claiming external market evidence.",
        "policy": {"expansion_rule": "EVIDENCE_SUPPORTED_ONLY", "force_all_modes": False, "packaging_variants_create_new_semantic_asset": False, "derivative_planning_stage": "AFTER_VALIDATED_MASTER", "submission_authority": "FOUNDER_CONTROLLED"},
        "evidence": [{"evidence_id": evidence_id, "kind": "OBJECT_ATLAS_SEED", "source_ref": "factory-v2/subject-spec.json", "source_sha256": canonical_sha256(subject_spec), "support": support, "rationale": "Object Atlas seed and typed subject contract bind the requested subject; buyer/use statements remain reviewed Object-Atlas-only hypotheses."}],
        "expressions": [{"semantic_asset_id": sid, "buyer": buyer, "commercial_use_case": use, "product_expression": product, "semantic_mode": mode, "producer_class": "RASTER_GENERATIVE", "candidate_marketplace_route": {"platform_id": "ADOBE_STOCK", "listing_use": product, "state": "CANDIDATE_REQUIRES_POLICY_CHECK"}, "evidence_refs": [evidence_id], "selection_rationale": "Single bounded raster expression for the active production card."}],
    }
    asset_expression.validate_asset_expression_plan(plan)
    bp = {
        "schema": "die.factory-asset.asset-blueprint.v2", "blueprint_id": bid,
        "semantic_identity": {"semantic_asset_id": sid, "commercial_use_case": use, "subject": seed["canonical_name"], "intent": "DESIGN_COMPONENT" if mode == "ISOLATED_OBJECT" else "COMMERCIAL_STOCK"},
        "asset_type": mode, "native_representation": "RASTER_PIXELS", "producer_class": "RASTER_GENERATIVE",
        "master_spec": {"format": "PNG", "width_px": 2000, "height_px": 2000, "color_space": "SRGB", "lineage_sha256_required": True},
        "derivatives": [
            {"derivative_id": "ADOBE_JPEG", "purpose": "MARKETPLACE_DELIVERY", "format": "JPEG", "semantic_identity_effect": "NONE"},
            {"derivative_id": "WEB_PREVIEW", "purpose": "PREVIEW", "format": "WEBP", "semantic_identity_effect": "NONE"},
        ],
        "distinctness": {"identity_rule": "DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT", "packaging_variants_create_new_semantic_asset": False, "near_duplicate_action": "QUARANTINE"},
        "rights": {"commercial_use_cleared": True, "trademark_free": True, "recognizable_person_or_property": False, "release_state": "NOT_REQUIRED"},
        "quality": {"magic_mime_match": True, "decode_reopen": True, "lineage_sha256": True, "family_checks": ["RASTER_DIMENSIONS", "ALPHA_POLICY", "COLOR_SPACE"]},
        "policy": {"compatibility_state": "COMPATIBLE", "marketplace_profiles": ["ADOBE_STOCK"], "unknown_policy_action": "BLOCK_SUBMISSION", "submission_authority": "FOUNDER_CONTROLLED"},
    }
    blueprint_compiler.validate_blueprint(bp)
    production_plan = blueprint_compiler.compile_blueprint(bp)
    route = producer_router.route_frozen_expression(plan=plan, semantic_asset_id=sid, blueprint=bp, frozen_blueprint_sha256=producer_router.canonical_sha256(bp))
    lock = {
        "schema": "die.factory-asset.pre-generation-contract-lock.v1", "prompt_authority": policy["new_card_prompt_authority"],
        "legacy_blueprint_id": legacy_blueprint["blueprint_id"], "legacy_blueprint_sha256": legacy_blueprint_sha256,
        "subject_spec_sha256": canonical_sha256(subject_spec), "preset_id": preset_id, "preset_revision": preset_revision,
        "visual_spec_sha256": canonical_sha256(visual), "compiled_provider_prompt_sha256": canonical_sha256(compiled),
        "provider_prompt_sha256": compiled["provider_prompt_sha256"], "asset_expression_plan_sha256": canonical_sha256(plan),
        "asset_blueprint_v2_sha256": canonical_sha256(bp), "production_plan_sha256": canonical_sha256(production_plan),
        "producer_route_sha256": canonical_sha256(route), "authority_effect": "NONE", "provider_call_authorized": False,
        "submission_authorized": False, "publication_authorized": False,
    }
    return {"subject_spec": copy.deepcopy(subject_spec), "visual_spec": visual, "compiled_prompt": compiled,
            "plan": plan, "blueprint": bp, "production_plan": production_plan, "route": route, "lock": lock}


def write_pre_generation_contract(*, workspace: Path, legacy_blueprint: dict[str, Any], legacy_blueprint_sha256: str,
                                  subject_spec: dict[str, Any], preset_id: str | None = None,
                                  preset_revision: str | None = None, visual_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    built = build_pre_generation_contract(legacy_blueprint=legacy_blueprint, legacy_blueprint_sha256=legacy_blueprint_sha256,
                                          subject_spec=subject_spec, preset_id=preset_id, preset_revision=preset_revision,
                                          visual_overrides=visual_overrides)
    root = workspace / "factory-v2"
    for filename, key in [
        ("subject-spec.json", "subject_spec"), ("visual-requirement-spec.json", "visual_spec"),
        ("compiled-provider-prompt.json", "compiled_prompt"), ("asset-expression-plan.json", "plan"),
        ("asset-blueprint-v2.json", "blueprint"), ("production-plan.json", "production_plan"),
        ("producer-route.json", "route"), ("pre-generation-lock.json", "lock")]:
        _atomic_or_verify(root / filename, built[key])
    return {"root": root, **built}


def verify_pre_generation_contract(*, workspace: Path, legacy_blueprint: dict[str, Any], legacy_blueprint_sha256: str) -> dict[str, Any]:
    root = workspace / "factory-v2"
    mapping = {"subject_spec": "subject-spec.json", "visual_spec": "visual-requirement-spec.json",
               "compiled_prompt": "compiled-provider-prompt.json", "plan": "asset-expression-plan.json",
               "blueprint": "asset-blueprint-v2.json", "production_plan": "production-plan.json",
               "route": "producer-route.json", "lock": "pre-generation-lock.json"}
    values: dict[str, Any] = {}
    for key, name in mapping.items():
        path = root / name
        if not path.is_file():
            raise PreGenerationContractError("PREGEN_ARTIFACT_MISSING", name)
        values[key] = json.loads(path.read_text(encoding="utf-8"))
    lock = values["lock"]
    if lock.get("schema") != "die.factory-asset.pre-generation-contract-lock.v1" or lock.get("prompt_authority") != "TYPED_VISUAL_CONTRACT_V1":
        raise PreGenerationContractError("PREGEN_LOCK_INVALID", str(root))
    if lock.get("legacy_blueprint_sha256") != legacy_blueprint_sha256 or lock.get("legacy_blueprint_id") != legacy_blueprint.get("blueprint_id"):
        raise PreGenerationContractError("PREGEN_LEGACY_BINDING", legacy_blueprint.get("blueprint_id", "unknown"))
    checks = {
        "subject_spec_sha256": canonical_sha256(values["subject_spec"]), "visual_spec_sha256": canonical_sha256(values["visual_spec"]),
        "compiled_provider_prompt_sha256": canonical_sha256(values["compiled_prompt"]), "asset_expression_plan_sha256": canonical_sha256(values["plan"]),
        "asset_blueprint_v2_sha256": canonical_sha256(values["blueprint"]), "production_plan_sha256": canonical_sha256(values["production_plan"]),
        "producer_route_sha256": canonical_sha256(values["route"]),
    }
    for field, actual in checks.items():
        if lock.get(field) != actual:
            raise PreGenerationContractError("PREGEN_HASH_DRIFT", field)
    if lock.get("provider_prompt_sha256") != values["compiled_prompt"].get("provider_prompt_sha256"):
        raise PreGenerationContractError("PREGEN_PROMPT_HASH_DRIFT", "provider_prompt_sha256")
    prompt_compiler.validate_compiled_prompt(compiled=values["compiled_prompt"], subject_spec=values["subject_spec"], visual_spec=values["visual_spec"])
    blueprint_compiler.validate_blueprint(values["blueprint"])
    asset_expression.validate_asset_expression_plan(values["plan"])
    producer_router.route_frozen_expression(plan=values["plan"], semantic_asset_id=values["blueprint"]["semantic_identity"]["semantic_asset_id"], blueprint=values["blueprint"], frozen_blueprint_sha256=canonical_sha256(values["blueprint"]))
    return {"root": root, **values}
