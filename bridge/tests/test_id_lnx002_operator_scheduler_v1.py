from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "die-agents" / "hermes" / "operator-v2"
FIXTURE = ENGINE / "fixtures" / "build_operator_v2_fixture.py"
UNIT = ROOT / "company" / "die-agents" / "hermes" / "linux" / "die-hermes-gateway.service"
INSTALL = ROOT / "company" / "die-agents" / "hermes" / "linux" / "install-proactive-operator-v2.sh"
AGENTS = ROOT / "company" / "die-agents" / "hermes" / "AGENTS.md"


def _load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixture = _load("id_lnx002_fixture", FIXTURE)
validator = _load("id_lnx002_validator", ENGINE / "validate_receipt_snapshot.py")
projector = _load("id_lnx002_projector", ENGINE / "project_intelligence_stage.py")
scheduler = _load("id_lnx002_scheduler", ENGINE / "linux_scheduler_tick.py")


def _linux_snapshot(count: int) -> dict:
    snap = fixture.snapshot_prefix(count, kanban_done=False)
    snap["company_instance_id"] = "DIE-LINUX"
    for row in snap["receipts"]:
        if row.get("expires_at") is not None:
            row["expires_at"] = "2099-01-01T00:00:00Z"
        if row["receipt_type"] in {"WORTH_MAKING_AUTHOR", "BLUEPRINT_AUTHOR"}:
            row["issuer_id"] = "die-lnx-division-001"
        if row["receipt_type"] in {"WORTH_MAKING_EXEC_REVIEW", "BLUEPRINT_EXEC_REVIEW"}:
            row["issuer_id"] = "die-lnx-executive-001"
    return snap


def test_linux_projection_resolves_semantic_roles_to_linux_principals() -> None:
    div = projector.project(_linux_snapshot(2))
    assert div["company_instance_id"] == "DIE-LINUX"
    assert div["intelligence_stage"] == "WORTH_MAKING"
    assert div["required_principal"] == "die-lnx-division-001"
    assert div["next_action_type"] == "OP-REQUEST-DIVISION01-WORTH-MAKING"

    exe = projector.project(_linux_snapshot(3))
    assert exe["intelligence_stage"] == "EXEC_WORTH_MAKING_REVIEW"
    assert exe["required_principal"] == "die-lnx-executive-001"


def test_linux_snapshot_rejects_windows_semantic_issuer() -> None:
    snap = _linux_snapshot(3)
    author = next(x for x in snap["receipts"] if x["receipt_type"] == "WORTH_MAKING_AUTHOR")
    author["issuer_id"] = "division-head-division01"
    out = validator.validate(snap)
    assert out["status"] == "FAIL"
    assert any(x.startswith("E_CROSS_INSTANCE_ISSUER:WORTH_MAKING_AUTHOR") for x in out["errors"])


def test_windows_projection_remains_backward_compatible() -> None:
    snap = fixture.snapshot_prefix(2, kanban_done=False)
    out = projector.project(snap)
    assert out["company_instance_id"] == "DIE-WINDOWS"
    assert out["required_principal"] == "division-head-division01"


def test_linux_scheduler_writes_one_deduped_division_outbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = tmp_path / "die-state"
    inbox = state / "state" / "operator-v2" / "receipt-inbox"
    inbox.mkdir(parents=True)
    snap = _linux_snapshot(2)
    for i, receipt in enumerate(snap["receipts"], start=1):
        (inbox / f"{i:02d}.json").write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setenv("DIE_STATE_ROOT", str(state))
    monkeypatch.setenv("DIE_COMPANY_INSTANCE", "DIE-LINUX")
    monkeypatch.setenv("DIE_OPERATOR_V2_SUBJECT_ID", "M001-TEST")

    first = scheduler.run()
    assert first["status"] == "PASS"
    assert first["claim_status"] == "CLAIMED"
    assert first["action_type"] == "OP-REQUEST-DIVISION01-WORTH-MAKING"
    assert first["target_principal_id"] == "die-lnx-division-001"
    assert first["outbox_written"] is True
    files = list((state / "state" / "operator-v2" / "outbox").glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["company_instance_id"] == "DIE-LINUX"
    assert payload["action_request"]["target_principal_id"] == "die-lnx-division-001"
    assert payload["semantic_content_authored"] is False

    second = scheduler.run()
    assert second["status"] == "PASS"
    assert second["claim_status"] == "SUPPRESSED"
    assert second["routing_decision"] == "NO_OP_DUPLICATE"
    assert len(list((state / "state" / "operator-v2" / "outbox").glob("*.json"))) == 1


def test_linux_service_and_cron_installer_pin_instance_and_no_agent() -> None:
    unit = UNIT.read_text(encoding="utf-8")
    install = INSTALL.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")
    assert "Environment=DIE_COMPANY_INSTANCE=DIE-LINUX" in unit
    assert "die-proactive-operator-v1" in install
    assert "'*/30 * * * *'" in install
    assert "--no-agent" in install
    assert "DIE_COMPANY_INSTANCE=DIE-LINUX" in install
    assert "/opt/die/staging/income-os" in install
    assert "runpy.run_path" in install
    assert '--workdir "$WORKDIR"' in install
    assert "MUXIA_CHATGPT_IMAGE" in agents
    assert "Proxima :3211 only" not in agents
