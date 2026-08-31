from __future__ import annotations

import json
from pathlib import Path

from income_os_bridge import authority, canon_context, runtime_mcp_server

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "company" / "identity-registry.json"
INSTANCES = ROOT / "company" / "runtime-instances-v1.json"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
MODEL = ROOT / "docs" / "architecture" / "DIE_COMPANY_INSTANCE_MODEL_V1.md"


def _identity(identity_id: str) -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return next(row for row in registry["identities"] if row["id"] == identity_id)


def _tools(principal_id: str) -> dict[str, dict]:
    return {row["name"]: row for row in runtime_mcp_server.tool_definitions(principal_id, REGISTRY)}


def test_company_instances_share_roles_but_not_principals_or_accounts() -> None:
    data = json.loads(INSTANCES.read_text(encoding="utf-8"))
    assert data["status"] == "GOVERNED"
    win = data["instances"]["DIE-WINDOWS"]
    lnx = data["instances"]["DIE-LINUX"]
    assert win["principals"] == {"executive": "chatgpt-plus-executive", "division01": "division-head-division01"}
    assert lnx["principals"] == {"executive": "die-lnx-executive-001", "division01": "die-lnx-division-001"}
    assert win["account_binding"] != lnx["account_binding"]
    assert data["doctrine"]["credential_reuse_between_instances"] == "forbidden"
    assert data["doctrine"]["independent_mutable_state"] is True
    assert "full operational active-active federation is NOT claimed" in data["transitional_boundaries"]["claim"]


def test_linux_principals_reuse_shared_role_documents_without_inheritance() -> None:
    pairs = [
        ("chatgpt-plus-executive", "die-lnx-executive-001", "DIE-WINDOWS", "DIE-LINUX"),
        ("division-head-division01", "die-lnx-division-001", "DIE-WINDOWS", "DIE-LINUX"),
    ]
    for win_id, lnx_id, win_instance, lnx_instance in pairs:
        win = _identity(win_id)
        lnx = _identity(lnx_id)
        assert win["document"] == lnx["document"]
        assert win["kind"] == lnx["kind"] and win["scope"] == lnx["scope"]
        assert win["capabilities"] == lnx["capabilities"]
        assert win["inherits_identity_ids"] == [] and lnx["inherits_identity_ids"] == []
        assert win["company_instance_id"] == win_instance
        assert lnx["company_instance_id"] == lnx_instance
        assert win["role_profile_id"] == lnx["role_profile_id"]
        assert lnx["architect_dev_access"] == "deny"


def test_linux_runtime_bindings_are_distinct_from_windows_and_preserve_tool_counts() -> None:
    assert runtime_mcp_server.runtime_port("chatgpt-plus-executive") == 8791
    assert runtime_mcp_server.runtime_port("division-head-division01") == 8792
    assert runtime_mcp_server.runtime_port("die-lnx-executive-001") == 8891
    assert runtime_mcp_server.runtime_port("die-lnx-division-001") == 8892
    assert runtime_mcp_server.runtime_public_base_url("die-lnx-executive-001") == "https://executive-mcp.aethers.biz.id"
    assert runtime_mcp_server.runtime_public_base_url("die-lnx-division-001") == "https://division01-mcp.aethers.biz.id"
    assert len(_tools("die-lnx-executive-001")) == 18
    assert len(_tools("die-lnx-division-001")) == 6


def test_instance_local_escalation_never_crosses_linux_to_windows() -> None:
    win_schema = _tools("division-head-division01")["escalate"]["inputSchema"]
    lnx_schema = _tools("die-lnx-division-001")["escalate"]["inputSchema"]
    assert win_schema["properties"]["escalation_target"]["enum"] == ["chatgpt-plus-executive", "founder"]
    assert lnx_schema["properties"]["escalation_target"]["enum"] == ["die-lnx-executive-001", "founder"]
    assert "chatgpt-plus-executive" not in lnx_schema["properties"]["escalation_target"]["enum"]
    base = {
        "request_id": "REQ-LNX-ESC-001",
        "source_snapshot": {},
        "reason": "bounded instance-local escalation test",
        "evidence_refs": [],
        "target_ref": "M-001",
    }
    linux_identity = _identity("die-lnx-division-001")
    accepted = runtime_mcp_server._validate_control(
        "escalate", {**base, "escalation_target": "die-lnx-executive-001"}, linux_identity
    )
    assert accepted["escalation_target"] == "die-lnx-executive-001"
    try:
        runtime_mcp_server._validate_control(
            "escalate", {**base, "escalation_target": "chatgpt-plus-executive"}, linux_identity
        )
    except runtime_mcp_server.RuntimeMcpError as exc:
        assert exc.code == "E_MCP_INPUT_INVALID"
    else:
        raise AssertionError("Linux Division01 must not escalate to the Windows Executive principal")


def test_linux_principals_authorize_same_scoped_semantics_and_share_canon_profiles(monkeypatch) -> None:
    monkeypatch.setenv("DIE_REPO_SHA", "0" * 40)
    e = authority.authorize("die-lnx-executive-001", "context.snapshot.read", "company_portfolio", REGISTRY)
    d = authority.authorize("die-lnx-division-001", "context.snapshot.read", "single_division", REGISTRY)
    assert e["principal_id"] == "die-lnx-executive-001"
    assert d["division_id"] == "DIVISION-01"
    ectx = canon_context.build_surface(e, root=ROOT)
    dctx = canon_context.build_surface(d, root=ROOT)
    assert ectx["data"]["principal_id"] == "die-lnx-executive-001"
    assert dctx["data"]["principal_id"] == "die-lnx-division-001"
    assert any(row["fact_id"] == "EXECUTIVE-ROLE" for row in ectx["data"]["decision_facts"])
    assert any(row["fact_id"] == "DIVISION01-ROLE" for row in dctx["data"]["decision_facts"])


def test_rekey_login_gate_releases_real_e2e_and_wake_after_new_account_login() -> None:
    tasks = {row["id"]: row for row in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["COMPANY-INSTANCE-001"]["status"] == "DONE"
    assert tasks["IDENTITY-LNX-REKEY-001"]["status"] == "DONE"
    assert tasks["IDENTITY-LNX-REKEY-002"]["status"] == "DONE"
    assert tasks["IDENTITY-LNX-REKEY-003"]["status"] == "DONE"
    assert tasks["IDENTITY-LNX-REKEY-004"]["status"] == "DONE"
    assert tasks["MCP-LNX-003"]["status"] == "DONE"
    assert "IDENTITY-LNX-REKEY-004" in tasks["MCP-LNX-003"]["depends_on"]
    assert tasks["WAKE-LNX-001"]["status"] == "DONE"
    assert "IDENTITY-LNX-REKEY-004" in tasks["WAKE-LNX-001"]["depends_on"]


def test_model_explicitly_refuses_source_fork_and_full_federation_claim() -> None:
    text = MODEL.read_text(encoding="utf-8")
    assert "not source-code forks" in text
    assert "ROLE != PRINCIPAL != EXTERNAL ACCOUNT != COMPANY INSTANCE != RUNTIME" in text
    assert "full operational active-active federation" in text
    assert "die-lnx-executive-001" in text and "die-lnx-division-001" in text
