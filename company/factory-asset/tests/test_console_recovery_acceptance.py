from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
CONSOLE = ROOT / "company/factory-asset/console-prototype"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from console_recovery_acceptance import (  # noqa: E402
    build_precrash_queue,
    build_recovery_snapshot,
    load_and_reconcile,
    persist_recovery_snapshot,
    run_console_recovery_acceptance,
)


def load_server(name: str):
    spec = importlib.util.spec_from_file_location(name, CONSOLE / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def command(job_id: str, action: str, suffix: str = "001") -> dict:
    return {
        "schema": "die.factory-asset.console-api.v1",
        "kind": "CONTROL_COMMAND",
        "command_id": f"c012-{suffix}-{action.lower()}",
        "job_id": job_id,
        "action": action,
    }


def test_fa_c012_direct_recovery_acceptance_passes(tmp_path):
    result = run_console_recovery_acceptance(tmp_path)
    assert result["result"] == "PASS"
    assert result["provider_calls_performed"] is False
    assert result["browser_owner_actions"] == 0
    assert result["duplicate_dispatch_blocked"] is True
    assert result["reconciliation_required_job_ids"] == ["FCJOB-FA-C012-RUNNING-COMMITTED"]
    assert all(result["assertions"].values())


def test_fa_c012_precommit_running_recovers_ready_but_committed_dispatch_is_fenced(tmp_path):
    q = build_precrash_queue()
    snapshot = build_recovery_snapshot(q)
    path = tmp_path / "snapshot.json"
    persist_recovery_snapshot(path, snapshot)
    recovered, manifest = load_and_reconcile(path)
    uncommitted = recovered.get("FCJOB-FA-C012-RUNNING-UNCOMMITTED")
    committed = recovered.get("FCJOB-FA-C012-RUNNING-COMMITTED")
    assert uncommitted.state == "READY"
    assert uncommitted.recovery_count == 1
    assert uncommitted.owner is None and uncommitted.lease_token is None
    assert committed.state == "PAUSED"
    assert committed.failure_code == "DISPATCH_RECONCILIATION_REQUIRED"
    assert committed.recovery_count == 1
    assert manifest["reconciliation_required_job_ids"] == [committed.job_id]


def test_fa_c012_success_pause_retry_truth_survives_restart(tmp_path):
    q = build_precrash_queue()
    before = {row["job_id"]: row for row in q.list()}
    path = tmp_path / "snapshot.json"
    persist_recovery_snapshot(path, build_recovery_snapshot(q))
    recovered, _ = load_and_reconcile(path)
    after = {row["job_id"]: row for row in recovered.list()}
    assert after["FCJOB-FA-C012-SUCCEEDED"]["state"] == "SUCCEEDED"
    assert after["FCJOB-FA-C012-SUCCEEDED"]["artifact_sha256"] == before["FCJOB-FA-C012-SUCCEEDED"]["artifact_sha256"]
    assert after["FCJOB-FA-C012-PAUSED"]["state"] == "PAUSED"
    assert after["FCJOB-FA-C012-RETRY-WAIT"]["state"] == "RETRY_WAIT"
    assert after["FCJOB-FA-C012-RUNNING-UNCOMMITTED"]["artifact_sha256"] is None


def test_fa_c012_corrupt_snapshot_fails_closed(tmp_path):
    q = build_precrash_queue()
    snapshot = build_recovery_snapshot(q)
    snapshot["queue_snapshot"]["jobs"][0]["intent"]["semantic_asset_id"] = "TAMPERED"
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(Exception) as exc:
        load_and_reconcile(path)
    assert "E_SNAPSHOT_HASH" in str(exc.value)


def test_console_recovery_fence_blocks_redispatch_capable_commands(tmp_path):
    q = build_precrash_queue()
    path = tmp_path / "snapshot.json"
    persist_recovery_snapshot(path, build_recovery_snapshot(q))
    recovered, manifest = load_and_reconcile(path)
    server = load_server("console_c012_fence")
    server.install_recovered_queue(recovered, reconciliation_required_job_ids=manifest["reconciliation_required_job_ids"])
    fenced = "FCJOB-FA-C012-RUNNING-COMMITTED"
    for action in ("START", "RESUME", "RETRY"):
        with pytest.raises(server.ConsoleRequestError) as exc:
            server.apply_queue_command(command(fenced, action, action.lower()))
        assert exc.value.code == "RECONCILIATION_REQUIRED"
    assert server.CORE_QUEUE.get(fenced).state == "PAUSED"


def test_console_ui_restart_reconciles_same_factory_core_truth(tmp_path):
    q = build_precrash_queue()
    path = tmp_path / "snapshot.json"
    persist_recovery_snapshot(path, build_recovery_snapshot(q))

    def roundtrip(module_name: str):
        recovered, manifest = load_and_reconcile(path)
        server = load_server(module_name)
        server.install_recovered_queue(recovered, reconciliation_required_job_ids=manifest["reconciliation_required_job_ids"])
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/queue/jobs", timeout=5) as response:
                return json.loads(response.read())
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)

    first = roundtrip("console_c012_restart_one")
    second = roundtrip("console_c012_restart_two")
    assert first == second
    assert first["provider_dispatch_performed"] is False
    assert first["reconciliation_required_job_ids"] == ["FCJOB-FA-C012-RUNNING-COMMITTED"]
    states = {event["job_id"]: event["state"] for event in first["events"]}
    assert states["FCJOB-FA-C012-RUNNING-UNCOMMITTED"] == "READY"
    assert states["FCJOB-FA-C012-RUNNING-COMMITTED"] == "PAUSED"
    assert states["FCJOB-FA-C012-SUCCEEDED"] == "SUCCEEDED"


def test_console_recovery_http_fence_returns_normalized_error(tmp_path):
    q = build_precrash_queue()
    path = tmp_path / "snapshot.json"
    persist_recovery_snapshot(path, build_recovery_snapshot(q))
    recovered, manifest = load_and_reconcile(path)
    server = load_server("console_c012_http_fence")
    server.install_recovered_queue(recovered, reconciliation_required_job_ids=manifest["reconciliation_required_job_ids"])
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps(command("FCJOB-FA-C012-RUNNING-COMMITTED", "RESUME", "http")).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_port}/api/queue/action",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=5)
        payload = json.loads(exc.value.read())
        assert exc.value.code == 400
        assert payload["code"] == "RECONCILIATION_REQUIRED"
        assert payload["dispatch_performed"] is False
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_fa_c012_evidence_contains_no_secret_or_provider_wire_material(tmp_path):
    text = json.dumps(run_console_recovery_acceptance(tmp_path)).lower()
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
