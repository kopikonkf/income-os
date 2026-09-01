import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
ROADMAP = ROOT / "docs" / "architecture" / "DIE_PRODUCTION_POSTPROCESSING_ROADMAP_V1.md"


def _tasks():
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    return {row["id"]: row for row in graph["tasks"]}


def test_new_postprocessing_tasks_have_unique_ids_and_valid_dependencies():
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    ids = [row["id"] for row in graph["tasks"]]
    assert len(ids) == len(set(ids))
    known = set(ids)
    for row in graph["tasks"]:
        assert set(row.get("depends_on", [])) <= known


def test_worker_model_lane_is_zero_cost_and_gates_oe007f():
    tasks = _tasks()
    assert tasks["WRK-001A"]["status"] == "DONE"
    assert tasks["WRK-001B"]["status"] == "DONE"
    assert tasks["WRK-001C"]["status"] == "DONE"
    assert tasks["WRK-001D"]["status"] == "READY"
    assert tasks["WRK-001"]["status"] == "BLOCKED"
    assert tasks["WRK-001A"]["depends_on"] == ["DIE-202"]
    assert tasks["WRK-001B"]["depends_on"] == ["WRK-001A"]
    assert tasks["WRK-001C"]["depends_on"] == ["WRK-001B"]
    assert tasks["WRK-001D"]["depends_on"] == ["WRK-001C"]
    assert tasks["WRK-001"]["depends_on"] == ["WRK-001D"]
    assert "WRK-001" in tasks["OE-007F"]["depends_on"]
    text = ROADMAP.read_text(encoding="utf-8")
    assert "opencode/muse-spark-1.2-contributor-free" in text
    assert "no paid fallback" in text.lower()


def test_upscale_lane_is_recovery_only_and_gates_final_canary_feedback():
    tasks = _tasks()
    assert tasks["UP-001A"]["status"] == "DONE"
    assert tasks["UP-001"]["status"] == "DONE"
    assert tasks["UP-001A"]["depends_on"] == ["DIE-203"]
    assert tasks["UP-001"]["depends_on"] == ["UP-001D"]
    assert "UP-001" in tasks["OE-007G"]["depends_on"]
    text = ROADMAP.read_text(encoding="utf-8")
    assert "realesr-general-x4v3" in text
    assert "rights/safety failures are never recoverable by upscale" in text


def test_metadata_lane_preserves_division_semantic_authority():
    tasks = _tasks()
    assert tasks["META-001A"]["status"] == "DONE"
    assert tasks["META-001"]["status"] == "DONE"
    assert tasks["META-001A"]["depends_on"] == ["OE-005"]
    assert tasks["META-001E"]["depends_on"] == ["META-001D", "QA-001D"]
    assert tasks["META-001"]["depends_on"] == ["META-001E"]
    assert "META-001" in tasks["OE-007G"]["depends_on"]
    text = ROADMAP.read_text(encoding="utf-8")
    assert "Worker cannot invent" in text
    assert "canonical sidecar" in text


def test_rights_lane_uses_existing_nonwaivable_qa_vetoes():
    tasks = _tasks()
    assert tasks["RIGHTS-001A"]["status"] == "DONE"
    assert tasks["RIGHTS-001"]["status"] == "DONE"
    assert tasks["RIGHTS-001A"]["depends_on"] == ["QA-001"]
    assert tasks["RIGHTS-001"]["depends_on"] == ["RIGHTS-001E"]
    assert "RIGHTS-001" in tasks["OE-007G"]["depends_on"]
    text = ROADMAP.read_text(encoding="utf-8")
    assert "RIGHTS_UNCLEAR" in text
    assert "RIGHTS_FAILED" in text
    assert "does not provide legal advice or legal clearance" in text


def test_oe007g_requires_postprocessed_final_artifact_chain():
    tasks = _tasks()
    assert tasks["OE-007G"]["depends_on"] == [
        "OE-007F",
        "UP-001",
        "META-001",
        "RIGHTS-001",
        "QA-001",
        "QC-001",
    ]


def test_acceptance_receipts_are_pinned_and_passed():
    receipts = {
        "UP-001": ROOT / "company/muxia/receipts/UP-001-upscale-engine.acceptance.receipt.json",
        "META-001": ROOT / "company/muxia/receipts/META-001-asset-metadata.acceptance.receipt.json",
        "RIGHTS-001": ROOT / "company/muxia/receipts/RIGHTS-001-rights-ip-preflight.acceptance.receipt.json",
    }
    for task_id, path in receipts.items():
        assert path.is_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["task_id"] == task_id
        assert payload["status"] == "PASS"
    wrk = json.loads(
        (ROOT / "company/muxia/receipts/WRK-001-foundation.acceptance.receipt.json").read_text(encoding="utf-8")
    )
    assert wrk["status"] == "PARTIAL_PASS"
    assert wrk["completed_tasks"] == ["WRK-001A", "WRK-001B", "WRK-001C"]
    assert wrk["pending_task"] == "WRK-001D"
