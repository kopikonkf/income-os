#!/usr/bin/env python3
"""Mechanical conformance checks for the DIE Company Brain registry."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("company/identity-registry.json")
REQUIRED_IDENTITIES = {
    "founder",
    "chatgpt-plus-executive",
    "division-head-template",
    "hermes-operator",
    "worker-template",
}
REQUIRED_GOVERNANCE_PATHS = {
    "company_brain",
    "constitution",
    "agency_contract",
    "canonical_handoff",
}
IDENTITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _safe_file(repo_root: Path, value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: expected a non-empty relative path")
        return None

    if "\\" in value:
        errors.append(f"{label}: use repository-relative POSIX separators")
        return None

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{label}: path must stay inside the repository: {value!r}")
        return None

    root = repo_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label}: resolved outside repository: {value!r}")
        return None

    if not candidate.is_file():
        errors.append(f"{label}: file does not exist: {value!r}")
        return None
    if candidate.stat().st_size == 0:
        errors.append(f"{label}: file is empty: {value!r}")
    return candidate


def validate_registry(repo_root: Path, registry: Any) -> list[str]:
    """Validate a parsed registry. Returns deterministic, human-readable errors."""

    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["registry: top-level JSON value must be an object"]

    if registry.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected '1.0.0'")
    if registry.get("registry_id") != "die.company.identity-registry":
        errors.append("registry_id: unexpected or missing registry id")

    governance = registry.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance: expected an object")
        governance = {}
    for key in sorted(REQUIRED_GOVERNANCE_PATHS):
        _safe_file(repo_root, governance.get(key), f"governance.{key}", errors)

    security = registry.get("security")
    if not isinstance(security, dict):
        errors.append("security: expected an object")
        security = {}

    dev_plane_id = security.get("architect_dev_plane_id")
    if not isinstance(dev_plane_id, str) or not dev_plane_id:
        errors.append("security.architect_dev_plane_id: expected a non-empty id")

    forbidden_raw = security.get("runtime_forbidden_capabilities")
    if not isinstance(forbidden_raw, list) or not forbidden_raw:
        errors.append("security.runtime_forbidden_capabilities: expected a non-empty list")
        forbidden: set[str] = set()
    else:
        forbidden = {item for item in forbidden_raw if isinstance(item, str)}
        if len(forbidden) != len(forbidden_raw):
            errors.append("security.runtime_forbidden_capabilities: values must be unique strings")

    if security.get("runtime_architect_dev_access") != "deny":
        errors.append("security.runtime_architect_dev_access: must be 'deny'")
    if security.get("dev_privilege_inheritance") != "forbidden":
        errors.append("security.dev_privilege_inheritance: must be 'forbidden'")

    identities_raw = registry.get("identities")
    if not isinstance(identities_raw, list):
        errors.append("identities: expected an array")
        identities_raw = []

    identities: dict[str, dict[str, Any]] = {}
    for index, identity in enumerate(identities_raw):
        label = f"identities[{index}]"
        if not isinstance(identity, dict):
            errors.append(f"{label}: expected an object")
            continue

        identity_id = identity.get("id")
        if not isinstance(identity_id, str) or not IDENTITY_ID_RE.fullmatch(identity_id):
            errors.append(f"{label}.id: expected lowercase kebab-case id")
            continue
        if identity_id in identities:
            errors.append(f"{label}.id: duplicate identity {identity_id!r}")
            continue
        identities[identity_id] = identity

        for field in ("kind", "scope"):
            if not isinstance(identity.get(field), str) or not identity[field]:
                errors.append(f"{label}.{field}: expected a non-empty string")
        for field in ("runtime", "template"):
            if not isinstance(identity.get(field), bool):
                errors.append(f"{label}.{field}: expected a boolean")

        _safe_file(repo_root, identity.get("document"), f"{label}.document", errors)

        inheritance = identity.get("inherits_identity_ids")
        if not isinstance(inheritance, list) or any(not isinstance(item, str) for item in inheritance):
            errors.append(f"{label}.inherits_identity_ids: expected an array of identity ids")

        capabilities = identity.get("capabilities")
        if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
            errors.append(f"{label}.capabilities: expected an array of capability strings")
        elif len(set(capabilities)) != len(capabilities):
            errors.append(f"{label}.capabilities: duplicate capability")

        if identity.get("runtime") is True and identity.get("architect_dev_access") != "deny":
            errors.append(f"{identity_id}: runtime identity must set architect_dev_access='deny'")

    missing = sorted(REQUIRED_IDENTITIES - set(identities))
    if missing:
        errors.append(f"identities: missing required ids: {', '.join(missing)}")

    development_planes_raw = registry.get("development_planes")
    if not isinstance(development_planes_raw, list) or not development_planes_raw:
        errors.append("development_planes: expected a non-empty array")
        development_planes_raw = []

    development_plane_ids: set[str] = set()
    for index, plane in enumerate(development_planes_raw):
        label = f"development_planes[{index}]"
        if not isinstance(plane, dict):
            errors.append(f"{label}: expected an object")
            continue
        plane_id = plane.get("id")
        if not isinstance(plane_id, str) or not plane_id:
            errors.append(f"{label}.id: expected a non-empty string")
            continue
        if plane_id in development_plane_ids:
            errors.append(f"{label}.id: duplicate development plane {plane_id!r}")
        development_plane_ids.add(plane_id)
        if plane.get("runtime") is not False:
            errors.append(f"{plane_id}: development plane must not be runtime")
        if plane.get("founder_invoked") is not True:
            errors.append(f"{plane_id}: development plane must be Founder-invoked")
        if plane.get("not_inheritable") is not True:
            errors.append(f"{plane_id}: development plane must be non-inheritable")
        capabilities = plane.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append(f"{plane_id}: development plane needs explicit capabilities")

    if dev_plane_id and dev_plane_id not in development_plane_ids:
        errors.append("security.architect_dev_plane_id: id is not registered in development_planes")

    effective_cache: dict[str, set[str]] = {}

    def effective_capabilities(identity_id: str, trail: tuple[str, ...] = ()) -> set[str]:
        if identity_id in effective_cache:
            return effective_cache[identity_id]
        if identity_id in trail:
            errors.append(f"{identity_id}: identity inheritance cycle detected")
            return set()

        identity = identities[identity_id]
        capabilities = {
            item for item in identity.get("capabilities", []) if isinstance(item, str)
        }
        parents = identity.get("inherits_identity_ids", [])
        if not isinstance(parents, list):
            parents = []

        for parent_id in parents:
            if not isinstance(parent_id, str):
                continue
            if parent_id in development_plane_ids:
                errors.append(
                    f"{identity_id}: cannot inherit non-inheritable development plane {parent_id!r}"
                )
                continue
            if parent_id not in identities:
                errors.append(f"{identity_id}: inherited identity not found: {parent_id!r}")
                continue
            capabilities.update(effective_capabilities(parent_id, trail + (identity_id,)))

        effective_cache[identity_id] = capabilities
        return capabilities

    for identity_id, identity in identities.items():
        effective = effective_capabilities(identity_id)
        if identity.get("runtime") is True:
            leaked = sorted(effective & forbidden)
            if leaked:
                errors.append(
                    f"{identity_id}: runtime identity has DEV-reserved capabilities: {', '.join(leaked)}"
                )

    services_raw = registry.get("services")
    if not isinstance(services_raw, list):
        errors.append("services: expected an array")
        services_raw = []
    sole_writers = [
        service
        for service in services_raw
        if isinstance(service, dict) and service.get("sole_physical_writer") is True
    ]
    expected_writer = governance.get("canonical_state_writer")
    if len(sole_writers) != 1:
        errors.append("services: exactly one sole physical writer is required")
    elif sole_writers[0].get("id") != expected_writer:
        errors.append("services: sole physical writer must match governance.canonical_state_writer")

    control_plane = governance.get("operational_control_plane")
    if control_plane not in identities:
        errors.append("governance.operational_control_plane: identity is not registered")

    return errors


def validate(repo_root: Path) -> list[str]:
    registry_file = repo_root / REGISTRY_PATH
    if not registry_file.is_file():
        return [f"registry: file does not exist: {REGISTRY_PATH.as_posix()}"]
    try:
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"registry: cannot load JSON: {exc}"]
    return validate_registry(repo_root, registry)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors = validate(repo_root)
    if errors:
        print(json.dumps({"status": "fail", "errors": errors}, indent=2))
        return 1

    registry = json.loads((repo_root / REGISTRY_PATH).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": "pass",
                "registry": REGISTRY_PATH.as_posix(),
                "identity_count": len(registry["identities"]),
                "runtime_identity_count": sum(
                    identity["runtime"] for identity in registry["identities"]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
