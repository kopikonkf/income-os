from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "company" / "workers" / "opencode" / "model_worker.py"
POLICY = ROOT / "company" / "workers" / "opencode" / "model-policy.v1.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MW = load("wrk001_model_worker_test", RUNNER)


def job(workspace: Path) -> dict:
    return {
        "schema": "die.worker-job-envelope.v1",
        "task_id": "WRK001-SYNTH",
        "mission_id": "M-001",
        "executor": "opencode",
        "goal": "Return exactly WRK001_BOUNDED_OK and nothing else.",
        "context": "Synthetic zero-cost execution proof.",
        "workspace": str(workspace.resolve()),
        "constraints": {
            "time_budget_min": 5,
            "allowed_paths": [str(workspace.resolve())],
            "network": "allowlist",
            "forbidden": ["credentials", "market submission", "spawning workers", "writes outside workspace", "destructive operations"],
        },
        "acceptance_criteria": [{"id": "AC-1", "statement": "marker returned", "verify_with": "model receipt"}],
        "handoff": {"kind": "muxia_job", "provider_id": "chatgpt", "required_capability": "image_generation", "profile_selector": None, "timeout_ms": 60000},
    }


def test_wrk001_policy_pins_only_muse_free_and_forbids_paid_fallback() -> None:
    policy = json.loads(POLICY.read_text())
    MW.validate_policy(policy)
    assert policy["model"] == "opencode/muse-spark-1.2-contributor-free"
    assert policy["small_model"] == policy["model"]
    assert policy["cost_policy"] == "ZERO_USD_ONLY"
    assert policy["paid_fallback_allowed"] is False


def test_wrk001_rejects_non_allowlisted_network_and_workspace_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    ws = root / "job"
    ws.mkdir(parents=True)
    value = job(ws)
    value["constraints"]["network"] = "none"
    with pytest.raises(MW.ModelWorkerError, match="E_NETWORK_NOT_GOVERNED"):
        MW.validate_job(value, root)
    outside = job(tmp_path / "outside")
    with pytest.raises(MW.ModelWorkerError, match="E_WORKSPACE_ESCAPE"):
        MW.validate_job(outside, root)


def test_wrk001_runtime_config_requires_exact_single_model_whitelist(tmp_path: Path) -> None:
    cfg = tmp_path / "opencode.jsonc"
    cfg.write_text(json.dumps({
        "model": MW.MODEL,
        "small_model": MW.MODEL,
        "provider": {"opencode": {"whitelist": ["muse-spark-1.2-contributor-free"]}},
    }))
    MW.validate_runtime_config(cfg)
    bad = json.loads(cfg.read_text())
    bad["provider"]["opencode"]["whitelist"].append("paid-model")
    cfg.write_text(json.dumps(bad))
    with pytest.raises(MW.ModelWorkerError, match="E_RUNTIME_WHITELIST"):
        MW.validate_runtime_config(cfg)


@pytest.mark.skipif(os.name == "nt", reason="WRK-001 model subprocess boundary is Linux-only")
def test_wrk001_bounded_model_receipt_records_exact_identity_without_fallback(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "job"
    workspace.mkdir(parents=True)
    worker_home = tmp_path / "worker-home"
    config = worker_home / ".config" / "opencode" / "opencode.jsonc"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({
        "model": MW.MODEL,
        "small_model": MW.MODEL,
        "provider": {"opencode": {"whitelist": ["muse-spark-1.2-contributor-free"]}},
    }))
    fake = tmp_path / "opencode"
    fake.write_text("#!/usr/bin/env python3\nimport json\nprint(json.dumps({'type':'text','text':'WRK001_BOUNDED_OK'}))\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    policy = json.loads(POLICY.read_text())
    policy["worker_home"] = str(worker_home)
    policy["config_path"] = str(config)
    policy["binary"] = str(fake)
    receipt = MW.execute(job=job(workspace), policy=policy, workspace_root=workspace_root, expected_marker="WRK001_BOUNDED_OK", timeout_sec=10)
    assert receipt["status"] == "PASS"
    assert receipt["model"] == MW.MODEL
    assert receipt["cost_policy"] == "ZERO_USD_ONLY"
    assert receipt["paid_fallback_used"] is False
    assert receipt["expected_marker_verified"] is True
    assert receipt["authority_boundary"]["semantic_authority_expanded"] is False
