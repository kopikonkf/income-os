from __future__ import annotations

import json
from pathlib import Path
from typing import Any

UNKNOWN = "UNKNOWN"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(numerator: int | float, denominator: int | float) -> float | str:
    if not denominator:
        return UNKNOWN
    return round(float(numerator) * 100.0 / float(denominator), 2)


def build_telemetry(*, repo_root: Path, queue_state: dict[str, Any], cluster_topology: dict[str, Any]) -> dict[str, Any]:
    base = repo_root / "company/factory-asset"
    fa124 = _load(base / "fixtures/scale/FA-124-final-result.json")
    fa307 = _load(base / "fixtures/multi-cluster/FA-307-composite-closure-20260908.json")

    throughput = fa124["throughput"]
    route_counts = fa124["route_counts"]
    storage = fa124["storage_economics"]
    accepted = int(throughput["accepted_masters"])
    dispatches = int(throughput["dispatch_commits"])
    failures = int(throughput["provider_failures_after_commit"])

    historical_topology = fa307["parallel_topology_basis"]["topology"]
    after = historical_topology["after"]["clusters"]
    latency_samples: dict[str, Any] = {}
    for row in fa307.get("current_original_lineage", {}).values():
        route = f"{row.get('provider_id')}@{row.get('cluster_id')}"
        latency_samples[route] = row.get("latency_ms", UNKNOWN)

    live_clusters = {c["cluster_id"]: c for c in cluster_topology.get("clusters", [])}
    clusters = []
    for cluster_id in sorted(live_clusters):
        live = live_clusters[cluster_id]
        tabs = live.get("tab_occupancy", {})
        hist = after.get(cluster_id, {})
        clusters.append({
            "cluster_id": cluster_id,
            "health": live.get("health", UNKNOWN),
            "broker_state": live.get("broker_state", UNKNOWN),
            "active_tabs": tabs.get("open_pages", UNKNOWN),
            "max_tabs": tabs.get("max_tabs", UNKNOWN),
            "active_leases": tabs.get("active_leases", UNKNOWN),
            "generation_slots_available": tabs.get("generation_slots_available", UNKNOWN),
            "ram": {
                "live_rss_tree_mb": UNKNOWN,
                "historical_after_rss_tree_mb": hist.get("rss_tree_mb", UNKNOWN),
                "historical_bounded_acceptance": bool(fa307.get("assertions", {}).get("bounded_ram")),
                "evidence_freshness": "HISTORICAL_FA307_ACCEPTANCE",
            },
        })

    provider_sessions: dict[str, dict[str, Any]] = {}
    for cluster in cluster_topology.get("clusters", []):
        cid = cluster.get("cluster_id")
        for session in cluster.get("provider_sessions", []):
            provider_sessions[f"{session.get('provider_id')}@{cid}"] = session

    routes = []
    for route_id, successes in sorted(route_counts.items()):
        session = provider_sessions.get(route_id, {})
        routes.append({
            "route_id": route_id,
            "accepted_masters": int(successes),
            "success_rate_pct": UNKNOWN,
            "reject_rate_pct": UNKNOWN,
            "attempt_denominator": UNKNOWN,
            "latency_ms": latency_samples.get(route_id, UNKNOWN),
            "latency_evidence": "FA307_ACCEPTED_ORIGINAL_SAMPLE" if route_id in latency_samples else UNKNOWN,
            "health": session.get("readiness", UNKNOWN),
            "capacity": session.get("capacity", UNKNOWN),
            "active_jobs": len(session.get("active_jobs") or []),
            "cost_usd": UNKNOWN,
        })

    queue_events = queue_state.get("events", [])
    state_counts: dict[str, int] = {}
    for row in queue_events:
        state = str(row.get("state", UNKNOWN))
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "schema": "die.factory-asset.console-telemetry.v1",
        "mode": "READ_ONLY_MIXED_EVIDENCE",
        "observed_at": cluster_topology.get("observed_at"),
        "queue": {"depth": len(queue_events), "state_counts": state_counts},
        "throughput": {
            "acceptance_run_accepted_masters": accepted,
            "acceptance_run_dispatch_commits": dispatches,
            "acceptance_run_provider_failures_after_commit": failures,
            "overall_success_rate_pct": _pct(accepted, dispatches),
            "overall_reject_rate_pct": _pct(failures, dispatches),
            "generated_masters_per_day": UNKNOWN,
            "generated_masters_per_day_reason": "NO_BOUNDED_ELAPSED_TIME_WINDOW_IN_CANONICAL_FA124_RESULT",
        },
        "economics": {
            "observed_spend_usd": storage.get("observed_spend_usd", UNKNOWN),
            "accepted_provider_artifact_gib": storage.get("accepted_provider_artifact_gib", UNKNOWN),
            "cost_per_accepted_master_usd": 0.0 if storage.get("observed_spend_usd") == 0 else UNKNOWN,
            "route_level_cost_usd": UNKNOWN,
        },
        "clusters": clusters,
        "routes": routes,
        "historical_bounds": {
            "max_combined_browser_tree_rss_mb": historical_topology.get("max_combined_browser_tree_rss_mb", UNKNOWN),
            "max_active_leases": historical_topology.get("max_active_leases", {}),
            "max_open_pages": historical_topology.get("max_open_pages", {}),
            "bounded_ram": bool(fa307.get("assertions", {}).get("bounded_ram")),
            "bounded_tabs": bool(fa307.get("assertions", {}).get("bounded_tabs")),
        },
        "truth_boundaries": {
            "provider_dispatch_performed": False,
            "browser_owner_actions_performed": False,
            "marketplace_actions_performed": False,
            "production_cadence_changed": False,
            "scale_100_per_day_authorized": False,
            "unknown_values_are_not_inferred": True,
        },
    }
