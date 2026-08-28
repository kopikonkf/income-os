#!/usr/bin/env python3
"""Fail-closed Chapter #4 one-canon validator (DIE-104).

Stdlib only. Validates repository topology, ownership, path-root separation,
tracked runtime exceptions, external source snapshots, and migration boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


SECRET_PATTERNS = [
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: pathlib.Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "git failed")
    return proc.stdout.splitlines()


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(name: str, fn) -> CheckResult:
    try:
        detail = fn()
        return CheckResult(name, True, str(detail or "PASS"))
    except Exception as exc:  # fail closed: any unexpected validation error is a failure
        return CheckResult(name, False, f"{type(exc).__name__}: {exc}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _task_by_id(graph: dict) -> dict[str, dict]:
    tasks = graph.get("tasks")
    _assert(isinstance(tasks, list), "task graph tasks must be a list")
    by = {}
    for task in tasks:
        ident = task.get("id")
        _assert(ident and ident not in by, f"invalid/duplicate task id: {ident}")
        by[ident] = task
    return by


def validate(root: pathlib.Path, *, require_clean: bool = False) -> dict:
    root = root.resolve()
    contract_path = root / "company/contracts/die.one-canon-validator.v1.json"
    contract = _load_json(contract_path)
    canonical = contract["canonical_paths"]
    results: list[CheckResult] = []

    def add(name: str, fn) -> None:
        results.append(_check(name, fn))

    def repo_identity() -> str:
        top = pathlib.Path(_git(root, "rev-parse", "--show-toplevel")[0]).resolve()
        _assert(top == root, f"validator root is not Git top-level: {top}")
        if require_clean:
            dirty = _git(root, "status", "--porcelain")
            _assert(not dirty, f"worktree dirty: {len(dirty)} paths")
        return f"git_root={top}; require_clean={require_clean}"

    add("repo_identity", repo_identity)

    def required_files() -> str:
        for rel in canonical.values():
            p = root / rel
            if rel == canonical["legacy_human_atlas"]:
                continue
            _assert(p.exists(), f"required canonical path missing: {rel}")
        _assert(not (root / canonical["legacy_human_atlas"]).exists(), "legacy Atlas path still exists")
        return "canonical paths present; legacy Atlas absent"

    add("canonical_paths", required_files)

    registry = _load_json(root / canonical["component_registry"])
    graph = _load_json(root / canonical["task_graph"])
    path_contract = _load_json(root / canonical["path_roots_contract"])
    disposition = (root / canonical["disposition_matrix"]).read_text(encoding="utf-8")

    def component_registry() -> str:
        _assert(registry.get("schema") == "die.component-registry.v1", "wrong component registry schema")
        _assert(registry.get("status") == "CANON", "component registry not CANON")
        components = registry.get("components")
        _assert(isinstance(components, dict), "components must be object")
        required = set(contract["required_components"])
        _assert(set(components) == required, f"component set mismatch: {sorted(set(components) ^ required)}")
        for name, component in components.items():
            logical = component.get("logical_root")
            _assert(logical and not pathlib.PurePosixPath(logical).is_absolute(), f"invalid logical_root for {name}")
            _assert((root / logical).is_dir(), f"logical_root missing for {name}: {logical}")
            refs = component.get("source_refs", [])
            _assert(isinstance(refs, list) and refs, f"source_refs missing for {name}")
            for ref in refs:
                # Absolute Windows external roots are boundary/provenance references, not repo files.
                if re.match(r"^[A-Za-z]:\\", ref):
                    _assert(name in {"architect"}, f"unexpected absolute source_ref for {name}: {ref}")
                    continue
                _assert((root / ref).exists(), f"source_ref missing for {name}: {ref}")
        return f"components={len(components)}"

    add("component_registry", component_registry)

    def path_roots() -> str:
        _assert(path_contract.get("schema") == "die.path-roots.v1", "wrong path-root schema")
        env = path_contract["environment"]
        expected = contract["linux_roots"]
        actual = {key: env[key]["linux_default"] for key in expected}
        _assert(actual == expected, f"Linux root mismatch: {actual}")
        values = list(actual.values())
        _assert(len(values) == len(set(values)), "Linux source/state/config/install roots overlap exactly")
        for value in values:
            _assert(value.startswith("/"), f"Linux root not absolute: {value}")
        _assert(path_contract["derived"]["STATE"] == "<DIE_STATE_ROOT>/state", "STATE not state-root derived")
        _assert(path_contract["derived"]["WORKSPACES"] == "<DIE_STATE_ROOT>/workspaces", "WORKSPACES not state-root derived")
        return json.dumps(actual, sort_keys=True)

    add("path_root_separation", path_roots)

    tracked = _git(root, "ls-files")

    def company_forbidden_paths() -> str:
        forbidden_components = set(contract["company_forbidden_path_components"])
        forbidden_suffixes = tuple(contract["company_forbidden_suffixes"])
        bad = []
        for rel in tracked:
            if not rel.startswith("company/"):
                continue
            parts = pathlib.PurePosixPath(rel).parts
            if any(part in forbidden_components for part in parts) or rel.endswith(forbidden_suffixes):
                bad.append(rel)
        _assert(not bad, f"forbidden tracked company paths: {bad[:20]}")
        return "forbidden_company_paths=0"

    add("company_forbidden_paths", company_forbidden_paths)

    def legacy_runtime_boundary() -> str:
        current_state = sorted(rel for rel in tracked if rel.startswith("state/"))
        allowed = sorted(contract["legacy_tracked_runtime_allowlist"])
        _assert(current_state == allowed, f"legacy tracked state changed: added/removed={sorted(set(current_state) ^ set(allowed))}")
        tracked_workspaces = [rel for rel in tracked if rel.startswith("workspaces/")]
        _assert(not tracked_workspaces, f"tracked workspaces forbidden: {tracked_workspaces[:20]}")
        return f"legacy_state_allowlist={len(allowed)}; tracked_workspaces=0"

    add("legacy_runtime_boundary", legacy_runtime_boundary)

    def migration_boundaries() -> str:
        components = registry["components"]
        architect = components["architect"]
        expected_arch = contract["architect_boundary"]
        _assert(architect["status"] == expected_arch["component_status"], "Architect component status drift")
        _assert(architect["migration_task"] == expected_arch["migration_task"], "Architect migration task drift")
        _assert(architect["source_refs"] == [r"D:\mcp-architect"], "Architect source must remain external/deferred")

        division = components["division01"]
        expected_div = contract["division01_boundary"]
        _assert(division.get("principal_id") == expected_div["principal_id"], "Division01 principal drift")
        _assert(division.get("logical_root") == "company/division/division001", "Division01 logical-root drift")
        oauth = components["web_ai_oauth_adapter"]
        _assert(oauth.get("logical_root") == "company/next-subprojects/web-ai-oauth-adapter", "OAUTH logical-root drift")
        _assert(oauth.get("external_source_root") == r"D:\OAUTH", "OAUTH source-root drift")
        _assert(oauth.get("logical_root") != division.get("logical_root"), "OAUTH must remain separate from Division01")

        by = _task_by_id(graph)
        _assert(by["DIE-104"].get("depends_on") == ["DIE-103"], "DIE-104 dependency drift")
        _assert("DIE-104" in by["DIE-200"].get("depends_on", []), "DIE-200 must depend on DIE-104")
        _assert(by["MX-053"].get("depends_on") == expected_arch["mx053_depends_on"], "MX-053 ordering drift")
        _assert(by[expected_arch["handoff_task"]].get("depends_on") == ["MX-054"], "Architect handoff ordering drift")

        overlay = graph.get("migration_overlay", {})
        _assert(overlay.get("aether_boundary") == contract["aether_boundary"], "Aether overlay drift")
        _assert("NOT Division01" in overlay.get("oauth_boundary", ""), "task graph OAUTH boundary drift")

        for token in [r"C:\aether\aether-ai-os", r"D:\aether-bridge", r"D:\aether-identity", r"D:\state-shared"]:
            _assert(token in disposition, f"Aether disposition missing: {token}")
        _assert(disposition.count("`KEEP_EXTERNAL`") >= 4, "KEEP_EXTERNAL dispositions insufficient")
        return "Architect deferred; OAUTH separate; Aether external; task ordering intact"

    add("migration_boundaries", migration_boundaries)

    def atlas_canon() -> str:
        atlas = root / canonical["human_atlas"]
        _assert(atlas.is_file(), "human Atlas canonical file missing")
        old = canonical["legacy_human_atlas"]
        operational = [
            "COMPANY_BRAIN.md",
            "bridge/income_os_bridge/canon_context.py",
            "bridge/tests/test_runtime_canon_load_contract_v1.py",
            "company/runtime-canon-context-v1.json",
            "company/executive/IDENTITY.md",
            "company/division/division001/IDENTITY.md",
        ]
        bad = []
        for rel in operational:
            text = (root / rel).read_text(encoding="utf-8")
            if old in text or old.replace("/", "\\") in text:
                bad.append(rel)
        _assert(not bad, f"operational legacy Atlas references: {bad}")
        return "Atlas canonical path singular in operational references"

    add("atlas_canon", atlas_canon)

    def validate_snapshot(manifest_rel: str, *, kind: str) -> str:
        manifest_path = root / manifest_rel
        manifest = _load_json(manifest_path)
        _assert(manifest.get("schema") == contract["snapshot_rules"]["schema"], f"wrong {kind} snapshot schema")
        base = manifest_path.parent
        rows = manifest.get("files")
        _assert(isinstance(rows, list) and rows, f"{kind} snapshot files missing")
        listed = set()
        for row in rows:
            rel = row["path"]
            pure = pathlib.PurePosixPath(rel)
            _assert(not pure.is_absolute() and ".." not in pure.parts, f"unsafe {kind} snapshot path: {rel}")
            _assert(rel not in listed, f"duplicate {kind} manifest path: {rel}")
            listed.add(rel)
            path = base / pathlib.Path(*pure.parts)
            _assert(path.is_file(), f"missing {kind} snapshot file: {rel}")
            expected_hash = row.get("imported_sha256") or row.get("sha256")
            _assert(expected_hash and _sha256(path) == expected_hash, f"{kind} imported hash mismatch: {rel}")
        actual = {
            p.relative_to(base).as_posix()
            for p in base.rglob("*")
            if p.is_file() and p.name != "SOURCE_MANIFEST.json"
        }
        _assert(actual == listed, f"{kind} manifest/file-set mismatch: {sorted(actual ^ listed)}")
        if kind == "object":
            _assert(manifest.get("linux_runnable") is contract["snapshot_rules"]["object_linux_runnable"], "object linux_runnable drift")
            defects = manifest.get("excluded_source_defects", [])
            _assert(len(defects) == 1, "object excluded-source-defect record drift")
        if kind == "oauth":
            _assert(manifest.get("source_git_head") == contract["snapshot_rules"]["oauth_source_git_head"], "OAUTH source HEAD drift")
        return f"files={len(rows)}"

    add("object_snapshot", lambda: validate_snapshot(canonical["object_snapshot_manifest"], kind="object"))
    add("oauth_snapshot", lambda: validate_snapshot(canonical["oauth_snapshot_manifest"], kind="oauth"))

    def secret_scan() -> str:
        hits = []
        for rel in tracked:
            if not rel.startswith("company/"):
                continue
            path = root / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                hits.append(rel)
        _assert(not hits, f"high-confidence secret patterns in tracked company files: {hits[:20]}")
        return "high_confidence_secret_hits=0"

    add("company_secret_scan", secret_scan)

    passed = sum(1 for result in results if result.ok)
    failed = [result for result in results if not result.ok]
    payload = {
        "schema": "die.one-canon-validation-result.v1",
        "status": "PASS" if not failed else "FAIL",
        "root": str(root),
        "checks_total": len(results),
        "checks_passed": passed,
        "checks_failed": len(failed),
        "results": [result.__dict__ for result in results],
    }
    return payload


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_one_canon")
    parser.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        payload = validate(pathlib.Path(args.root), require_clean=args.require_clean)
    except Exception as exc:
        payload = {
            "schema": "die.one-canon-validation-result.v1",
            "status": "FAIL",
            "checks_total": 0,
            "checks_passed": 0,
            "checks_failed": 1,
            "results": [{"name": "validator_bootstrap", "ok": False, "detail": f"{type(exc).__name__}: {exc}"}],
        }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(text)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
