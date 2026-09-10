import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "company/workers/opencode/runner.py"
SCHEMA = ROOT / "company/workers/contract/worker-job-envelope.v1.schema.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("worker_runner_contract_test", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def job(workspace: Path, scheduler_contract=True):
    handoff = {
        "kind": "muxia_job",
        "provider_id": "AUTO",
        "required_capability": "image.generate",
        "profile_selector": "governed-multi-cluster",
        "timeout_ms": 600000,
    }
    if scheduler_contract:
        handoff["scheduler_contract"] = "FA-306"
    return {
        "schema": "die.worker-job-envelope.v1",
        "task_id": "PRODSEED000116",
        "mission_id": "M-001",
        "executor": "opencode",
        "goal": "Prepare bounded MUXIA image-generation handoff.",
        "context": "fixed blueprint",
        "workspace": str(workspace),
        "constraints": {
            "time_budget_min": 30,
            "allowed_paths": [str(workspace)],
            "network": "none",
            "forbidden": ["credentials", "market submission", "spawning workers", "writes outside workspace", "destructive operations"],
        },
        "acceptance_criteria": [{"id": "AC-1", "statement": "handoff valid", "verify_with": "muxia-job-request.json"}],
        "handoff": handoff,
    }


def test_scheduler_contract_from_production_runtime_is_accepted(tmp_path):
    workspace = tmp_path / "PRODSEED000116"
    workspace.mkdir()
    assert load_runner().validate_job(job(workspace, True), tmp_path) == workspace.resolve()


def test_legacy_handoff_without_scheduler_contract_remains_accepted(tmp_path):
    workspace = tmp_path / "PRODSEED000115"
    workspace.mkdir()
    j = job(workspace, False)
    j["task_id"] = "PRODSEED000115"
    assert load_runner().validate_job(j, tmp_path) == workspace.resolve()


def test_invalid_scheduler_contract_fails_closed(tmp_path):
    workspace = tmp_path / "PRODSEED000116"
    workspace.mkdir()
    j = job(workspace, True)
    j["handoff"]["scheduler_contract"] = "FA 306/unsafe"
    try:
        load_runner().validate_job(j, tmp_path)
    except ValueError as exc:
        assert "E_HANDOFF:scheduler_contract invalid" in str(exc)
    else:
        raise AssertionError("invalid scheduler_contract must fail closed")


def test_json_schema_declares_scheduler_contract_optional_and_bounded():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    handoff = schema["properties"]["handoff"]
    assert "scheduler_contract" in handoff["properties"]
    assert "scheduler_contract" not in handoff["required"]
    assert handoff["properties"]["scheduler_contract"]["pattern"] == "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
