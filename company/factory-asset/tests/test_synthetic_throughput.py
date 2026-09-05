import importlib.util
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
s = importlib.util.spec_from_file_location(
    "fa120_synth",
    R / "company/factory-asset/lib/synthetic_throughput.py",
)
m = importlib.util.module_from_spec(s)
sys.modules[s.name] = m
assert s and s.loader
s.loader.exec_module(m)


def test_fa120_thousands_backpressure_acceptance(tmp_path):
    result = m.run_synthetic_throughput_acceptance(tmp_path)
    assert result["result"] == "PASS"
    assert result["provider_calls_performed"] is False
    assert result["queue"]["unique_jobs"] == 5000
    assert result["queue"]["terminal_successes"] == 5000
    assert result["queue"]["terminal_failures"] == 0
    assert result["queue"]["peak_active_depth"] <= 256
    assert result["queue"]["admission_backpressure_events"] > 0
    assert result["fairness"]["violations"] == 0
    assert max(result["fairness"]["completion_counts"].values()) - min(result["fairness"]["completion_counts"].values()) <= 1
    assert result["leases"]["contention_blocked"] >= 1
    assert result["leases"]["active_after_run"] == 0
    assert result["retries"]["retry_events"] > 0
    assert result["retries"]["max_retries_per_job"] <= 2
    assert result["dedupe"]["duplicate_submissions"] > 0
    assert result["dedupe"]["duplicate_reused"] == result["dedupe"]["duplicate_submissions"]
    assert result["dedupe"]["idempotency_conflicts_blocked"] == 1
    assert result["restart"]["performed"] is True
    assert result["restart"]["recovered_jobs"] > 0
    assert result["restart"]["max_recovery_count"] == 1
    assert result["disk_backpressure"]["events"] > 0
    assert result["disk_backpressure"]["resume_events"] == result["disk_backpressure"]["events"]
    assert result["disk_backpressure"]["peak_bytes"] <= result["disk_backpressure"]["high_watermark_bytes"]
    assert all(result["assertions"].values())


def test_config_rejects_non_thousand_scale(tmp_path):
    bad = m.HarnessConfig(unique_jobs=1999, restart_after_successes=1000)
    try:
        m.run_synthetic_throughput_acceptance(tmp_path, config=bad)
    except ValueError as exc:
        assert "thousands" in str(exc)
    else:
        raise AssertionError("small run should not satisfy FA-120 acceptance config")


def test_harness_source_has_no_provider_or_network_client_imports():
    source = (R / "company/factory-asset/lib/synthetic_throughput.py").read_text(encoding="utf-8")
    forbidden = (
        "requests",
        "httpx",
        "urllib.request",
        "socket.create_connection",
        "subprocess.run",
        "providers/",
        "cluster_broker",
        "provider_readiness",
    )
    for token in forbidden:
        assert token not in source
