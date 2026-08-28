from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "company" / "workers" / "opencode" / "runner.py"
DISPATCH = ROOT / "company" / "die-agents" / "hermes" / "worker_dispatch.py"
MUXIA_PROOF = ROOT / "company" / "workers" / "opencode" / "synthetic_muxia_proof.mjs"
HERMES_INSTALL = ROOT / "company" / "die-agents" / "hermes" / "linux" / "install-linux.sh"
HERMES_UNIT = ROOT / "company" / "die-agents" / "hermes" / "linux" / "die-hermes-gateway.service"
OPENCODE_INSTALL = ROOT / "company" / "workers" / "opencode" / "install-linux.sh"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_module("die202_opencode_runner", RUNNER)
dispatch = _load_module("die202_worker_dispatch", DISPATCH)


def _job(workspace: Path) -> dict:
    return {
        "schema": "die.worker-job-envelope.v1",
        "task_id": "DIE202-SYNTH",
        "mission_id": "M-001",
        "executor": "opencode",
        "goal": "Prepare one bounded MUXIA job request and prove OpenCode CLI availability.",
        "context": "Synthetic zero-cost boundary proof only; no provider/model call.",
        "workspace": str(workspace.resolve()),
        "constraints": {
            "time_budget_min": 5,
            "allowed_paths": [str(workspace.resolve())],
            "network": "none",
            "forbidden": [
                "credentials",
                "market submission",
                "spawning workers",
                "writes outside workspace",
                "destructive operations",
            ],
        },
        "acceptance_criteria": [
            {"id": "AC-1", "statement": "OpenCode executable probe passes", "verify_with": "opencode-probe.json"},
            {"id": "AC-2", "statement": "MUXIA job request exists", "verify_with": "muxia-job-request.json"},
        ],
        "handoff": {
            "kind": "muxia_job",
            "provider_id": "chatgpt",
            "required_capability": "image_generation",
            "profile_selector": None,
            "timeout_ms": 60000,
        },
    }


def test_die202_canon_relocation_materializes_hermes_and_worker_contract() -> None:
    assert (ROOT / "company/die-agents/hermes/SOUL.md").is_file()
    assert (ROOT / "company/die-agents/hermes/AGENTS.md").is_file()
    assert (ROOT / "company/workers/contract/IDENTITY.md").is_file()
    assert (ROOT / "company/workers/contract/WORKER_CONTRACT_V0.md").is_file()
    assert not (ROOT / "IDENTITY/hermes-operator/SOUL.md").exists()
    assert not (ROOT / "IDENTITY/hermes-operator/AGENTS.md").exists()
    assert not (ROOT / "IDENTITY/worker-template.md").exists()
    assert not (ROOT / "PROTOCOLS/worker-contract-v0.md").exists()


def test_die202_worker001_runner_never_invokes_model_call() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert '[str(binary), "--version"]' in text
    assert '"network"] != "none"' in text
    assert 'model/provider call performed' in text.lower()
    assert 'opencode run' not in text.lower()
    assert 'fetch(' not in text.lower()
    assert 'requests.' not in text.lower()


def test_die202_hermes_install_is_clean_rebuild_and_ready_gated() -> None:
    install = HERMES_INSTALL.read_text(encoding="utf-8")
    unit = HERMES_UNIT.read_text(encoding="utf-8")
    assert "a0ca7c19204e514f9590ce3b812e029b315ab9e9" in install
    assert '-m pip install -e "$SOURCE_ROOT"' in install
    assert "https://github.com/NousResearch/hermes-agent.git" in install
    assert "ConditionPathExists=/etc/die/hermes/READY" in unit
    assert "User=die-hermes" in unit
    assert "Group=die-runtime" in unit
    assert "AppData" not in install
    assert "auth.json" not in install
    assert "state.db" not in install
    assert "windows_profile_copied=false" in install
    assert '! "$VENV/bin/python" -m pip --version' in install
    assert 'rm -rf "$VENV"' in install


def test_die202_opencode_install_pins_package_and_no_windows_config_copy() -> None:
    text = OPENCODE_INSTALL.read_text(encoding="utf-8")
    assert 'PKG_VERSION="1.18.23"' in text
    assert "npm install --global --prefix" in text
    assert "provider_credentials_copied=false" in text
    assert "windows_config_copied=false" in text
    assert "model_call_performed=false" in text
    assert "C:\\" not in text


def test_die202_runner_rejects_workspace_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.mkdir()
    job = _job(tmp_path / "outside")
    with pytest.raises(ValueError, match="E_WORKSPACE"):
        runner.validate_job(job, root)


def test_die202_runner_rejects_networked_synthetic_job(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    workspace = root / "job"
    workspace.mkdir(parents=True)
    job = _job(workspace)
    job["constraints"]["network"] = "allowlist"
    with pytest.raises(ValueError, match="E_NETWORK"):
        runner.validate_job(job, root)


def test_die202_dispatch_downgrades_done_without_evidence(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    workspace = root / "job"
    workspace.mkdir(parents=True)
    job = _job(workspace)
    result = {
        "schema": "die.worker-result-envelope.v1",
        "task_id": job["task_id"],
        "executor": "opencode",
        "status": "done",
        "summary": "bad",
        "artifacts": [],
        "evidence": [],
        "tests": [],
        "errors": [],
        "next_action": None,
    }
    accepted = dispatch.verify_result(job, result, workspace)
    assert accepted["accepted_status"] == "blocked"
    assert "DONE_WITHOUT_EVIDENCE" in accepted["reasons"]


def test_die202_hermes_to_worker_to_muxia_synthetic_boundary(tmp_path: Path) -> None:
    workspaces = tmp_path / "workspaces"
    workspace = workspaces / "DIE202-SYNTH"
    workspace.mkdir(parents=True)
    job = _job(workspace)
    job_path = workspace / "job.json"
    result_path = workspace / "worker-result.json"
    dispatch_receipt = workspace / "dispatch-receipt.json"
    job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(DISPATCH),
            "--job", str(job_path),
            "--worker-result", str(result_path),
            "--dispatch-receipt", str(dispatch_receipt),
            "--worker-runner", str(RUNNER),
            "--workspace-root", str(workspaces),
            "--opencode-bin", sys.executable,
            "--worker-home", str(tmp_path / "worker-home"),
        ],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    accepted = json.loads(dispatch_receipt.read_text(encoding="utf-8"))
    assert accepted["accepted_status"] == "done"

    muxia_root = tmp_path / "muxia"
    muxia_receipt = workspace / "muxia-boundary-receipt.json"
    node = subprocess.run(
        [
            "node", str(MUXIA_PROOF),
            "--request", str(workspace / "muxia-job-request.json"),
            "--muxia-root", str(muxia_root),
            "--receipt-out", str(muxia_receipt),
        ],
        cwd=str(ROOT),
        env={**dict(__import__("os").environ), "DIE_HOME": str(ROOT)},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert node.returncode == 0, node.stderr
    receipt = json.loads(muxia_receipt.read_text(encoding="utf-8"))
    assert receipt["final_status"] == "SUCCEEDED"
    assert receipt["synthetic_fixture"] is True
    assert receipt["provider_call_performed"] is False
    assert receipt["consumer_chatgpt_used"] is False
    assert all(receipt["completion_evidence"].values())
