from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "company" / "scripts" / "validate_one_canon.py"
SPEC = importlib.util.spec_from_file_location("die_one_canon_validator", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


def _copy(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    root.mkdir()

    files = [
        "company/contracts/die.one-canon-validator.v1.json",
        "company/contracts/die.path-roots.v1.json",
        "company/component-registry-v1.json",
        "company/muxia-task-graph-v1.json",
        "docs/migration/DIE_WINDOWS_ESTATE_DISPOSITION_MATRIX_V1.md",
        "company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md",
        "company/atlas/object-centric/object-asset-engine/source-snapshot/windows-v1/SOURCE_MANIFEST.json",
        "company/next-subprojects/web-ai-oauth-adapter/source-snapshot/core-v1/SOURCE_MANIFEST.json",
    ]
    for rel in files:
        _copy(ROOT / rel, root / rel)

    # Snapshot payloads must exactly match their manifests.
    for manifest_rel in [
        "company/atlas/object-centric/object-asset-engine/source-snapshot/windows-v1/SOURCE_MANIFEST.json",
        "company/next-subprojects/web-ai-oauth-adapter/source-snapshot/core-v1/SOURCE_MANIFEST.json",
    ]:
        manifest = json.loads((ROOT / manifest_rel).read_text(encoding="utf-8"))
        for row in manifest["files"]:
            src = ROOT / pathlib.Path(manifest_rel).parent / pathlib.Path(row["path"])
            dst = root / pathlib.Path(manifest_rel).parent / pathlib.Path(row["path"])
            _copy(src, dst)

    registry = json.loads((root / "company/component-registry-v1.json").read_text(encoding="utf-8"))
    for component in registry["components"].values():
        (root / component["logical_root"]).mkdir(parents=True, exist_ok=True)
        for ref in component["source_refs"]:
            if len(ref) >= 3 and ref[1:3] == ":\\":
                continue
            path = root / ref
            if ref.endswith("/"):
                path.mkdir(parents=True, exist_ok=True)
            elif not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")

    # Operational files only need to prove the old Atlas path is absent.
    new_atlas = "company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md"
    for rel in [
        "COMPANY_BRAIN.md",
        "bridge/income_os_bridge/canon_context.py",
        "bridge/tests/test_runtime_canon_load_contract_v1.py",
        "company/runtime-canon-context-v1.json",
        "IDENTITY/chatgpt-plus-executive.md",
        "IDENTITY/division-head-division01.md",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(new_atlas + "\n", encoding="utf-8")

    contract = json.loads((root / "company/contracts/die.one-canon-validator.v1.json").read_text(encoding="utf-8"))
    for rel in contract["legacy_tracked_runtime_allowlist"]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")

    _git(root, "init")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "DIE-104 Fixture")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root


def _failed_names(payload: dict) -> set[str]:
    return {item["name"] for item in payload["results"] if not item["ok"]}


def test_die104_current_repo_passes_one_canon_validator() -> None:
    payload = validator.validate(ROOT)
    assert payload["status"] == "PASS", payload
    assert payload["checks_failed"] == 0
    assert payload["checks_passed"] == payload["checks_total"] == 11


def test_die104_fixture_passes(tmp_path: pathlib.Path) -> None:
    root = _fixture(tmp_path)
    payload = validator.validate(root, require_clean=True)
    assert payload["status"] == "PASS", payload


def test_die104_fails_closed_on_forbidden_company_credentials(tmp_path: pathlib.Path) -> None:
    root = _fixture(tmp_path)
    bad = root / "company/next-subprojects/web-ai-oauth-adapter/credentials/token.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{}\n", encoding="utf-8")
    _git(root, "add", str(bad.relative_to(root)))
    payload = validator.validate(root)
    assert payload["status"] == "FAIL"
    assert "company_forbidden_paths" in _failed_names(payload)


def test_die104_fails_closed_on_new_tracked_runtime_state(tmp_path: pathlib.Path) -> None:
    root = _fixture(tmp_path)
    bad = root / "state/NEW.jsonl"
    bad.write_text("{}\n", encoding="utf-8")
    _git(root, "add", str(bad.relative_to(root)))
    payload = validator.validate(root)
    assert payload["status"] == "FAIL"
    assert "legacy_runtime_boundary" in _failed_names(payload)


def test_die104_fails_closed_on_architect_ordering_drift(tmp_path: pathlib.Path) -> None:
    root = _fixture(tmp_path)
    graph_path = root / "company/muxia-task-graph-v1.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    mx053 = next(task for task in graph["tasks"] if task["id"] == "MX-053")
    mx053["depends_on"] = ["DIE-104"]
    graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    payload = validator.validate(root)
    assert payload["status"] == "FAIL"
    assert "migration_boundaries" in _failed_names(payload)


def test_die104_fails_closed_on_snapshot_tamper(tmp_path: pathlib.Path) -> None:
    root = _fixture(tmp_path)
    manifest_path = root / "company/next-subprojects/web-ai-oauth-adapter/source-snapshot/core-v1/SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = manifest_path.parent / manifest["files"][0]["path"]
    target.write_text(target.read_text(encoding="utf-8") + "# tamper\n", encoding="utf-8")
    payload = validator.validate(root)
    assert payload["status"] == "FAIL"
    assert "oauth_snapshot" in _failed_names(payload)
