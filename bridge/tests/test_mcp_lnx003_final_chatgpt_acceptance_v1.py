from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
RECEIPT = ROOT / "company" / "muxia" / "receipts" / "MCP-LNX-003-final-chatgpt-cloud.acceptance.receipt.json"
REKEY = ROOT / "company" / "muxia" / "receipts" / "IDENTITY-LNX-REKEY-003-acceptance.receipt.json"


def test_mcp_lnx003_is_done_from_real_chatgpt_cloud_and_preserves_degraded_truth() -> None:
    tasks = {row["id"]: row for row in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["MCP-LNX-003"]["status"] == "DONE"
    assert tasks["WAKE-LNX-001"]["status"] == "DONE"
    assert tasks["WAKE-LNX-002"]["status"] == "READY"
    d = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert d["status"] == "DONE"
    div = d["chatgpt_cloud"]["division01"]
    exe = d["chatgpt_cloud"]["executive"]
    assert div["tool_scan"] == "6/6 PASS"
    assert div["context_snapshot"]["principal_id"] == "die-lnx-division-001"
    assert div["context_snapshot"]["scope"] == "single_division"
    assert div["context_snapshot"]["freshness_status"] == "fresh"
    assert div["context_snapshot"]["source_trust"] == "DEGRADED"
    assert div["control_boundary"] == "E_STAGING_READ_ONLY"
    assert exe["tool_scan"] == "18/18 PASS"
    assert exe["context_snapshot"]["principal_id"] == "die-lnx-executive-001"
    assert exe["context_snapshot"]["scope"] == "company_portfolio"
    assert exe["context_snapshot"]["freshness_status"] == "fresh"
    assert exe["context_snapshot"]["source_trust"] == "DEGRADED"
    assert exe["control_boundary"] == "E_STAGING_READ_ONLY"
    assert d["semantic_quality_note"]["source_trust_degraded_is_mcp_transport_failure"] is False
    assert d["surface_boundary"]["dev_or_raw_filesystem_tools_exposed"] is False


def test_cross_principal_equivalent_authenticated_proof_remains_denied() -> None:
    r = json.loads(REKEY.read_text(encoding="utf-8"))
    proof = r["linux"]["authenticated_proof"]
    assert proof["cross_bearer_exec_to_div"] == "DENIED_401"
    assert proof["cross_bearer_div_to_exec"] == "DENIED_401"
