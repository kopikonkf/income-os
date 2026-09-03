from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT_SCHEMA_PATH = ROOT / "company/factory-asset/schemas/asset-blueprint-v2.schema.json"
ASSET_TYPE_SCHEMA_PATH = ROOT / "company/factory-asset/schemas/asset-type-registry.schema.json"
ASSET_TYPE_REGISTRY_PATH = ROOT / "company/factory-asset/registries/asset-types.v1.json"
DELIVERY_PROFILE_PATH = ROOT / "company/factory-asset/registries/marketplace-delivery-profiles.v1.json"


class BlueprintCompileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_schema(instance: Any, schema: dict[str, Any], code: str) -> None:
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(x) for x in first.absolute_path) or "$"
        raise BlueprintCompileError(code, f"{path}: {first.message}")


@dataclass(frozen=True)
class CompilerCatalog:
    asset_registry: dict[str, Any]
    delivery_profiles: dict[str, Any]

    @classmethod
    def load_default(cls) -> "CompilerCatalog":
        asset_registry = _load(ASSET_TYPE_REGISTRY_PATH)
        _validate_schema(asset_registry, _load(ASSET_TYPE_SCHEMA_PATH), "ASSET_REGISTRY_SCHEMA_INVALID")
        return cls(asset_registry=asset_registry, delivery_profiles=_load(DELIVERY_PROFILE_PATH))

    @property
    def asset_types(self) -> dict[str, dict[str, Any]]:
        return {row["asset_type"]: row for row in self.asset_registry["asset_types"]}

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return {row["platform_id"]: row for row in self.delivery_profiles["profiles"]}


MASTER_RECIPE = {
    "RASTER_GENERATIVE": "raster-generative-master-v1",
    "NATIVE_VECTOR": "native-vector-master-v1",
    "PROCEDURAL_VECTOR": "procedural-vector-master-v1",
    "MOTION_RENDERER": "motion-render-master-v1",
}

RASTER_RECIPES = {
    "PNG": "raster-png-export-v1",
    "JPEG": "raster-jpeg-stock-v1",
    "WEBP": "raster-webp-preview-v1",
    "TIFF": "raster-tiff-compat-v1",
    "PDF": "raster-pdf-preview-v1",
}
VECTOR_RECIPES = {
    "SVG": "vector-svg-native-v1",
    "EPS": "vector-eps-export-v1",
    "PNG": "vector-png-preview-v1",
    "JPEG": "vector-jpeg-preview-v1",
    "WEBP": "vector-webp-preview-v1",
    "PDF": "vector-pdf-preview-v1",
}
MOTION_RECIPES = {
    "MP4": "motion-mp4-export-v1",
    "MOV": "motion-mov-export-v1",
    "PNG": "motion-png-still-preview-v1",
    "JPEG": "motion-jpeg-still-preview-v1",
    "WEBP": "motion-webp-still-preview-v1",
}


def _canonical_delivery_values(profile: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for entries in profile.get("delivery", {}).values():
        if not isinstance(entries, list):
            continue
        for raw in entries:
            text = str(raw).upper()
            if text in {"JPEG", "JPG"}:
                values.add("JPEG")
            elif text in {"PNG", "TIFF", "SVG", "EPS", "MOV", "MP4"}:
                values.add(text)
            elif text.startswith("MP4/"):
                values.add("MP4")
            elif text.startswith("QUICKTIME MOV"):
                values.add("MOV")
            elif text == "JPEG PREVIEW":
                values.add("JPEG")
    return values


def _recipe_for(native_representation: str, derivative: dict[str, Any]) -> str:
    fmt = derivative["format"]
    purpose = derivative["purpose"]
    if native_representation == "RASTER_PIXELS":
        if fmt in {"SVG", "EPS"}:
            raise BlueprintCompileError("RASTER_TO_VECTOR_FORBIDDEN", f"{fmt} requires a native vector blueprint or a later gated trace task")
        if fmt in {"MP4", "MOV"}:
            raise BlueprintCompileError("RASTER_TO_MOTION_FORBIDDEN", f"{fmt} cannot be compiled from a raster master")
        recipe = RASTER_RECIPES.get(fmt)
    elif native_representation == "VECTOR_PATHS":
        if fmt in {"MP4", "MOV"}:
            raise BlueprintCompileError("VECTOR_TO_MOTION_FORBIDDEN", f"{fmt} cannot be compiled from a vector master")
        recipe = VECTOR_RECIPES.get(fmt)
    elif native_representation == "TIMED_FRAMES":
        if fmt in {"SVG", "EPS", "TIFF", "PDF"}:
            raise BlueprintCompileError("MOTION_DERIVATIVE_FORBIDDEN", f"{fmt} is not a supported motion derivative")
        if fmt in {"PNG", "JPEG", "WEBP"} and purpose not in {"PREVIEW", "THUMBNAIL"}:
            raise BlueprintCompileError("MOTION_STILL_DELIVERY_FORBIDDEN", f"{fmt} from motion is preview-only")
        recipe = MOTION_RECIPES.get(fmt)
    else:
        raise BlueprintCompileError("UNKNOWN_NATIVE_REPRESENTATION", native_representation)
    if recipe is None:
        raise BlueprintCompileError("DERIVATIVE_RECIPE_UNAVAILABLE", f"no deterministic recipe for {native_representation}->{fmt}")
    return recipe


def validate_blueprint(blueprint: dict[str, Any], catalog: CompilerCatalog | None = None) -> None:
    catalog = catalog or CompilerCatalog.load_default()
    _validate_schema(blueprint, _load(BLUEPRINT_SCHEMA_PATH), "BLUEPRINT_SCHEMA_INVALID")

    asset_type = catalog.asset_types.get(blueprint["asset_type"])
    if asset_type is None:
        raise BlueprintCompileError("ASSET_TYPE_UNKNOWN", blueprint["asset_type"])
    if blueprint["native_representation"] != asset_type["native_representation"]:
        raise BlueprintCompileError("NATIVE_REPRESENTATION_MISMATCH", f"{blueprint['asset_type']} requires {asset_type['native_representation']}")
    if blueprint["producer_class"] not in asset_type["producer_classes"]:
        raise BlueprintCompileError("PRODUCER_CLASS_MISMATCH", f"{blueprint['producer_class']} not allowed for {blueprint['asset_type']}")
    if blueprint["master_spec"]["format"] not in asset_type["master_formats"]:
        raise BlueprintCompileError("MASTER_FORMAT_MISMATCH", f"{blueprint['master_spec']['format']} not allowed for {blueprint['asset_type']}")

    required_checks = set(asset_type["quality"]["family_checks"])
    actual_checks = set(blueprint["quality"]["family_checks"])
    if not required_checks.issubset(actual_checks):
        missing = sorted(required_checks - actual_checks)
        raise BlueprintCompileError("QUALITY_CONTRACT_INCOMPLETE", ",".join(missing))

    selected_profiles = []
    for profile_id in blueprint["policy"]["marketplace_profiles"]:
        profile = catalog.profiles.get(profile_id)
        if profile is None:
            raise BlueprintCompileError("MARKETPLACE_PROFILE_UNKNOWN", profile_id)
        selected_profiles.append(profile)

    if blueprint["policy"]["compatibility_state"] == "COMPATIBLE":
        non_pinned = [p["platform_id"] for p in selected_profiles if p["profile_state"] != "EVIDENCE_PINNED"]
        if non_pinned:
            raise BlueprintCompileError("COMPATIBILITY_CLAIM_EXCEEDS_EVIDENCE", ",".join(sorted(non_pinned)))

    for derivative in blueprint["derivatives"]:
        if derivative["format"] not in asset_type["delivery_formats"]:
            raise BlueprintCompileError("DELIVERY_FORMAT_NOT_ALLOWED", f"{blueprint['asset_type']}->{derivative['format']}")
        _recipe_for(blueprint["native_representation"], derivative)
        if derivative["purpose"] == "MARKETPLACE_DELIVERY" and blueprint["policy"]["compatibility_state"] == "COMPATIBLE":
            for profile in selected_profiles:
                supported = _canonical_delivery_values(profile)
                if derivative["format"] not in supported:
                    raise BlueprintCompileError("MARKETPLACE_FORMAT_UNSUPPORTED", f"{profile['platform_id']}:{derivative['format']}")


def compile_blueprint(blueprint: dict[str, Any], catalog: CompilerCatalog | None = None) -> dict[str, Any]:
    catalog = catalog or CompilerCatalog.load_default()
    validate_blueprint(blueprint, catalog)
    asset_type = catalog.asset_types[blueprint["asset_type"]]
    profiles = [catalog.profiles[p] for p in blueprint["policy"]["marketplace_profiles"]]

    derivative_plan = []
    for derivative in blueprint["derivatives"]:
        derivative_plan.append({
            "derivative_id": derivative["derivative_id"],
            "purpose": derivative["purpose"],
            "format": derivative["format"],
            "recipe_id": _recipe_for(blueprint["native_representation"], derivative),
            "semantic_asset_id": blueprint["semantic_identity"]["semantic_asset_id"],
            "semantic_identity_effect": "NONE",
            "marketplace_profiles": sorted(blueprint["policy"]["marketplace_profiles"]) if derivative["purpose"] == "MARKETPLACE_DELIVERY" else [],
        })

    compatibility_unknown = any(p["profile_state"] != "EVIDENCE_PINNED" for p in profiles)
    submission_blocked = blueprint["policy"]["compatibility_state"] != "COMPATIBLE" or compatibility_unknown
    return {
        "schema": "die.factory-asset.production-plan.v1",
        "blueprint_id": blueprint["blueprint_id"],
        "blueprint_sha256": _sha256(blueprint),
        "semantic_asset_id": blueprint["semantic_identity"]["semantic_asset_id"],
        "asset_type": blueprint["asset_type"],
        "asset_type_registry_revision": catalog.asset_registry["revision"],
        "marketplace_delivery_profile_revision": catalog.delivery_profiles["revision"],
        "producer": {
            "class": blueprint["producer_class"],
            "recipe_id": MASTER_RECIPE[blueprint["producer_class"]],
            "maturity": asset_type["maturity"]["state"],
        },
        "master": dict(blueprint["master_spec"]),
        "derivatives": derivative_plan,
        "policy_gate": {
            "compatibility_state": blueprint["policy"]["compatibility_state"],
            "marketplace_profiles": sorted(blueprint["policy"]["marketplace_profiles"]),
            "submission_blocked": submission_blocked,
            "submission_authority": "FOUNDER_CONTROLLED",
        },
    }