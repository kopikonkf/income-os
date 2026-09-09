from __future__ import annotations

from typing import Any

_FORBIDDEN = {"cookie","cookies","token","tokens","access_token","refresh_token","authorization","oauth","session_key","session_bytes","credentials","credential","browser_profile_path"}


def _scan(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _FORBIDDEN:
                raise ValueError(f"WORKER_REGISTRY_SECRET_MATERIAL_FORBIDDEN:{path}.{k}")
            _scan(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan(item, f"{path}[{i}]")


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(registry, dict) or registry.get("schema_version") != "die.h03.provider-worker-registry.v1" or registry.get("holding_id") != "H03":
        raise ValueError("WORKER_REGISTRY_SCHEMA_INVALID")
    providers = registry.get("providers")
    if not isinstance(providers, list) or not providers:
        raise ValueError("WORKER_REGISTRY_PROVIDERS_REQUIRED")
    ids: set[str] = set()
    for provider in providers:
        if not isinstance(provider, dict) or not provider.get("provider_id") or not provider.get("model_route"):
            raise ValueError("WORKER_REGISTRY_PROVIDER_INVALID")
        pid = provider["provider_id"]
        if pid in ids:
            raise ValueError("WORKER_REGISTRY_PROVIDER_DUPLICATE")
        ids.add(pid)
        if not provider.get("roles") or not isinstance(provider.get("roles"), list):
            raise ValueError("WORKER_REGISTRY_ROLES_REQUIRED")
        if not isinstance(provider.get("capabilities"), list) or not isinstance(provider.get("transport_families"), list):
            raise ValueError("WORKER_REGISTRY_CAPABILITIES_INVALID")
        if not isinstance(provider.get("priority"), int):
            raise ValueError("WORKER_REGISTRY_PRIORITY_INVALID")
    _scan(registry)
    return registry


def route_worker(*, role: str, registry: dict[str, Any], runtime_status: dict[str, dict[str, Any]], required_capabilities: list[str] | None = None) -> dict[str, Any]:
    validate_registry(registry)
    required = set(required_capabilities or [])
    eligible: list[dict[str, Any]] = []
    for provider in registry["providers"]:
        if role not in provider["roles"]:
            continue
        if not required.issubset(set(provider["capabilities"])):
            continue
        status = runtime_status.get(provider["provider_id"], {})
        if status.get("state") != "READY":
            continue
        slots = status.get("available_slots")
        if not isinstance(slots, int) or slots <= 0:
            continue
        shard_id = status.get("profile_shard_id")
        if shard_id is not None and (not isinstance(shard_id, str) or not shard_id.strip()):
            raise ValueError("WORKER_RUNTIME_SHARD_INVALID")
        eligible.append({
            "provider_id": provider["provider_id"],
            "model_route": provider["model_route"],
            "priority": provider["priority"],
            "profile_shard_id": shard_id,
            "transport_families": list(provider["transport_families"]),
            "available_slots": slots
        })
    if not eligible:
        raise RuntimeError("NO_ELIGIBLE_WORKER_SLOT")
    eligible.sort(key=lambda x: (-x["priority"], -x["available_slots"], x["provider_id"]))
    return eligible[0]
