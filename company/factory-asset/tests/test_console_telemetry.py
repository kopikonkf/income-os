import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib/console_telemetry.py"
CONSOLE = ROOT / "company/factory-asset/console-prototype"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def topology():
    return {
        "observed_at": "2026-09-10T00:00:00Z",
        "clusters": [
            {
                "cluster_id": "cluster-a",
                "health": "HEALTHY",
                "broker_state": "READY",
                "tab_occupancy": {"open_pages": 1, "max_tabs": 8, "active_leases": 0, "generation_slots_available": 5},
                "provider_sessions": [
                    {"provider_id": p, "readiness": "HEALTHY", "capacity": "AVAILABLE", "active_jobs": []}
                    for p in ("chatgpt", "qwen", "gemini", "manus", "duckai")
                ],
            },
            {
                "cluster_id": "cluster-b",
                "health": "HEALTHY",
                "broker_state": "READY",
                "tab_occupancy": {"open_pages": 1, "max_tabs": 8, "active_leases": 0, "generation_slots_available": 4},
                "provider_sessions": [
                    {"provider_id": p, "readiness": "HEALTHY", "capacity": "AVAILABLE", "active_jobs": []}
                    for p in ("chatgpt", "qwen", "gemini", "manus", "duckai")
                ],
            },
        ],
    }


def queue():
    return {"events": [{"job_id": "a", "state": "READY"}, {"job_id": "b", "state": "RETRY_WAIT"}, {"job_id": "c", "state": "SUCCEEDED"}]}


def test_c018_reports_observable_overall_rates_live_tabs_and_historical_ram():
    d = load(LIB, "telemetry_unit").build_telemetry(repo_root=ROOT, queue_state=queue(), cluster_topology=topology())
    assert d["queue"]["depth"] == 3
    assert d["queue"]["state_counts"] == {"READY": 1, "RETRY_WAIT": 1, "SUCCEEDED": 1}
    assert d["throughput"]["acceptance_run_accepted_masters"] == 100
    assert d["throughput"]["acceptance_run_dispatch_commits"] == 113
    assert d["throughput"]["overall_success_rate_pct"] == 88.5
    assert d["throughput"]["overall_reject_rate_pct"] == 11.5
    assert d["economics"]["observed_spend_usd"] == 0.0
    assert d["economics"]["cost_per_accepted_master_usd"] == 0.0
    assert [(c["active_tabs"], c["generation_slots_available"]) for c in d["clusters"]] == [(1, 5), (1, 4)]
    assert all(c["ram"]["historical_bounded_acceptance"] is True and c["ram"]["historical_after_rss_tree_mb"] != "UNKNOWN" for c in d["clusters"])


def test_unknown_is_explicit_for_unobservable_per_route_rates_live_ram_and_daily_rate():
    d = load(LIB, "telemetry_unknown").build_telemetry(repo_root=ROOT, queue_state=queue(), cluster_topology=topology())
    assert d["throughput"]["generated_masters_per_day"] == "UNKNOWN"
    assert all(c["ram"]["live_rss_tree_mb"] == "UNKNOWN" for c in d["clusters"])
    assert len(d["routes"]) == 10
    assert all(r["success_rate_pct"] == "UNKNOWN" and r["reject_rate_pct"] == "UNKNOWN" and r["attempt_denominator"] == "UNKNOWN" for r in d["routes"])
    by = {r["route_id"]: r for r in d["routes"]}
    assert by["qwen@cluster-a"]["latency_ms"] == 19865
    assert by["gemini@cluster-b"]["latency_ms"] == 26372
    assert by["chatgpt@cluster-a"]["latency_ms"] == "UNKNOWN"


def test_telemetry_payload_is_sanitized_and_read_only():
    d = load(LIB, "telemetry_safe").build_telemetry(repo_root=ROOT, queue_state=queue(), cluster_topology=topology())
    assert d["truth_boundaries"] == {
        "provider_dispatch_performed": False,
        "browser_owner_actions_performed": False,
        "marketplace_actions_performed": False,
        "production_cadence_changed": False,
        "scale_100_per_day_authorized": False,
        "unknown_values_are_not_inferred": True,
    }
    text = json.dumps(d).lower()
    assert "/var/lib/" not in text and "d:\\\\" not in text and "cookie" not in text and "token" not in text and "credential" not in text


def test_telemetry_http_roundtrip_and_ui_unknown_contract():
    m = load(CONSOLE / "server.py", "telemetry_server")
    m.queue_state = queue
    m.cluster_topology_state = topology
    httpd = m.ThreadingHTTPServer(("127.0.0.1", 0), m.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/telemetry", timeout=5) as r:
            d = json.loads(r.read())
        assert d["schema"] == "die.factory-asset.console-telemetry.v1" and len(d["routes"]) == 10
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)
    js = (CONSOLE / "app.js").read_text(encoding="utf-8")
    html = (CONSOLE / "index.html").read_text(encoding="utf-8")
    assert "getLocal('/api/telemetry')" in js and "UNKNOWN is deliberate" in js and "Per-route success/reject rates remain UNKNOWN" in js
    assert 'data-view="telemetry"' in html and 'data-view-panel="telemetry"' in html
