"""Offline FA-034 acceptance; internal packages never certify a marketplace."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from asset_identity import assert_identity_invariants
from package_composer import compose_dry_run_package
from pattern_qa import verify_pattern
from procedural_pattern import produce_pattern

ROOT = Path(__file__).resolve().parents[1]


def accept_fixture(request: dict, *, output_dir: str | Path) -> dict:
    """Exercise production, independent QA, regeneration and packaging in a new root."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    runs = [produce_pattern(copy.deepcopy(request), output_dir=root/name)
            for name in ("first", "regenerated")]
    qa = [verify_pattern(request, run) for run in runs]
    if any(row["result"] != "PASS" for row in qa):
        return {"result": "FAIL", "stage": "PATTERN_QA", "qa": qa}
    if runs[0]["native_receipt"] != runs[1]["native_receipt"]:
        return {"result": "FAIL", "stage": "DETERMINISM"}
    for section, key in (("pattern", "master_path"), ("preview", "path")):
        if Path(runs[0][section][key]).read_bytes() != Path(runs[1][section][key]).read_bytes():
            return {"result": "FAIL", "stage": "DETERMINISM"}

    produced = runs[0]
    master = Path(produced["pattern"]["master_path"])
    preview = Path(produced["preview"]["path"])
    original = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (master, preview)]

    # These fixture-only references certify internal artifact integrity, not a
    # marketplace route, rights clearance, or submission readiness.
    evidence = {
        "metadata": {"scope": "SYNTHETIC_ACCEPTANCE", "semantic_asset_id": request["semantic_asset_id"]},
        "rights": {"state": "NOT_EVALUATED", "publication_authority": "NONE"},
        "compatibility": {"scope": "FA034_INTERNAL_PACKAGE", "state": "COMPATIBLE",
                          "marketplace_compatibility": "COMPATIBILITY_UNKNOWN"},
    }
    for name, value in evidence.items():
        (root/f"{name}.json").write_text(json.dumps(value, sort_keys=True)+"\n")
    before = json.loads((ROOT/"fixtures/shopping-bag-blueprint-v2/pattern.json").read_text())
    before["blueprint_id"] = request["blueprint_id"]
    before["semantic_identity"]["semantic_asset_id"] = request["semantic_asset_id"]
    after = copy.deepcopy(before)
    after["derivatives"] = [
        {"derivative_id": "SVG_DELIVERY", "purpose": "MARKETPLACE_DELIVERY", "format": "SVG", "semantic_identity_effect": "NONE"},
        {"derivative_id": "TILED_PREVIEW", "purpose": "PREVIEW", "format": "PNG", "semantic_identity_effect": "NONE"},
    ]
    identity = assert_identity_invariants(before, after)
    deliverables = []
    for row, path in zip(after["derivatives"], (master, preview)):
        deliverables.append({**row, "source_path": str(path), "recipe_id": "FA034_INTERNAL_ACCEPTANCE",
                             "receipt_ref": "../compatibility.json", "compatibility_state": "COMPATIBLE"})
    package = compose_dry_run_package(
        package_dir=root/"package", semantic_asset_id=request["semantic_asset_id"],
        master_sha256=produced["pattern"]["master_sha256"], deliverables=deliverables,
        metadata_ref="../metadata.json", rights_ref="../rights.json",
        compatibility_receipt_ref="../compatibility.json")
    manifest = json.loads(Path(package["manifest_path"]).read_text())
    source_bytes = {"SVG_DELIVERY": original[0][0], "TILED_PREVIEW": original[1][0]}
    for row in manifest["deliverables"]:
        data = (root/"package"/row["package_path"]).read_bytes()
        if data != source_bytes[row["derivative_id"]] or len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            return {"result": "FAIL", "stage": "PACKAGE_LINEAGE"}
    if original != [(p.read_bytes(), p.stat().st_mtime_ns) for p in (master, preview)]:
        return {"result": "FAIL", "stage": "SOURCE_MUTATION"}
    return {"schema": "die.factory-asset.pattern-engine-fixture-acceptance.v1", "result": "PASS",
            "semantic_asset_id": request["semantic_asset_id"], "native_receipt": produced["native_receipt"],
            "qa": qa[0], "regeneration": "BYTE_IDENTICAL", "sources_unchanged": True,
            "master_sha256": produced["pattern"]["master_sha256"], "preview_sha256": produced["preview"]["sha256"],
            "identity_transition": identity, "package_manifest": manifest,
            "package": {k: v for k, v in package.items() if k != "manifest_path"},
            "compatibility_scope": "FA034_INTERNAL_PACKAGE", "marketplace_compatibility": "COMPATIBILITY_UNKNOWN"}
