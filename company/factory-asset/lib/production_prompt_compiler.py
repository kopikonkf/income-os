from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "company/factory-asset"
PRESET_REGISTRY_PATH = BASE / "registries/production-presets.v1.json"
PRESET_SCHEMA_PATH = BASE / "schemas/production-preset-registry.schema.json"
SUBJECT_SCHEMA_PATH = BASE / "schemas/subject-spec.v1.schema.json"
VISUAL_SCHEMA_PATH = BASE / "schemas/visual-requirement-spec.v1.schema.json"
COMPILED_SCHEMA_PATH = BASE / "schemas/compiled-provider-prompt.v1.schema.json"
COMPILER_REVISION = "1.0.0"


class ProductionPromptError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_schema(instance: Any, schema_path: Path, code: str) -> None:
    validator = jsonschema.Draft202012Validator(_load(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        where = ".".join(str(x) for x in first.absolute_path) or "$"
        raise ProductionPromptError(code, f"{where}: {first.message}")


def validate_preset_registry(registry: dict[str, Any]) -> None:
    _validate_schema(registry, PRESET_SCHEMA_PATH, "PRESET_REGISTRY_SCHEMA_INVALID")
    ids: set[tuple[str, str]] = set()
    for row in registry["presets"]:
        key = (row["preset_id"], row["revision"])
        if key in ids:
            raise ProductionPromptError("PRESET_DUPLICATE", f"{key[0]}@{key[1]}")
        ids.add(key)
        if row["composition_defaults"]["background_mode"] not in row["composition_defaults"]["allowed_background_modes"]:
            raise ProductionPromptError("PRESET_BACKGROUND_DEFAULT_NOT_ALLOWED", row["preset_id"])
        if row["asset_type"] == "ISOLATED_OBJECT":
            c = row["composition_defaults"]
            if not c["full_subject_visible"] or not c["clean_silhouette"] or c["unrelated_props"]:
                raise ProductionPromptError("ISOLATED_PRESET_COMPOSITION_INVALID", row["preset_id"])


def load_preset_registry(path: Path = PRESET_REGISTRY_PATH) -> dict[str, Any]:
    registry = _load(path)
    validate_preset_registry(registry)
    return registry


def get_preset(preset_id: str, revision: str | None = None, *, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_preset_registry()
    rows = [x for x in registry["presets"] if x["preset_id"] == preset_id and (revision is None or x["revision"] == revision)]
    if not rows:
        raise ProductionPromptError("PRESET_NOT_FOUND", f"{preset_id}@{revision or 'latest'}")
    if revision is None:
        rows.sort(key=lambda x: tuple(int(n) for n in x["revision"].split(".")), reverse=True)
    return copy.deepcopy(rows[0])


def validate_subject_spec(subject_spec: dict[str, Any]) -> None:
    _validate_schema(subject_spec, SUBJECT_SCHEMA_PATH, "SUBJECT_SPEC_SCHEMA_INVALID")
    names = [x["name"].strip().casefold() for x in subject_spec["essential_components"]]
    if len(names) != len(set(names)):
        raise ProductionPromptError("SUBJECT_COMPONENT_DUPLICATE", subject_spec["subject_spec_id"])
    if not subject_spec["recognition_anchors"]:
        raise ProductionPromptError("SUBJECT_RECOGNITION_ANCHOR_REQUIRED", subject_spec["subject_spec_id"])


def validate_visual_spec(visual_spec: dict[str, Any]) -> None:
    _validate_schema(visual_spec, VISUAL_SCHEMA_PATH, "VISUAL_SPEC_SCHEMA_INVALID")
    if visual_spec["asset_type"] == "ISOLATED_OBJECT":
        c = visual_spec["composition"]
        if not c["full_subject_visible"]:
            raise ProductionPromptError("ISOLATED_FULL_SUBJECT_REQUIRED", visual_spec["visual_spec_id"])
        if not c["clean_silhouette"]:
            raise ProductionPromptError("ISOLATED_CLEAN_SILHOUETTE_REQUIRED", visual_spec["visual_spec_id"])
        if c["unrelated_props"]:
            raise ProductionPromptError("ISOLATED_UNRELATED_PROPS_FORBIDDEN", visual_spec["visual_spec_id"])
    negative = [x.casefold() for x in visual_spec["negative_constraints"]]
    for mandatory in ("readable text", "logo", "trademark", "watermark"):
        if not any(mandatory in x for x in negative):
            raise ProductionPromptError("VISUAL_NEGATIVE_REQUIRED", mandatory)


_VIEW_DEFAULT = {
    "SUBJECT_APPROPRIATE": "use the clearest subject-appropriate commercial view",
    "FRONT": "front view",
    "THREE_QUARTER": "three-quarter view",
    "TOP_DOWN": "top-down view",
    "SIDE": "side view",
    "ISOMETRIC": "clean isometric view",
}


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    return value[:72] or "SPEC"


def resolve_visual_requirements(
    *,
    subject_spec: dict[str, Any],
    semantic_asset_id: str,
    preset_id: str,
    preset_revision: str | None = None,
    overrides: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_subject_spec(subject_spec)
    preset = get_preset(preset_id, preset_revision, registry=registry)
    overrides = copy.deepcopy(overrides or {})
    allowed_override_keys = {"background_mode", "viewpoint", "view_instruction", "extra_negative_constraints"}
    unknown = sorted(set(overrides) - allowed_override_keys)
    if unknown:
        raise ProductionPromptError("VISUAL_OVERRIDE_UNKNOWN", ",".join(unknown))

    background = overrides.get("background_mode", preset["composition_defaults"]["background_mode"])
    if background not in preset["composition_defaults"]["allowed_background_modes"]:
        raise ProductionPromptError("BACKGROUND_NOT_ALLOWED_BY_PRESET", f"{preset_id}:{background}")

    viewpoint = overrides.get("viewpoint", preset["view_defaults"]["viewpoint"])
    if viewpoint == "CUSTOM" and not str(overrides.get("view_instruction", "")).strip():
        raise ProductionPromptError("CUSTOM_VIEW_INSTRUCTION_REQUIRED", preset_id)
    instruction = str(overrides.get("view_instruction") or _VIEW_DEFAULT.get(viewpoint, "use a clear commercial view")).strip()

    extra_neg = overrides.get("extra_negative_constraints", [])
    if not isinstance(extra_neg, list) or any(not isinstance(x, str) or not x.strip() for x in extra_neg):
        raise ProductionPromptError("NEGATIVE_OVERRIDE_INVALID", preset_id)
    negatives: list[str] = []
    for item in [*preset["negative_defaults"], *extra_neg]:
        if item not in negatives:
            negatives.append(item)

    sid = _safe_id(f"{semantic_asset_id}_{preset['preset_id']}")
    visual = {
        "schema": "die.factory-asset.visual-requirement-spec.v1",
        "visual_spec_id": f"FAVS-{sid}",
        "semantic_asset_id": semantic_asset_id,
        "asset_type": preset["asset_type"],
        "subject_spec_id": subject_spec["subject_spec_id"],
        "preset": {"preset_id": preset["preset_id"], "revision": preset["revision"]},
        "subject": {k: copy.deepcopy(subject_spec[k]) for k in [
            "canonical_name", "subject_class", "primary_form", "essential_components", "recognition_anchors",
            "natural_attributes", "spatial_relationships", "forbidden_subject_mutations"
        ]},
        "view": {"viewpoint": viewpoint, "instruction": instruction},
        "rendering": {
            "render_language": preset["render_language"],
            "style_family": preset["style"]["family"],
            "style_variant": preset["style"]["variant"],
            "medium": preset["style"]["medium"],
            "stylization": preset["style"]["stylization"],
            "prompt_descriptors": copy.deepcopy(preset["prompt_descriptors"]),
        },
        "fidelity": copy.deepcopy(preset["fidelity_defaults"]),
        "composition": {
            "background_mode": background,
            "centered": preset["composition_defaults"]["centered"],
            "full_subject_visible": preset["composition_defaults"]["full_subject_visible"],
            "generous_whitespace": preset["composition_defaults"]["generous_whitespace"],
            "clean_silhouette": preset["composition_defaults"]["clean_silhouette"],
            "unrelated_props": preset["composition_defaults"]["unrelated_props"],
        },
        "commercial": copy.deepcopy(preset["commercial_defaults"]),
        "negative_constraints": negatives,
        "authority": {"effect": "NONE", "provider_call_authorized": False, "submission_authorized": False, "publication_authorized": False},
    }
    validate_visual_spec(visual)
    return visual


_FIDELITY_BY_FIELD = {
    "proportions": {
        "REALISTIC": "realistic proportions",
        "NATURAL_RECOGNIZABLE": "natural recognizable proportions",
        "STYLIZED_RECOGNIZABLE": "stylized but recognizable proportions",
    },
    "recognizability": {"HIGH": "high recognizability", "VERY_HIGH": "immediately recognizable subject identity"},
    "texture_detail": {"LOW": "minimal texture detail", "LIGHT": "light texture detail", "MODERATE": "moderate texture detail", "DETAILED": "detailed textures"},
    "color_behavior": {"NATURAL": "natural colors", "VIBRANT_REALISTIC": "vibrant but realistic colors", "FRIENDLY_STYLIZED": "friendly stylized colors", "MUTED": "muted controlled colors"},
    "edge_character": {"CRISP_CLEAN": "crisp clean edges", "SOFT_HAND_PAINTED": "soft hand-painted edges", "SMOOTH_VECTOR_LIKE": "smooth vector-like edges", "NATURAL_PHOTOGRAPHIC": "natural photographic edges"},
    "shading": {"NONE": "no artificial shading", "SUBTLE": "subtle soft highlights and shading", "GENTLE": "gentle shading", "NATURAL": "natural shading", "DETAILED": "detailed natural shading"},
}


_BACKGROUND = {
    "TRANSPARENT": "transparent background with no background elements",
    "PURE_WHITE": "pure white background with no environmental elements",
    "SOLID_NEUTRAL": "simple solid neutral background with no environmental elements",
}


def _dedupe_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        item = raw.strip().rstrip(".")
        key = item.casefold()
        if item and key not in seen:
            out.append(item)
            seen.add(key)
    return out


def _render_prompt(visual_spec: dict[str, Any]) -> tuple[str, str]:
    s = visual_spec["subject"]
    r = visual_spec["rendering"]
    f = visual_spec["fidelity"]
    c = visual_spec["composition"]
    commercial = visual_spec["commercial"]
    clauses: list[str] = []

    if visual_spec["asset_type"] == "ISOLATED_OBJECT":
        clauses.append(f"Create exactly one standalone isolated {s['canonical_name']} as a polished commercial stock asset")
    else:
        clauses.append(f"Create exactly one {s['canonical_name']} as a polished commercial stock asset")
    clauses.append(f"Primary subject form: {s['primary_form']}")

    if s["essential_components"]:
        parts = []
        for comp in s["essential_components"]:
            parts.append(f"{comp['name']} - {comp['description']}; {comp['placement']}")
        clauses.append("Required visible components: " + "; ".join(parts))
    clauses.append("Recognition anchors: " + "; ".join(s["recognition_anchors"]))
    if s["natural_attributes"]:
        clauses.append("Natural subject attributes: " + "; ".join(s["natural_attributes"]))
    if s["spatial_relationships"]:
        clauses.append("Spatial structure: " + "; ".join(s["spatial_relationships"]))

    clauses.append("View: " + visual_spec["view"]["instruction"])
    clauses.append("Rendering direction: " + "; ".join(r["prompt_descriptors"]))

    fidelity_terms = _dedupe_keep_order([
        _FIDELITY_BY_FIELD["proportions"].get(f["proportions"], f["proportions"].replace("_", " ").lower()),
        _FIDELITY_BY_FIELD["recognizability"].get(f["recognizability"], f["recognizability"].replace("_", " ").lower()),
        _FIDELITY_BY_FIELD["texture_detail"].get(f["texture_detail"], f["texture_detail"].replace("_", " ").lower()),
        _FIDELITY_BY_FIELD["color_behavior"].get(f["color_behavior"], f["color_behavior"].replace("_", " ").lower()),
        _FIDELITY_BY_FIELD["edge_character"].get(f["edge_character"], f["edge_character"].replace("_", " ").lower()),
        _FIDELITY_BY_FIELD["shading"].get(f["shading"], f["shading"].replace("_", " ").lower()),
    ])
    clauses.append("Fidelity requirements: " + "; ".join(fidelity_terms))

    comp_terms = []
    if c["centered"]: comp_terms.append("centered composition")
    if c["full_subject_visible"]: comp_terms.append("complete subject fully visible with no crop")
    if c["generous_whitespace"]: comp_terms.append("generous usable whitespace")
    if c["clean_silhouette"]: comp_terms.append("clean separable silhouette")
    comp_terms.append(_BACKGROUND[c["background_mode"]])
    if not c["unrelated_props"]: comp_terms.append("no unrelated props")
    clauses.append("Composition requirements: " + "; ".join(comp_terms))

    sep = "very clear" if commercial["subject_separation"] == "VERY_CLEAR" else "clear"
    clauses.append(f"Commercial-use requirements: reusable standalone stock design component; {sep} visual separation; production-ready stock asset quality")
    if s["forbidden_subject_mutations"]:
        clauses.append("Preserve subject integrity: " + "; ".join(s["forbidden_subject_mutations"]))

    negative = "; ".join(visual_spec["negative_constraints"])
    clauses.append("Do not include: " + negative)
    prompt = ". ".join(_dedupe_keep_order(clauses)) + "."
    return prompt, negative


def compile_provider_prompt(*, subject_spec: dict[str, Any], visual_spec: dict[str, Any]) -> dict[str, Any]:
    validate_subject_spec(subject_spec)
    validate_visual_spec(visual_spec)
    if subject_spec["subject_spec_id"] != visual_spec["subject_spec_id"]:
        raise ProductionPromptError("SUBJECT_VISUAL_ID_MISMATCH", visual_spec["visual_spec_id"])
    if subject_spec["canonical_name"] != visual_spec["subject"]["canonical_name"]:
        raise ProductionPromptError("SUBJECT_VISUAL_NAME_MISMATCH", visual_spec["visual_spec_id"])

    provider_prompt, negative = _render_prompt(visual_spec)
    if len(provider_prompt) > 8000:
        raise ProductionPromptError("COMPILED_PROMPT_TOO_LONG", str(len(provider_prompt)))
    if re.search(r"<[^>]{1,80}>|\bTODO\b|\bTBD\b", provider_prompt, flags=re.I):
        raise ProductionPromptError("COMPILED_PROMPT_PLACEHOLDER", visual_spec["visual_spec_id"])

    compiled = {
        "schema": "die.factory-asset.compiled-provider-prompt.v1",
        "compiler_revision": COMPILER_REVISION,
        "visual_spec_id": visual_spec["visual_spec_id"],
        "subject_spec_sha256": canonical_sha256(subject_spec),
        "visual_spec_sha256": canonical_sha256(visual_spec),
        "preset_id": visual_spec["preset"]["preset_id"],
        "preset_revision": visual_spec["preset"]["revision"],
        "provider_prompt": provider_prompt,
        "negative_prompt": negative,
        "required_component_names": [x["name"] for x in visual_spec["subject"]["essential_components"]],
        "required_recognition_anchors": list(visual_spec["subject"]["recognition_anchors"]),
        "provider_prompt_sha256": hashlib.sha256(provider_prompt.encode("utf-8")).hexdigest(),
        "compiled_contract_sha256": "0" * 64,
    }
    compiled["compiled_contract_sha256"] = canonical_sha256({k: v for k, v in compiled.items() if k != "compiled_contract_sha256"})
    validate_compiled_prompt(compiled=compiled, subject_spec=subject_spec, visual_spec=visual_spec)
    return compiled


def validate_compiled_prompt(*, compiled: dict[str, Any], subject_spec: dict[str, Any], visual_spec: dict[str, Any]) -> None:
    _validate_schema(compiled, COMPILED_SCHEMA_PATH, "COMPILED_PROMPT_SCHEMA_INVALID")
    validate_subject_spec(subject_spec)
    validate_visual_spec(visual_spec)
    if compiled["subject_spec_sha256"] != canonical_sha256(subject_spec):
        raise ProductionPromptError("COMPILED_SUBJECT_HASH_MISMATCH", compiled["visual_spec_id"])
    if compiled["visual_spec_sha256"] != canonical_sha256(visual_spec):
        raise ProductionPromptError("COMPILED_VISUAL_HASH_MISMATCH", compiled["visual_spec_id"])
    if compiled["provider_prompt_sha256"] != hashlib.sha256(compiled["provider_prompt"].encode("utf-8")).hexdigest():
        raise ProductionPromptError("COMPILED_PROMPT_HASH_MISMATCH", compiled["visual_spec_id"])
    expected_contract = canonical_sha256({k: v for k, v in compiled.items() if k != "compiled_contract_sha256"})
    if compiled["compiled_contract_sha256"] != expected_contract:
        raise ProductionPromptError("COMPILED_CONTRACT_HASH_MISMATCH", compiled["visual_spec_id"])

    prompt = compiled["provider_prompt"].casefold()
    for name in compiled["required_component_names"]:
        if name.casefold() not in prompt:
            raise ProductionPromptError("COMPILED_COMPONENT_OMITTED", name)
    for anchor in compiled["required_recognition_anchors"]:
        if anchor.casefold() not in prompt:
            raise ProductionPromptError("COMPILED_RECOGNITION_ANCHOR_OMITTED", anchor)
    for desc in visual_spec["rendering"]["prompt_descriptors"]:
        if desc.casefold() not in prompt:
            raise ProductionPromptError("COMPILED_STYLE_DESCRIPTOR_OMITTED", desc)
    for neg in visual_spec["negative_constraints"]:
        if neg.casefold() not in prompt:
            raise ProductionPromptError("COMPILED_NEGATIVE_OMITTED", neg)
    expected_bg = _BACKGROUND[visual_spec["composition"]["background_mode"]].casefold()
    if expected_bg not in prompt:
        raise ProductionPromptError("COMPILED_BACKGROUND_OMITTED", visual_spec["composition"]["background_mode"])


def compile_from_files(*, subject_path: Path, semantic_asset_id: str, preset_id: str, preset_revision: str | None = None, overrides: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    subject = _load(subject_path)
    visual = resolve_visual_requirements(subject_spec=subject, semantic_asset_id=semantic_asset_id, preset_id=preset_id, preset_revision=preset_revision, overrides=overrides)
    compiled = compile_provider_prompt(subject_spec=subject, visual_spec=visual)
    return visual, compiled
