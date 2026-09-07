from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from console_provider_canary import ConsoleProviderCanaryError, run_console_provider_canary, validate_request  # noqa: E402

REQUEST = ROOT / "company/factory-asset/fixtures/console-provider-canary/FA-C010-request.json"


def load_request():
    return json.loads(REQUEST.read_text(encoding="utf-8"))


def fake_executor(*, owner_after=640348, active_leases_after=0):
    calls = {"count": 0}

    def execute(request, workspace):
        calls["count"] += 1
        artifact = workspace / "provider-artifact" / "source-original.png"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1024, 1024), (22, 140, 145)).save(artifact, format="PNG")
        import hashlib
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        route = {
            "schema": "die.factory-asset.cluster-provider-route.v1",
            "job_id": request["job_id"],
            "idempotency_key": request["idempotency_key"],
            "attempt": 1,
            "retry_index": 0,
            "route_id": "route-fake",
            "provider_id": "qwen",
            "cluster_id": request["routing_constraint"]["cluster_id"],
            "transport": "BROWSER_CDP",
            "requires_tab_lease": True,
            "browser_owner_action": "NONE",
        }
        return {
            "schema": "die.factory-asset.console-provider-executor.v1",
            "result": "PASS",
            "status": "SUCCEEDED",
            "job_id": request["job_id"],
            "idempotency_key": request["idempotency_key"],
            "route": route,
            "generation_commit": {"commit_id": "commit-fake", "provider_id": "qwen", "cluster_id": request["routing_constraint"]["cluster_id"]},
            "dispatch_committed_count": 1,
            "artifact": {"path": str(artifact), "sha256": digest, "bytes": artifact.stat().st_size, "mime": "image/png"},
            "broker_before": {"cluster_id": request["routing_constraint"]["cluster_id"], "browser_owner_pid": 640348, "active_leases": 0, "open_pages": 2, "max_tabs": 8},
            "broker_after": {"cluster_id": request["routing_constraint"]["cluster_id"], "browser_owner_pid": owner_after, "active_leases": active_leases_after, "open_pages": 2, "max_tabs": 8},
            "credential_values_read": False,
            "cookies_or_tokens_read": False,
            "provider_login_automated": False,
            "submission_authorized": False,
            "publication_authorized": False,
            "spend_usd": 0,
        }

    return calls, execute


def test_fa_c010_console_job_reaches_governed_provider_and_persists_master(tmp_path):
    request = load_request()
    calls, executor = fake_executor()
    result = run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=executor)
    assert result["result"] == "PASS"
    assert result["source_surface"] == "FACTORY_CONSOLE"
    assert result["route"]["provider_id"] == "qwen"
    assert result["route"]["cluster_id"] == request["routing_constraint"]["cluster_id"]
    assert result["route"]["transport"] == "BROWSER_CDP"
    assert result["dispatch_committed_count"] == 1
    assert result["direct_gui_provider_browser_ownership"] is False
    assert result["master"]["provider_original_exact_copy"] is True
    assert Path(result["master"]["path"]).is_file()
    assert calls["count"] == 1
    state = json.loads((tmp_path / "console-state.json").read_text())
    assert state["job"]["state"] == "SUCCEEDED"
    assert state["job"]["artifact_sha256"] == result["master"]["sha256"]
    lineage = json.loads((tmp_path / "lineage.json").read_text())
    assert lineage["provider_original_sha256"] == lineage["master_sha256"] == result["master"]["sha256"]


def test_fa_c010_replay_reuses_final_without_provider_call(tmp_path):
    request = load_request()
    calls, executor = fake_executor()
    first = run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=executor)
    assert first["provider_call_performed"] is True

    def forbidden(*_args, **_kwargs):
        raise AssertionError("provider must not be called on replay")

    second = run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=forbidden)
    assert second["idempotent_replay"] is True
    assert second["provider_call_performed"] is False
    assert calls["count"] == 1


def test_fa_c010_rejects_authority_drift():
    request = load_request()
    request["authority"]["spend_usd"] = 1
    with pytest.raises(ConsoleProviderCanaryError, match="E_AUTHORITY"):
        validate_request(request)


def test_fa_c010_fails_closed_on_prior_committed_attempt(tmp_path):
    request = load_request()
    (tmp_path / "provider-attempt.json").write_text(json.dumps({"dispatch_committed": True}) + "\n")
    with pytest.raises(ConsoleProviderCanaryError, match="E_PRIOR_DISPATCH_COMMITTED"):
        run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=lambda *_: {})


def test_fa_c010_rejects_browser_owner_drift(tmp_path):
    request = load_request()
    _, executor = fake_executor(owner_after=999999)
    with pytest.raises(ConsoleProviderCanaryError, match="E_BROWSER_OWNER_DRIFT"):
        run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=executor)


def test_fa_c010_rejects_lease_leak(tmp_path):
    request = load_request()
    _, executor = fake_executor(active_leases_after=1)
    with pytest.raises(ConsoleProviderCanaryError, match="E_LEASE_LEAK"):
        run_console_provider_canary(request=request, workspace=tmp_path, execute_provider=executor)
