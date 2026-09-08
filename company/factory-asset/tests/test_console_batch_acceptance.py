from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
CONSOLE = ROOT / "company/factory-asset/console-prototype"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from console_batch_acceptance import run_console_batch_acceptance  # noqa: E402


def load_server():
    spec = importlib.util.spec_from_file_location("console_c011_server", CONSOLE / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fa_c011_direct_batch_acceptance_passes(tmp_path):
    result = run_console_batch_acceptance(tmp_path)
    assert result["result"] == "PASS"
    assert result["source_surface"] == "FACTORY_CONSOLE"
    assert result["provider_calls_performed"] is False
    assert result["queue"]["peak_concurrent_running"] == 3
    assert result["queue"]["worker_slot_limit"] == 3
    assert result["queue"]["backpressure_events"] > 0
    assert result["queue"]["succeeded"] == 11
    assert result["queue"]["failed"] == 1
    assert result["routing"]["route_counts"] == {"chatgpt": 6, "qwen": 6}
    assert all(result["assertions"].values())


def test_fa_c011_pause_resume_retry_and_partial_failure_are_contained(tmp_path):
    result = run_console_batch_acceptance(tmp_path)
    controls = result["controls"]
    assert controls["pause_events"] == 1
    assert controls["resume_events"] == 1
    assert controls["retry_events"] == 1
    assert controls["terminal_partial_failures"] == 1
    assert controls["succeeded_after_terminal_failure"] > 0
    assert result["queue"]["max_retries_per_job"] == 1
    assert result["assertions"]["partial_failures_contained"] is True
    assert result["assertions"]["queue_progress"] is True


def test_fa_c011_dedupe_ownership_and_semantic_count_integrity(tmp_path):
    result = run_console_batch_acceptance(tmp_path)
    ownership = result["ownership_and_dedupe"]
    semantics = result["semantic_integrity"]
    assert ownership == {
        "duplicate_ownership_blocked": 1,
        "duplicate_submissions": 3,
        "duplicate_reuses": 3,
        "idempotency_conflicts_blocked": 1,
    }
    assert semantics["expected_semantic_assets"] == 12
    assert semantics["unique_semantic_assets"] == 12
    assert semantics["terminal_jobs"] == 12
    assert semantics["total_attempts"] > 12
    assert semantics["attempts_do_not_count_as_semantic_assets"] is True
    assert semantics["duplicates_do_not_count_as_semantic_assets"] is True
    assert semantics["partial_failure_does_not_create_replacement_semantic_asset"] is True


def test_fa_c011_writes_durable_console_state_timeline_and_final(tmp_path):
    result = run_console_batch_acceptance(tmp_path)
    paths = {key: Path(value) for key, value in result["evidence_paths"].items()}
    assert all(path.is_file() for path in paths.values())
    state = json.loads(paths["console_state"].read_text(encoding="utf-8"))
    timeline = json.loads(paths["timeline"].read_text(encoding="utf-8"))
    final = json.loads(paths["final_result"].read_text(encoding="utf-8"))
    assert state["phase"] == "TERMINAL"
    assert state["semantic_asset_count"] == 12
    assert state["provider_calls_performed"] is False
    assert len(timeline["events"]) >= 8
    assert max(event["states"]["RUNNING"] for event in timeline["events"]) == 3
    assert final["result"] == "PASS"


def test_fa_c011_console_http_roundtrip(tmp_path):
    server = load_server()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({"schema": "die.factory-asset.console-batch-acceptance-request.v1"}).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_port}/api/synthetic/batch-acceptance",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
        assert result["result"] == "PASS"
        assert result["provider_calls_performed"] is False
        assert result["queue"]["peak_concurrent_running"] == 3
        assert result["semantic_integrity"]["unique_semantic_assets"] == 12
        assert "evidence_paths" not in result
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_fa_c011_http_rejects_wrong_request_envelope():
    server = load_server()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({"schema": "wrong"}).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_port}/api/synthetic/batch-acceptance",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=10)
            raise AssertionError("wrong request envelope must fail")
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read())
            assert exc.code == 400
            assert payload["code"] == "INVALID_SYNTHETIC_BATCH_ACCEPTANCE_REQUEST"
            assert payload["dispatch_performed"] is False
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_fa_c011_response_contains_no_secret_or_provider_wire_material(tmp_path):
    text = json.dumps(run_console_batch_acceptance(tmp_path)).lower()
    for marker in (
        "session_token",
        "access_token",
        "refresh_token",
        '"cookie":',
        '"cookies":',
        '"set-cookie"',
        "rpc_id",
        "cdp_url",
        "browser_profile",
        "raw_auth_body",
        "playwright",
        "websocket",
    ):
        assert marker not in text

