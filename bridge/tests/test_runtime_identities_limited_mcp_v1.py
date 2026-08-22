"""Runtime identities, division scoping, and least-privilege MCP v1."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from income_os_bridge import (
    authority,
    config,
    projection,
    runtime_mcp_server,
    snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "company" / "identity-registry.json"
NOW = dt.datetime(2026, 8, 22, 3, 0, tzinfo=dt.timezone.utc)


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _identity(identity_id: str) -> dict:
    return next(row for row in _registry()["identities"] if row["id"] == identity_id)


def _surface(name: str, data: object) -> dict:
    return {
        "surface": name,
        "as_of": "2026-08-22T03:00:00Z",
        "completeness": "complete",
        "source_trust": "VERIFIED",
        "operational_control_plane": "hermes-operator/income-operator",
        "canonical_writer": "die-state-manager",
        "sources": [f"semantic:{name}"],
        "notes": [],
        "data": data,
    }


def _signed_division_snapshot(monkeypatch) -> dict:
    monkeypatch.setenv(snapshot.SIGNING_KEY_ENV, "k" * 32)
    monkeypatch.setenv(snapshot.SIGNING_KEY_ID_ENV, "test-key-v1")
    granted = authority.authorize(
        "division-head-division01",
        "context.snapshot.read",
        "single_division",
        REGISTRY,
    )
    return snapshot.build(
        granted,
        {
            "system_state": _surface("system_state", {"autonomy_level": "A0"}),
            "recent_events": _surface(
                "recent_events",
                {"events": [], "since_seq": 0, "next_seq": 0, "truncated": False},
            ),
        },
        now=NOW,
    )


def test_registry_has_concrete_three_chatgpt_runtime_roles() -> None:
    expected = {
        "chatgpt-plus-executive": (
            "executive_strategic_intelligence",
            "company_portfolio",
        ),
        "division-head-division01": (
            "division_decision_engine",
            "single_division",
        ),
        "chatgpt-creator": ("proxima_creator", "single_job_workspace"),
    }
    forbidden = set(_registry()["security"]["runtime_forbidden_capabilities"])
    for identity_id, (kind, scope) in expected.items():
        identity = _identity(identity_id)
        assert identity["kind"] == kind
        assert identity["scope"] == scope
        assert identity["runtime"] is True
        assert identity["template"] is False
        assert identity["architect_dev_access"] == "deny"
        assert identity["inherits_identity_ids"] == []
        assert not (set(identity["capabilities"]) & forbidden)
    assert _identity("division-head-division01")["division_id"] == "DIVISION-01"
    assert _identity("chatgpt-creator")["capabilities"] == ["artifact_production"]


def test_role_specific_tool_surfaces_do_not_leak_dev_or_creator_authority() -> None:
    executive = {
        tool["name"]
        for tool in runtime_mcp_server.tool_definitions(
            "chatgpt-plus-executive",
            REGISTRY,
        )
    }
    division = {
        tool["name"]
        for tool in runtime_mcp_server.tool_definitions(
            "division-head-division01",
            REGISTRY,
        )
    }
    creator = runtime_mcp_server.tool_definitions("chatgpt-creator", REGISTRY)

    assert len(runtime_mcp_server.EXECUTIVE_PROJECTION_TOOLS) == 11
    assert runtime_mcp_server.EXECUTIVE_READ_TOOLS == (
        runtime_mcp_server.EXECUTIVE_PROJECTION_TOOLS | {"context_snapshot"}
    )
    assert runtime_mcp_server.EXECUTIVE_READ_TOOLS <= set(
        runtime_mcp_server.mcp_server.TOOLS
    )
    assert set(runtime_mcp_server.CONTROL_CAPABILITIES) <= executive
    assert division == {
        "context_snapshot",
        "propose_mission",
        "pause_mission",
        "resume_mission",
        "challenge",
        "escalate",
    }
    assert "request_audit" not in division
    assert creator == []
    exposed = executive | division
    assert "wake_chatgpt" not in exposed
    assert not exposed.intersection(
        {
            "architect_dev",
            "repository_write",
            "git_write",
            "test_execution",
            "service_control",
            "credential_read",
            "write_file",
            "shell_exec",
        }
    )


def test_division_snapshot_excludes_untagged_and_other_division_rows(monkeypatch) -> None:
    monkeypatch.setattr(config, "IDENTITY_REGISTRY", REGISTRY)
    monkeypatch.setattr(
        projection,
        "system_state",
        lambda: _surface("system_state", {"autonomy_level": "A0"}),
    )
    monkeypatch.setattr(
        projection,
        "system_health",
        lambda: _surface(
            "system_health",
            {
                "gateway_running": True,
                "cognitive_lane_stale_min": 0,
                "bridge_seq_last": 12,
                "event_backlog": 0,
                "active_alarms": [{"secret": "cross-division"}],
                "cron": [{"name": "private"}],
            },
        ),
    )
    monkeypatch.setattr(
        projection,
        "active_missions",
        lambda status="any": _surface(
            "active_missions",
            [
                {"mission_id": "M-001", "division_id": "DIVISION-01"},
                {"mission_id": "M-002", "division_id": "DIVISION-02"},
                {"mission_id": "M-003"},
            ],
        ),
    )
    monkeypatch.setattr(
        projection,
        "recent_events",
        lambda since_seq=0, limit=20, min_class="INFO": _surface(
            "recent_events",
            {
                "events": [
                    {"event_id": "E-1", "division_id": "DIVISION-01"},
                    {"event_id": "E-2", "division_id": "DIVISION-02"},
                    {"event_id": "E-3"},
                ],
                "since_seq": since_seq,
                "next_seq": 3,
                "truncated": False,
            },
        ),
    )
    monkeypatch.setattr(projection, "_decision_evidence_refs", lambda limit=20, division_id=None: [])

    result = projection.context_snapshot(
        "division-head-division01",
        "single_division",
        0,
        20,
    )
    assert result["principal"]["principal_id"] == "division-head-division01"
    assert [row["mission_id"] for row in result["data"]["active_missions"]] == ["M-001"]
    assert [row["event_id"] for row in result["data"]["recent_events"]["events"]] == ["E-1"]
    assert "active_alarms" not in result["data"]["system_health"]
    assert "cron" not in result["data"]["system_health"]


def test_division_mission_proposal_commits_through_state_manager_and_routes_hermes(
    monkeypatch,
) -> None:
    source = _signed_division_snapshot(monkeypatch)
    captured: dict = {}

    def writer(normalized: dict) -> dict:
        captured.update(normalized)
        return {
            "record": {
                "decision_id": "D-TEST-1",
                "ts": "2026-08-22T03:01:00+00:00",
                "request_id": normalized["request_id"],
            },
            "replayed": False,
        }

    result = runtime_mcp_server.call_tool(
        "propose_mission",
        {
            "request_id": "REQ-DIV01-0001",
            "source_snapshot": source,
            "mission_id": "M-001",
            "goal": "Produce one bounded offer for a Founder-approved buyer segment",
            "buyer_path": "Founder-approved outreach to one verified buyer",
            "kill_criteria": ["Stop after ten qualified rejections and zero payment"],
            "reason": "Cheapest bounded validation after foundation acceptance",
            "evidence_refs": [],
            "assumptions": ["No market contact occurs without Founder approval"],
        },
        principal_id="division-head-division01",
        writer=writer,
        now=NOW + dt.timedelta(minutes=1),
        registry_path=REGISTRY,
        rate_limit=runtime_mcp_server.mcp_server.RateLimit(),
    )
    payload = json.loads(result["content"][0]["text"])
    assert result.get("isError") is False
    assert payload["status"] == "committed"
    assert payload["writer"] == "die-state-manager"
    assert payload["route"]["next_owner"] == "hermes-operator"
    assert captured["object"]["buyer_path"]
    assert captured["object"]["kill_criteria"]
    assert captured["object"]["division_id"] == "DIVISION-01"


def test_control_rejects_missing_economic_gate_and_raw_access(monkeypatch) -> None:
    source = _signed_division_snapshot(monkeypatch)
    base = {
        "request_id": "REQ-DIV01-0002",
        "source_snapshot": source,
        "mission_id": "M-001",
        "goal": "Prepare a bounded offer",
        "reason": "Test rejection",
        "evidence_refs": [],
    }
    missing = runtime_mcp_server.call_tool(
        "propose_mission",
        base,
        principal_id="division-head-division01",
        writer=lambda normalized: {},
        registry_path=REGISTRY,
    )
    assert missing["isError"] is True
    assert missing["content"][0]["text"].startswith("E_MCP_INPUT_INVALID:")

    raw = dict(base)
    raw.update(
        {
            "buyer_path": "Inspect ../private before outreach",
            "kill_criteria": ["Stop on first scope breach"],
        }
    )
    denied = runtime_mcp_server.call_tool(
        "propose_mission",
        raw,
        principal_id="division-head-division01",
        writer=lambda normalized: {},
        registry_path=REGISTRY,
    )
    assert denied["isError"] is True
    assert denied["content"][0]["text"].startswith("E_NO_RAW_ACCESS:")


def test_creator_contract_requires_durable_artifact_and_evidence_handoff() -> None:
    creator = (ROOT / "IDENTITY" / "chatgpt-creator.md").read_text(encoding="utf-8")
    worker = (ROOT / "PROTOCOLS" / "worker-contract-v0.md").read_text(encoding="utf-8")
    creator_words = " ".join(creator.lower().split())
    assert '"artifact_path"' in creator
    assert '"evidence_ref"' in creator
    assert "relative to the assigned workspace" in creator
    assert "visible output without durable workspace export is not an artifact" in creator_words
    assert '"artifact"' in worker and '"evidence"' in worker


def test_runtime_token_is_required_and_never_derived_from_repository(monkeypatch) -> None:
    monkeypatch.delenv("DIE_MCP_TOKEN", raising=False)
    monkeypatch.delenv("OPERATOR_TOKEN", raising=False)
    try:
        runtime_mcp_server._runtime_token()
    except runtime_mcp_server.RuntimeMcpError as exc:
        assert exc.code == "E_RUNTIME_TOKEN_REQUIRED"
    else:
        raise AssertionError("runtime token must fail closed")
    monkeypatch.setenv("OPERATOR_TOKEN", "o" * 32)
    assert runtime_mcp_server._runtime_token() == "o" * 32


def test_runtime_bindings_are_principal_pinned_and_avoid_infrastructure_ports() -> None:
    assert runtime_mcp_server.runtime_port("chatgpt-plus-executive") == 8791
    assert runtime_mcp_server.runtime_port("division-head-division01") == 8792
    assert len(set(runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS.values())) == 2
    assert not (
        set(runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS.values())
        & runtime_mcp_server.INFRASTRUCTURE_RESERVED_PORTS
    )
    assert runtime_mcp_server.runtime_port(
        "chatgpt-plus-executive",
        18787,
    ) == 18787


def test_runtime_binding_rejects_creator_invalid_and_reserved_ports() -> None:
    cases = (
        ("chatgpt-creator", None, "E_RUNTIME_BINDING_MISSING"),
        ("chatgpt-plus-executive", 8787, "E_RUNTIME_PORT_RESERVED"),
        ("division-head-division01", 8789, "E_RUNTIME_PORT_RESERVED"),
        ("division-head-division01", 8790, "E_RUNTIME_PORT_RESERVED"),
        ("chatgpt-plus-executive", 80, "E_RUNTIME_PORT_INVALID"),
        ("division-head-division01", True, "E_RUNTIME_PORT_INVALID"),
    )
    for principal_id, port, expected_code in cases:
        try:
            runtime_mcp_server.runtime_port(principal_id, port)
        except runtime_mcp_server.RuntimeMcpError as exc:
            assert exc.code == expected_code
        else:
            raise AssertionError(f"binding must reject {principal_id} on {port}")
