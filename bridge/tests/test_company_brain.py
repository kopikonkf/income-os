"""Conformance tests for Company Brain identity and privilege boundaries."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "bin" / "die_company_brain_check.py"
REGISTRY_PATH = REPO_ROOT / "company" / "identity-registry.json"

SPEC = importlib.util.spec_from_file_location("die_company_brain_check", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def identity(registry: dict, identity_id: str) -> dict:
    return next(item for item in registry["identities"] if item["id"] == identity_id)


def test_company_brain_registry_conforms() -> None:
    assert VALIDATOR.validate(REPO_ROOT) == []


def test_every_registered_identity_resolves_to_nonempty_repo_document() -> None:
    root = REPO_ROOT.resolve()
    for item in load_registry()["identities"]:
        document = (root / item["document"]).resolve()
        document.relative_to(root)
        assert document.is_file(), item["id"]
        assert document.stat().st_size > 0, item["id"]


def test_every_runtime_identity_explicitly_denies_architect_dev_access() -> None:
    registry = load_registry()
    assert registry["security"]["runtime_architect_dev_access"] == "deny"
    for item in registry["identities"]:
        if item["runtime"]:
            assert item["architect_dev_access"] == "deny", item["id"]


def test_validator_rejects_runtime_architect_dev_access() -> None:
    registry = load_registry()
    identity(registry, "chatgpt-plus-executive")["architect_dev_access"] = "allow"

    errors = VALIDATOR.validate_registry(REPO_ROOT, registry)

    assert any("runtime identity must set architect_dev_access='deny'" in error for error in errors)


def test_validator_rejects_runtime_dev_capability() -> None:
    registry = load_registry()
    identity(registry, "division-head-template")["capabilities"].append("git_write")

    errors = VALIDATOR.validate_registry(REPO_ROOT, registry)

    assert any("DEV-reserved capabilities: git_write" in error for error in errors)


def test_validator_rejects_development_plane_inheritance() -> None:
    registry = load_registry()
    identity(registry, "hermes-operator")["inherits_identity_ids"].append(
        registry["security"]["architect_dev_plane_id"]
    )

    errors = VALIDATOR.validate_registry(REPO_ROOT, registry)

    assert any("cannot inherit non-inheritable development plane" in error for error in errors)


def test_validator_rejects_indirect_dev_capability_inheritance() -> None:
    registry = load_registry()
    poison_parent = copy.deepcopy(identity(registry, "founder"))
    poison_parent.update(
        {
            "id": "poison-parent",
            "runtime": False,
            "capabilities": ["service_control"],
        }
    )
    registry["identities"].append(poison_parent)
    identity(registry, "worker-template")["inherits_identity_ids"].append("poison-parent")

    errors = VALIDATOR.validate_registry(REPO_ROOT, registry)

    assert any("DEV-reserved capabilities: service_control" in error for error in errors)
