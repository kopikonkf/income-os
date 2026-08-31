from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
RECEIPT = ROOT / "company" / "muxia" / "receipts" / "ID-LNX-001-hermes-prompt-convergence.acceptance.receipt.json"


def test_id_lnx001_done_and_scheduler_lane_released() -> None:
    tasks = {x["id"]: x for x in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["ID-LNX-001"]["status"] == "DONE"
    assert tasks["ID-LNX-002"]["status"] == "READY"
    d = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert d["status"] == "DONE"
    assert d["live"]["effective_agents_files"] == [
        "/srv/die/AGENTS.md",
        "/srv/die/company/die-agents/hermes/AGENTS.md",
    ]
    assert d["live"]["has_root_contract"] is True
    assert d["live"]["has_hermes_specific_contract"] is True
    assert d["live"]["llm_call_performed"] is False
    assert d["isolation"]["production_source_mutated"] is False
    assert d["isolation"]["mx062_pid_before"] == d["isolation"]["mx062_pid_after"] == 200975
