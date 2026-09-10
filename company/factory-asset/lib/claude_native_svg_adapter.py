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
SCHEMA_PATH = BASE / "schemas/claude-native-svg-adapter.v1.schema.json"
CONTRACT_PATH = BASE / "providers/claude/native-vector/contract.v1.json"


class ClaudeNativeVectorError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_contract() -> dict[str, Any]:
    d = _load(CONTRACT_PATH)
    if d.get("schema") != "die.factory-asset.claude-native-svg-producer.v1":
        raise ClaudeNativeVectorError("CONTRACT_SCHEMA_INVALID", str(CONTRACT_PATH))
    if d.get("engine_state") != "CANDIDATE_UNACCEPTED":
        raise ClaudeNativeVectorError("ROUTE_PREMATURELY_ACCEPTED", d.get("engine_state", "missing"))
    return d


def validate_request(req: dict[str, Any]) -> None:
    schema = _load(SCHEMA_PATH)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(req), key=lambda e: list(e.absolute_path))
    if errors:
        e = errors[0]
        where = ".".join(str(x) for x in e.absolute_path) or "$"
        raise ClaudeNativeVectorError("REQUEST_SCHEMA_INVALID", f"{where}: {e.message}")
    if sha256_text(req["provider_prompt"]) != req["provider_prompt_sha256"]:
        raise ClaudeNativeVectorError("PROMPT_HASH_MISMATCH", req["job_id"])


def _validate_blueprint(blueprint: dict[str, Any], frozen_blueprint_sha256: str) -> None:
    if sha256_value(blueprint) != frozen_blueprint_sha256:
        raise ClaudeNativeVectorError("FROZEN_BLUEPRINT_HASH_MISMATCH", blueprint.get("blueprint_id", "unknown"))
    if blueprint.get("asset_type") not in {"ICON", "OUTLINE"}:
        raise ClaudeNativeVectorError("UNSUPPORTED_ASSET_TYPE", str(blueprint.get("asset_type")))
    if blueprint.get("producer_class") != "NATIVE_VECTOR":
        raise ClaudeNativeVectorError("PRODUCER_CLASS_MISMATCH", str(blueprint.get("producer_class")))
    if blueprint.get("native_representation") != "VECTOR_PATHS":
        raise ClaudeNativeVectorError("NATIVE_REPRESENTATION_MISMATCH", str(blueprint.get("native_representation")))
    if blueprint.get("master_spec", {}).get("format") != "SVG":
        raise ClaudeNativeVectorError("MASTER_FORMAT_NOT_SVG", str(blueprint.get("master_spec", {}).get("format")))


def build_request(
    *, job_id: str, blueprint: dict[str, Any], frozen_blueprint_sha256: str,
    provider_prompt: str, provider_prompt_sha256: str | None = None,
    producer_version: str = "1.0.0",
) -> dict[str, Any]:
    contract = load_contract()
    _validate_blueprint(blueprint, frozen_blueprint_sha256)
    provider_prompt = provider_prompt.strip()
    if not provider_prompt:
        raise ClaudeNativeVectorError("PROMPT_EMPTY", job_id)
    actual_prompt_sha = sha256_text(provider_prompt)
    if provider_prompt_sha256 is not None and provider_prompt_sha256 != actual_prompt_sha:
        raise ClaudeNativeVectorError("PROMPT_HASH_MISMATCH", job_id)
    sid = blueprint["semantic_identity"]["semantic_asset_id"]
    material = {
        "provider_id": "claude", "producer_class": "NATIVE_VECTOR", "producer_version": producer_version,
        "blueprint_id": blueprint["blueprint_id"], "semantic_asset_id": sid,
        "frozen_blueprint_sha256": frozen_blueprint_sha256, "provider_prompt_sha256": actual_prompt_sha,
    }
    req = {
        "schema": "die.factory-asset.claude-native-svg-adapter-request.v1",
        "job_id": job_id,
        "idempotency_key": sha256_value(material),
        "provider_id": "claude",
        "producer_class": "NATIVE_VECTOR",
        "producer_version": producer_version,
        "blueprint_id": blueprint["blueprint_id"],
        "semantic_asset_id": sid,
        "asset_type": blueprint["asset_type"],
        "native_representation": "VECTOR_PATHS",
        "master_format": "SVG",
        "frozen_blueprint_sha256": frozen_blueprint_sha256,
        "provider_prompt": provider_prompt,
        "provider_prompt_sha256": actual_prompt_sha,
        "output_contract": {
            "payload_kind": "SVG_SOURCE_TEXT", "native_editable_required": True,
            "conversion_from_raster": False, "embedded_raster_only_allowed": False,
            "scripts_allowed": False, "external_references_allowed": False,
        },
        "authority": {"provider_call_authorized": False, "submission_authorized": False, "publication_authorized": False},
    }
    validate_request(req)
    return req


def normalize_svg_payload(payload: str) -> str:
    text = payload.strip()
    fence = re.fullmatch(r"```(?:svg|xml)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("<svg")
    end = text.rfind("</svg>")
    if start < 0 or end < 0:
        raise ClaudeNativeVectorError("OUTPUT_NOT_SVG", "missing svg root")
    prefix = text[:start].strip()
    suffix = text[end + len("</svg>"):].strip()
    if prefix or suffix:
        raise ClaudeNativeVectorError("PROVIDER_RESPONSE_INVALID", "non-SVG prose outside root")
    return text[start:end + len("</svg>")]


def build_unaccepted_receipt(*, req: dict[str, Any], normalized_svg_sha256: str | None = None) -> dict[str, Any]:
    validate_request(req)
    return {
        "schema": "die.factory-asset.claude-native-svg-candidate-receipt.v1",
        "job_id": req["job_id"], "idempotency_key": req["idempotency_key"],
        "provider_id": "claude", "producer_class": "NATIVE_VECTOR", "producer_version": req["producer_version"],
        "route_state": "UNAVAILABLE_NOT_ACCEPTED", "candidate_svg_sha256": normalized_svg_sha256,
        "fa321_validation_required": True, "fa322_live_acceptance_required": True,
        "provider_call_authorized": False, "submission_authorized": False, "publication_authorized": False,
    }
