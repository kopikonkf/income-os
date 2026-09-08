from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
RECEIPT = ROOT / "company" / "muxia" / "receipts" / "MX-053-architect-linux-coexistence-staging.acceptance.receipt.json"
REGISTRY = ROOT / "company" / "component-registry-v1.json"

def test_mx053_linux_architect_local_staging_is_done_without_handoff() -> None:
    tasks={row["id"]:row for row in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert tasks["MX-053"]["status"] == "DONE"
    assert tasks["MX-054"]["status"] == "READY"
    assert tasks["CUT-006"]["depends_on"] == ["MX-054", "CUT-005"]
    assert receipt["decision"] == "LINUX_LOCAL_EXECUTOR_STAGING_PASS_NO_HANDOFF"
    assert receipt["mcp_architect_canon"]["accepted_main_sha"] == "1c3cd96847f94624a4c470291247798d4e31bfba"
    assert receipt["h01_runtime"]["runtime_id"] == "architect-h01-linux"
    assert receipt["h01_runtime"]["listener"] == "127.0.0.1:8890"
    assert "/srv/die" not in receipt["h01_runtime"]["write_roots"]
    assert receipt["acceptance_evidence"]["sanitized_runtime_log"]["secret_pattern_hits"] == 0
    assert receipt["windows_rollback"]["remains_control_channel"] is True
    assert receipt["authority_boundaries"]["public_ingress_created"] is False
    assert receipt["authority_boundaries"]["mission_control_target_runtime_broker_claimed"] is False
    assert receipt["authority_boundaries"]["cut006_handoff_authorized"] is False
    assert registry["components"]["architect"]["status"] == "LINUX_STAGING_LIVE"
