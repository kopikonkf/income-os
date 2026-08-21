"""Registry-backed authorization for semantic DIE actions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

ACTION_CAPABILITIES = {
    # v1 is Executive-only. Division observation stays closed until a
    # division-scoped projection filter and registered instance exist.
    "context.snapshot.read": {
        "semantic_observation",
    },
    "state.decision.submit": {
        "bounded_decision",
        "northstar_ratification",
    },
    "state.evidence.submit": {
        "evidence_submission",
        "evidence_capture",
    },
    "state.event.submit": {
        "semantic_state_request",
    },
}


class AuthorizationError(ValueError):
    """A deterministic deny result, safe to expose through a semantic API."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path is not None else config.IDENTITY_REGISTRY
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationError(
            "E_REGISTRY_UNAVAILABLE",
            f"identity registry unavailable or invalid: {exc}",
        ) from exc
    if registry.get("registry_id") != "die.company.identity-registry":
        raise AuthorizationError("E_REGISTRY_INVALID", "unexpected identity registry")
    return registry


def _effective_capabilities(
    identity_id: str,
    identities: dict[str, dict[str, Any]],
    development_plane_ids: set[str],
    trail: tuple[str, ...] = (),
) -> set[str]:
    if identity_id in trail:
        raise AuthorizationError("E_REGISTRY_INVALID", "identity inheritance cycle")

    identity = identities[identity_id]
    capabilities = {
        item for item in identity.get("capabilities", []) if isinstance(item, str)
    }
    for parent_id in identity.get("inherits_identity_ids", []):
        if parent_id in development_plane_ids:
            raise AuthorizationError(
                "E_DEV_PRIVILEGE_DENIED",
                f"identity cannot inherit development plane {parent_id!r}",
            )
        if parent_id not in identities:
            raise AuthorizationError(
                "E_REGISTRY_INVALID",
                f"inherited identity not registered: {parent_id!r}",
            )
        capabilities.update(
            _effective_capabilities(
                parent_id,
                identities,
                development_plane_ids,
                trail + (identity_id,),
            )
        )
    return capabilities


def authorize(
    principal_id: str,
    action: str,
    requested_scope: str | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve one registered principal and return its bounded authority."""

    registry = load_registry(registry_path)
    identities = {
        item["id"]: item
        for item in registry.get("identities", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    identity = identities.get(principal_id)
    if identity is None:
        raise AuthorizationError(
            "E_UNAUTHORIZED_PRINCIPAL",
            f"principal is not registered: {principal_id!r}",
        )
    if identity.get("template") is True:
        raise AuthorizationError(
            "E_UNINSTANTIATED_TEMPLATE",
            f"identity template cannot act directly: {principal_id!r}",
        )
    if identity.get("architect_dev_access") != "deny":
        raise AuthorizationError(
            "E_DEV_PRIVILEGE_DENIED",
            "semantic principal must explicitly deny Architect DEV access",
        )

    requirements = ACTION_CAPABILITIES.get(action)
    if requirements is None:
        raise AuthorizationError(
            "E_UNSUPPORTED_ACTION",
            f"semantic action is not supported: {action!r}",
        )

    development_plane_ids = {
        item["id"]
        for item in registry.get("development_planes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    effective = _effective_capabilities(
        principal_id,
        identities,
        development_plane_ids,
    )

    forbidden = set(
        registry.get("security", {}).get("runtime_forbidden_capabilities", [])
    )
    if identity.get("runtime") is True and effective & forbidden:
        raise AuthorizationError(
            "E_DEV_PRIVILEGE_DENIED",
            "runtime principal contains a DEV-reserved capability",
        )

    matched = sorted(effective & requirements)
    if not matched:
        raise AuthorizationError(
            "E_FORBIDDEN_ACTION",
            f"principal {principal_id!r} lacks authority for {action!r}",
        )

    registered_scope = identity.get("scope")
    scope = requested_scope or registered_scope
    if scope != registered_scope:
        raise AuthorizationError(
            "E_SCOPE_DENIED",
            f"requested scope {scope!r} exceeds registered scope {registered_scope!r}",
        )

    return {
        "principal_id": principal_id,
        "identity_id": identity["id"],
        "kind": identity.get("kind"),
        "scope": scope,
        "action": action,
        "capability": matched[0],
        "authority_source": "company/identity-registry.json",
    }
