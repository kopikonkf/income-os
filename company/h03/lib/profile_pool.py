from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import worker_router

SCHEMA = "die.h03.browser-profile-pool.v1"
_FORBIDDEN = {"cookie","cookies","token","tokens","access_token","refresh_token","authorization","oauth","session_key","session_bytes","credentials","credential","profile_path","browser_profile_path","user_data_dir"}


def _scan(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _FORBIDDEN:
                raise ValueError(f"PROFILE_POOL_SECRET_OR_PATH_FORBIDDEN:{path}.{k}")
            _scan(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan(item, f"{path}[{i}]")


def validate_profile_pool(pool: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pool, dict) or pool.get("schema_version") != SCHEMA or pool.get("holding_id") != "H03":
        raise ValueError("PROFILE_POOL_SCHEMA_INVALID")
    if pool.get("purpose") not in {"KNOWLEDGE_WORKFORCE","GROWTH_WORKFORCE"} or pool.get("session_material_policy") != "HOST_LOCAL_NOT_PRODUCT_TRUTH":
        raise ValueError("PROFILE_POOL_POLICY_INVALID")
    shards = pool.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("PROFILE_POOL_SHARDS_REQUIRED")
    seen: set[str] = set()
    for shard in shards:
        if not isinstance(shard, dict) or not shard.get("shard_id") or shard.get("state") not in {"READY","DEGRADED","UNAVAILABLE","UNKNOWN"}:
            raise ValueError("PROFILE_POOL_SHARD_INVALID")
        if shard["shard_id"] in seen:
            raise ValueError("PROFILE_POOL_SHARD_DUPLICATE")
        seen.add(shard["shard_id"])
        providers = shard.get("providers")
        if not isinstance(providers, list):
            raise ValueError("PROFILE_POOL_PROVIDERS_INVALID")
        for p in providers:
            if not isinstance(p, dict) or not p.get("provider_id") or p.get("state") not in {"READY","DEGRADED","UNAVAILABLE","AUTH_REQUIRED","RATE_LIMITED","UNKNOWN"}:
                raise ValueError("PROFILE_POOL_PROVIDER_INVALID")
            if not isinstance(p.get("available_slots"), int) or p["available_slots"] < 0:
                raise ValueError("PROFILE_POOL_SLOTS_INVALID")
            if p.get("transport_family") not in {"SESSION_API","BROWSER_CDP","OPENAI_COMPATIBLE"}:
                raise ValueError("PROFILE_POOL_TRANSPORT_INVALID")
    _scan(pool)
    return pool


def aggregate_runtime_status(pool: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_profile_pool(pool)
    best: dict[str, dict[str, Any]] = {}
    for shard in pool["shards"]:
        if shard["state"] not in {"READY","DEGRADED"}:
            continue
        for provider in shard["providers"]:
            pid = provider["provider_id"]
            state = provider["state"]
            slots = provider["available_slots"] if state == "READY" else 0
            candidate = {"state":"READY" if slots > 0 else state,"available_slots":slots,"profile_shard_id":shard["shard_id"]}
            current = best.get(pid)
            if current is None or candidate["available_slots"] > current.get("available_slots", 0):
                best[pid] = candidate
    return best


def route_worker_from_pool(*, role: str, registry: dict[str, Any], pool: dict[str, Any], required_capabilities: list[str] | None = None) -> dict[str, Any]:
    status = aggregate_runtime_status(pool)
    return worker_router.route_worker(role=role, registry=registry, runtime_status=status, required_capabilities=required_capabilities)
