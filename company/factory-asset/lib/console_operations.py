from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED"}
ACTIVE_STATES = {"READY", "RUNNING", "PAUSED", "RETRY_WAIT"}
SCHEDULABLE_READINESS = {"HEALTHY"}
SCHEDULABLE_CAPACITY = {"AVAILABLE"}
_PROVIDER_ORDER = {"qwen": 0, "chatgpt": 1, "gemini": 2, "manus": 3, "duckai": 4}
_TRANSPORT_ORDER = {"SESSION_API": 0, "BROWSER_CDP": 1}


def _safe_queue_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": str(row.get("job_id") or "UNKNOWN"),
        "label": str(row.get("label") or ""),
        "blueprint_id": str(row.get("blueprint_id") or "UNKNOWN"),
        "semantic_asset_id": str(row.get("semantic_asset_id") or "UNKNOWN"),
        "state": str(row.get("state") or "UNKNOWN"),
        "attempts": int(row.get("attempts") or 0),
        "retries": int(row.get("retries") or 0),
        "recovery_count": int(row.get("recovery_count") or 0),
        "failure_code": row.get("failure_code") if row.get("failure_code") else None,
    }


def _cluster_index(topology: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    for raw in topology.get("clusters", []):
        cluster_id = str(raw.get("cluster_id") or "UNKNOWN")
        sessions = {str(p.get("provider_id")): p for p in raw.get("provider_sessions", [])}
        index[cluster_id] = {"cluster": raw, "sessions": sessions}
        tabs = raw.get("tab_occupancy") or {}
        summaries.append(
            {
                "cluster_id": cluster_id,
                "health": str(raw.get("health") or "UNKNOWN"),
                "broker_state": str(raw.get("broker_state") or "UNKNOWN"),
                "open_pages": int(tabs.get("open_pages") or 0),
                "max_tabs": int(tabs.get("max_tabs") or 0),
                "active_leases": int(tabs.get("active_leases") or 0),
                "generation_slots_available": int(tabs.get("generation_slots_available") or 0),
            }
        )
    return index, summaries


def _routes(provider_dashboard: dict[str, Any], cluster_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Build cluster-keyed route previews from sanitized live topology.

    Provider dashboard rows are authoritative enrichments only when they carry an
    explicit cluster_id. Standalone Console mirrors can legitimately fall back to
    the older provider-level synthetic dashboard; those unclustered rows must never
    erase healthy provider+cluster identity already proven by live broker topology.
    """
    dashboard_by_route: dict[tuple[str, str], dict[str, Any]] = {}
    for provider in provider_dashboard.get("providers", []):
        provider_id = str(provider.get("provider_id") or "")
        cluster_id = str(provider.get("cluster_id") or "")
        if provider_id and cluster_id and cluster_id != "UNKNOWN":
            dashboard_by_route[(provider_id, cluster_id)] = provider

    routes: list[dict[str, Any]] = []
    for cluster_id, cluster_entry in cluster_index.items():
        cluster = cluster_entry.get("cluster") or {}
        sessions = cluster_entry.get("sessions") or {}
        for provider_id, session in sessions.items():
            if session.get("membership") != "ACTIVE":
                continue
            provider = dashboard_by_route.get((provider_id, cluster_id))
            readiness = str(session.get("readiness") or "UNKNOWN")
            capacity = str(session.get("capacity") or "UNKNOWN")
            transport = str(session.get("preferred_transport") or "UNKNOWN")
            reasons: list[str] = []
            if cluster.get("health") != "HEALTHY":
                reasons.append("CLUSTER_NOT_HEALTHY")
            if readiness not in SCHEDULABLE_READINESS:
                reasons.append(f"READINESS_{readiness}")
            if capacity not in SCHEDULABLE_CAPACITY:
                reasons.append(f"CAPACITY_{capacity}")
            if provider is not None:
                if provider.get("eligibility") not in {None, "ELIGIBLE"}:
                    reasons.append("PROVIDER_DASHBOARD_NOT_ELIGIBLE")
                if provider.get("health") not in {None, "HEALTHY"}:
                    reasons.append("PROVIDER_DASHBOARD_NOT_HEALTHY")
                if provider.get("capacity") not in {None, "AVAILABLE"}:
                    reasons.append("PROVIDER_DASHBOARD_NO_CAPACITY")
            routes.append(
                {
                    "provider_id": provider_id,
                    "cluster_id": cluster_id,
                    "transport": transport,
                    "readiness": readiness,
                    "capacity": capacity,
                    "schedulable": not reasons,
                    "reasons": reasons,
                }
            )
    routes.sort(
        key=lambda r: (
            0 if r["schedulable"] else 1,
            _TRANSPORT_ORDER.get(r["transport"], 9),
            _PROVIDER_ORDER.get(r["provider_id"], 99),
            r["cluster_id"],
        )
    )
    return routes


def build_operations_state(
    *,
    queue_state: dict[str, Any],
    cluster_topology: dict[str, Any],
    provider_dashboard: dict[str, Any],
) -> dict[str, Any]:
    """Compose the Console operations surface from already-sanitized read models.

    This function never performs routing, dispatch, browser ownership, provider calls,
    or credential/session access. `selected_route` is explicitly a capacity/readiness
    preview for Founder inspection, not a dispatch commitment.
    """
    events = [_safe_queue_row(row) for row in queue_state.get("events", [])]
    counts = Counter(row["state"] for row in events)
    cluster_index, clusters = _cluster_index(cluster_topology)
    routes = _routes(provider_dashboard, cluster_index)
    selected = next((deepcopy(row) for row in routes if row["schedulable"]), None)
    if selected is not None:
        selected.update(
            {
                "selection_basis": "SANITIZED_READINESS_CAPACITY_PREVIEW",
                "dispatch_committed": False,
                "provider_call_performed": False,
            }
        )

    active_jobs = sum(counts[state] for state in ACTIVE_STATES)
    runnable_jobs = counts["READY"] + counts["RETRY_WAIT"]
    generation_slots = sum(row["generation_slots_available"] for row in clusters if row["health"] == "HEALTHY")
    schedulable_routes = sum(1 for row in routes if row["schedulable"])
    blocked_routes = len(routes) - schedulable_routes
    if runnable_jobs and schedulable_routes == 0:
        pressure_state = "BLOCKED"
    elif runnable_jobs > generation_slots and not any(row["schedulable"] and row["transport"] == "SESSION_API" for row in routes):
        pressure_state = "BACKPRESSURE"
    else:
        pressure_state = "CLEAR"

    reconciliation = [str(x) for x in queue_state.get("reconciliation_required_job_ids", [])]
    return {
        "schema": "die.factory-asset.console-operations.v1",
        "evidence_mode": "LIVE_SANITIZED_COMPOSITE" if cluster_topology.get("evidence_mode") == "LIVE_BROKER_SANITIZED" else "SANITIZED_COMPOSITE",
        "observed_at": cluster_topology.get("observed_at") or provider_dashboard.get("observed_at") or "UNKNOWN",
        "queue": {
            "depth": len(events),
            "active_jobs": active_jobs,
            "ready": counts["READY"],
            "running": counts["RUNNING"],
            "paused": counts["PAUSED"],
            "retry_wait": counts["RETRY_WAIT"],
            "terminal": sum(counts[state] for state in TERMINAL_STATES),
            "retries_used": sum(row["retries"] for row in events),
            "reconciliation_required": len(reconciliation),
            "jobs": events,
        },
        "routing": {
            "selected_route": selected,
            "candidate_count": len(routes),
            "schedulable_route_count": schedulable_routes,
            "routes": routes,
            "dispatch_authority": "LOCKED",
            "provider_dispatch_performed": False,
        },
        "backpressure": {
            "state": pressure_state,
            "runnable_jobs": runnable_jobs,
            "browser_generation_slots_available": generation_slots,
            "schedulable_routes": schedulable_routes,
            "blocked_or_busy_routes": blocked_routes,
        },
        "clusters": clusters,
        "controls": {
            "allowed_actions": ["START", "PAUSE", "RESUME", "CANCEL", "RETRY"],
            "provider_dispatch_performed": False,
            "browser_owner_actions_performed": False,
            "marketplace_actions_performed": False,
        },
        "secret_material_exposed": False,
    }
