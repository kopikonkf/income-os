from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
ARCH = ROOT / "docs" / "architecture" / "DIE_PRODUCTION_ASSURANCE_DISTRIBUTION_ARCHITECTURE_V1.md"
TASKDOC = ROOT / "docs" / "architecture" / "DIE_PRODUCTION_ASSURANCE_DISTRIBUTION_TASK_GRAPH_V1.md"
ORCH = ROOT / "ORCHESTRATOR_CONTRACT.md"
QA_CORE = ROOT / "bridge" / "income_os_bridge" / "m001_asset_qa.py"


def _tasks() -> dict[str, dict]:
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data["tasks"]}


def test_pad_new_task_family_count_and_all_dependencies_resolve() -> None:
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    tasks = {row["id"]: row for row in data["tasks"]}
    pad = {k for k in tasks if k.startswith("QA-") or k.startswith("QC-") or k.startswith("SUB-") or k.startswith("CL-")}
    assert len(pad) == 49
    for task_id in pad:
        for dep in tasks[task_id]["depends_on"]:
            assert dep in tasks, f"{task_id} -> missing {dep}"


def test_existing_qa_core_is_promoted_not_reinvented() -> None:
    assert QA_CORE.is_file()
    code = QA_CORE.read_text(encoding="utf-8")
    assert "Deterministic universal-QA gate" in code
    assert '"BLOCKED_REVIEW"' in code
    assert '"REVIEW_REQUIRED"' in code
    arch = ARCH.read_text(encoding="utf-8")
    assert "promote/refactor this core" in arch


def test_qc_automation_can_remove_founder_manual_review_only_by_explicit_delegation() -> None:
    arch = ARCH.read_text(encoding="utf-8")
    assert "Founder-free QC" in arch
    assert "SHADOW_ONLY" in arch
    assert "BOUNDED_AUTO_QC" in arch
    assert "SAMPLED_AUDIT" in arch
    assert "Founder-ratified delegation policy artifact" in arch
    tasks = _tasks()
    assert "Founder shadow-mode" in tasks["QC-001E"]["title"]
    assert "Founder ratification" in tasks["QC-001F"]["acceptance"]
    assert "submission authority remains separate" in tasks["QC-001"]["acceptance"]


def test_submission_marketplace_set_is_exact_and_magnific_is_excluded() -> None:
    tasks = _tasks()
    expected = {"SUB-ADOBE", "SUB-DREAMSTIME", "SUB-123RF", "SUB-VECTEEZY", "SUB-MOTIONELEMENTS"}
    milestones = {task_id for task_id in tasks if task_id in expected}
    assert milestones == expected
    assert not any(task_id.startswith("SUB-MAGNIFIC") for task_id in tasks)
    arch = ARCH.read_text(encoding="utf-8")
    assert "Magnific is a production/recovery service" in arch


def test_each_marketplace_has_contract_dryrun_activation_and_acceptance() -> None:
    tasks = _tasks()
    for base in ["SUB-ADOBE", "SUB-DREAMSTIME", "SUB-123RF", "SUB-VECTEEZY", "SUB-MOTIONELEMENTS"]:
        assert base + "A" in tasks
        assert base + "B" in tasks
        assert base + "C" in tasks
        assert base in tasks
        assert tasks[base + "B"]["depends_on"] == [base + "A"]
        assert tasks[base + "C"]["depends_on"] == [base + "B"]
        assert tasks[base]["depends_on"] == [base + "C"]


def test_oe007_is_production_canary_and_requires_first_class_qa_qc() -> None:
    tasks = _tasks()
    assert tasks["OE-007G"]["depends_on"] == ["OE-007F", "QA-001", "QC-001"]
    assert "QA/QC" in tasks["OE-007G"]["title"]
    assert "no marketplace submission is claimed" in tasks["OE-007G"]["acceptance"]
    assert "production canary" in tasks["OE-007"]["title"]
    assert "external marketplace submission is not claimed" in tasks["OE-007"]["acceptance"]


def test_cl001_is_the_full_market_closed_loop() -> None:
    tasks = _tasks()
    assert tasks["CL-001"]["depends_on"] == ["CL-001F"]
    chain = " ".join(tasks[x]["acceptance"] for x in ["CL-001A", "CL-001B", "CL-001C", "CL-001D", "CL-001E", "CL-001F", "CL-001"])
    assert "marketplace adapter" in chain
    assert "QA PASS" in chain and "QC PASS" in chain
    assert "submission" in chain.lower()
    assert "review" in chain.lower()
    assert "ERVA" in chain
    assert "false-success=0" in chain


def test_submission_authority_is_separate_from_qc_authority() -> None:
    tasks = _tasks()
    assert "QC delegation is not submission delegation" in tasks["CL-001C"]["acceptance"]
    common = " ".join(tasks[x]["acceptance"] for x in ["SUB-001B", "SUB-001C", "SUB-001E", "SUB-001"])
    assert "Founder authority" in common
    orch = ORCH.read_text(encoding="utf-8")
    assert "A QC delegation does not imply submission delegation" in orch


def test_operator_acceptance_and_reliability_open_parallel_soak_and_qa_readiness() -> None:
    tasks = _tasks()
    assert tasks["OE-006D"]["status"] == "DONE"
    assert tasks["OE-006E"]["status"] == "DONE"
    assert tasks["OE-006F"]["status"] == "DONE"
    assert tasks["OE-006G"]["status"] == "DONE"
    assert tasks["OE-006"]["status"] == "DONE"
    assert tasks["MX-060"]["status"] == "DONE"
    assert tasks["MX-061"]["status"] == "DONE"
    assert tasks["MX-062"]["status"] == "READY"
    assert tasks["QA-001A"]["status"] == "DONE"
    assert tasks["QA-001B"]["status"] == "DONE"
    assert tasks["QA-001C"]["status"] == "READY"
    assert tasks["QA-001D"]["status"] == "READY"
    pad_statuses = {row["status"] for task_id, row in tasks.items() if task_id.startswith(("QA-", "QC-", "SUB-", "CL-"))}
    assert pad_statuses == {"DONE", "READY", "BLOCKED"}
    taskdoc = TASKDOC.read_text(encoding="utf-8")
    assert "OE-006 = DONE" in taskdoc
    assert "MX-062 = READY" in taskdoc
