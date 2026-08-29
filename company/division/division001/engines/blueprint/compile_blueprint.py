#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
COMPILED_SCHEMA = ROOT / "die.division001.compiled-blueprint.v1.schema.json"
CAPABILITY_PROFILE = ROOT / "BLUEPRINT_COMPILER_CAPABILITY_PROFILE_V1.json"
AUTHOR_VALIDATOR = ROOT / "validate_blueprint_authoring.py"
BOUNDARY_PREPARER = ROOT / "prepare_compile_input.py"
REVIEW_VALIDATOR = ROOT / "validate_executive_blueprint_review.py"

class CompilerError(RuntimeError):
    pass

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CompilerError("E_MODULE_LOAD:" + path.name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

AUTHOR = _load("oe005d_author_validator", AUTHOR_VALIDATOR)
BOUNDARY = _load("oe005d_boundary_preparer", BOUNDARY_PREPARER)
REVIEW = _load("oe005d_review_validator", REVIEW_VALIDATOR)

def canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")

def sha(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def file_sha(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CompilerError("E_TIME_TZ")
    return parsed.astimezone(dt.timezone.utc)

def validate_capability_profile(profile: dict[str, Any]) -> None:
    if profile.get("schema") != "die.division001.blueprint-compiler-capability-profile.v1":
        raise CompilerError("E_CAPABILITY_PROFILE_SCHEMA")
    if profile.get("runtime_availability_claimed") is not False:
        raise CompilerError("E_CAPABILITY_PROFILE_RUNTIME_CLAIM")
    for engine_id, engine in profile.get("engines", {}).items():
        if not engine.get("asset_types") or not engine.get("provider_id") or not engine.get("required_capability"):
            raise CompilerError("E_CAPABILITY_PROFILE_INCOMPLETE:" + engine_id)
        for evidence in engine.get("contract_evidence", []):
            path = REPO / evidence["path"]
            if not path.exists():
                raise CompilerError("E_CAPABILITY_EVIDENCE_MISSING:" + evidence["path"])
            if file_sha(path) != evidence["sha256"]:
                raise CompilerError("E_CAPABILITY_EVIDENCE_HASH:" + evidence["path"])
        if engine_id == "MUXIA_CHATGPT_IMAGE":
            domain = (REPO / "company/muxia/src/core/domain.ts").read_text(encoding="utf-8")
            domain_test = (REPO / "company/muxia/tests/core/domain.test.mjs").read_text(encoding="utf-8")
            artifact_test = (REPO / "company/muxia/tests/core/job-artifact-registry.test.mjs").read_text(encoding="utf-8")
            if "requiredCapability: string" not in domain or "capabilities: readonly string[]" not in domain:
                raise CompilerError("E_CAPABILITY_CONTRACT_MUXIA_DOMAIN")
            if "requiredCapability: 'image.generate'" not in domain_test or "providerId: 'chatgpt'" not in domain_test:
                raise CompilerError("E_CAPABILITY_CONTRACT_MUXIA_DOMAIN_TEST")
            if "requiredCapability: 'image.generate'" not in artifact_test or "providerId: 'chatgpt'" not in artifact_test:
                raise CompilerError("E_CAPABILITY_CONTRACT_MUXIA_ARTIFACT_TEST")

def compile_blueprint(
    blueprint: dict[str, Any],
    *,
    governed_result: dict[str, Any],
    worth_making: dict[str, Any],
    worth_making_review: dict[str, Any],
    longtail_candidate: dict[str, Any],
    executive_blueprint_review: dict[str, Any],
    as_of: str,
) -> dict[str, Any]:
    author_errors = AUTHOR.validate(
        blueprint,
        governed_result=governed_result,
        worth_making=worth_making,
        executive_review=worth_making_review,
        longtail_candidate=longtail_candidate,
        as_of=as_of,
    )
    if author_errors:
        raise CompilerError("E_AUTHOR_ARTIFACT_INVALID:" + author_errors[0])

    boundary = BOUNDARY.prepare(
        blueprint,
        governed_result=governed_result,
        worth_making=worth_making,
        executive_review=worth_making_review,
        longtail_candidate=longtail_candidate,
        as_of=as_of,
    )
    review_errors = REVIEW.validate(
        executive_blueprint_review,
        blueprint=blueprint,
        compile_boundary=boundary,
        governed_result=governed_result,
    )
    if review_errors:
        raise CompilerError("E_EXECUTIVE_REVIEW_INVALID:" + review_errors[0])
    if executive_blueprint_review["outcome"] != "NO_VETO":
        raise CompilerError("E_EXECUTIVE_REVIEW_NOT_NO_VETO")
    now = parse_time(as_of)
    if now >= parse_time(executive_blueprint_review["expires_at"]):
        raise CompilerError("E_EXECUTIVE_REVIEW_STALE")
    if parse_time(executive_blueprint_review["reviewed_at"]) > now:
        raise CompilerError("E_EXECUTIVE_REVIEW_FROM_FUTURE")

    engines = blueprint["production"]["engines_eligible"]
    if len(engines) != 1:
        raise CompilerError("E_ENGINE_SELECTION_AMBIGUOUS")
    engine_id = engines[0]
    profile = json.loads(CAPABILITY_PROFILE.read_text(encoding="utf-8"))
    validate_capability_profile(profile)
    if engine_id not in profile["engines"]:
        raise CompilerError("E_ENGINE_UNSUPPORTED:" + engine_id)
    capability = profile["engines"][engine_id]
    asset_type = blueprint["production"]["asset_type"]
    if asset_type not in capability["asset_types"]:
        raise CompilerError("E_CAPABILITY_MISMATCH:" + asset_type + ":" + engine_id)

    production_contract = {
        "asset_type": asset_type,
        "batch_size": blueprint["production"]["batch_size"],
        "engine_id": engine_id,
        "family": copy.deepcopy(boundary["authored_semantics"]["family"]),
        "buyer": copy.deepcopy(boundary["authored_semantics"]["buyer"]),
        "product_expression": copy.deepcopy(boundary["authored_semantics"]["product_expression"]),
        "visual_spec": copy.deepcopy(boundary["authored_semantics"]["visual_spec"]),
        "master_prompt": boundary["authored_semantics"]["master_prompt"],
        "negative_constraints": copy.deepcopy(boundary["authored_semantics"]["negative_constraints"]),
        "semantic_variation_plan": copy.deepcopy(boundary["authored_semantics"]["semantic_variation_plan"]),
        "platform_strategy": copy.deepcopy(boundary["authored_semantics"]["platform_strategy"]),
        "metadata_direction": copy.deepcopy(boundary["authored_semantics"]["metadata_direction"]),
        "qa_falsification": copy.deepcopy(boundary["authored_semantics"]["qa_falsification"]),
        "economics": copy.deepcopy(boundary["authored_semantics"]["economics"]),
    }
    compiled = {
        "schema_version": "die.division001.compiled-blueprint.v1",
        "compiler": {
            "compiler_id": "division001-blueprint-compiler-v1",
            "version": "1.0.0",
            "role": "SERIALIZE_VALIDATE_HASH_ONLY",
            "capability_profile_sha256": file_sha(CAPABILITY_PROFILE),
        },
        "blueprint_id": blueprint["blueprint_id"],
        "repository_sha": blueprint["snapshot"]["repository_sha"],
        "author_artifact": {
            "artifact_id": blueprint["blueprint_id"],
            "sha256": sha(blueprint),
            "principal_id": blueprint["principal"]["principal_id"],
        },
        "executive_review": {
            "review_id": executive_blueprint_review["review_id"],
            "sha256": sha(executive_blueprint_review),
            "principal_id": executive_blueprint_review["principal"]["principal_id"],
            "outcome": executive_blueprint_review["outcome"],
        },
        "governed_worth_making": {
            "bundle_id": governed_result["bundle_id"],
            "sha256": sha(governed_result),
            "decision": governed_result["decision"],
        },
        "compile_boundary": {
            "sha256": sha(boundary),
            "semantic_content_mutated": boundary["semantic_content_mutated"],
        },
        "capability_plan": {
            "asset_type": asset_type,
            "engine_id": engine_id,
            "provider_id": capability["provider_id"],
            "required_capability": capability["required_capability"],
            "artifact_mime_types": capability["artifact_mime_types"],
            "contract_compatible": True,
            "runtime_availability_claimed": False,
        },
        "production_contract": production_contract,
        "semantic_hashes": copy.deepcopy(boundary["semantic_field_hashes"]),
        "production_authority_granted": False,
    }
    schema = json.loads(COMPILED_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(compiled), key=lambda e: list(e.absolute_path))
    if errors:
        raise CompilerError("E_COMPILED_SCHEMA:" + errors[0].message)
    if compiled["production_contract"]["master_prompt"] != blueprint["production"]["master_prompt"]:
        raise CompilerError("E_SEMANTIC_MUTATION:master_prompt")
    if compiled["production_contract"]["semantic_variation_plan"] != blueprint["production"]["semantic_variation_plan"]:
        raise CompilerError("E_SEMANTIC_MUTATION:variation_plan")
    return compiled

def write_compiled(path: Path, compiled: dict[str, Any]) -> str:
    raw = canonical_bytes(compiled)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("blueprint"); ap.add_argument("--governed-result", required=True); ap.add_argument("--worth-making", required=True); ap.add_argument("--worth-making-review", required=True); ap.add_argument("--longtail-candidate", required=True); ap.add_argument("--executive-blueprint-review", required=True); ap.add_argument("--as-of", required=True); ap.add_argument("--output", required=True)
    args = ap.parse_args()
    try:
        load_json=lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
        compiled=compile_blueprint(load_json(args.blueprint),governed_result=load_json(args.governed_result),worth_making=load_json(args.worth_making),worth_making_review=load_json(args.worth_making_review),longtail_candidate=load_json(args.longtail_candidate),executive_blueprint_review=load_json(args.executive_blueprint_review),as_of=args.as_of)
        digest=write_compiled(Path(args.output),compiled)
        print(json.dumps({"status":"PASS","compiled_blueprint_sha256":digest,"output":args.output,"production_authority_granted":False},indent=2)); return 0
    except Exception as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)},indent=2)); return 2

if __name__ == "__main__":
    raise SystemExit(main())