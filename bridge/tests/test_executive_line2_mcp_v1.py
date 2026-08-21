"""Executive Line 2 MCP v1 transport and P5/P6 composition tests."""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from income_os_bridge import authority, executive_mcp_server, snapshot

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))
import die_event  # noqa: E402

NOW = dt.datetime(2026, 8, 21, 5, 0, tzinfo=dt.timezone.utc)
TEST_SIGNING_KEY = "executive-line2-test-key-" + ("x" * 48)


@pytest.fixture(autouse=True)
def signed_snapshot_runtime(monkeypatch) -> None:
    monkeypatch.setenv("DIE_SNAPSHOT_HMAC_KEY", TEST_SIGNING_KEY)
    monkeypatch.setenv("DIE_SNAPSHOT_HMAC_KEY_ID", "executive-line2-test-v1")


def surface(name: str, data: object) -> dict:
    return {
        "surface": name,
        "as_of": "2026-08-21T05:00:00Z",
        "completeness": "complete",
        "source_trust": "VERIFIED",
        "sources": [f"repo:/evidence/{name}.json"],
        "notes": [],
        "data": data,
    }


def fresh_snapshot(now: dt.datetime = NOW) -> dict:
    granted = authority.authorize(
        "chatgpt-plus-executive",
        "context.snapshot.read",
        "company_portfolio",
    )
    return snapshot.build(
        granted,
        {
            "system_state": surface("system_state", {"autonomy_level": "A0"}),
            "recent_events": surface(
                "recent_events",
                {
                    "events": [],
                    "since_seq": 320,
                    "next_seq": 321,
                    "truncated": False,
                },
            ),
        },
        [
            {
                "evidence_id": "EVREF-EXEC-L2-001",
                "kind": "decision_support",
                "ref": "repo:/evidence/executive-line2-proof.json",
                "claim": "The bounded experiment is ready for a decision",
                "trust": "VERIFIED",
                "observed_at": now.isoformat(
                    timespec="seconds"
                ).replace("+00:00", "Z"),
            }
        ],
        now=now,
    )


def arguments(now: dt.datetime = NOW) -> dict:
    source = fresh_snapshot(now)
    return {
        "request_id": "REQ-EXEC-L2-0001",
        "source_snapshot": source,
        "decision": {
            "decision_class": "strategy",
            "choice": "Run the bounded falsification experiment",
            "reason": "It limits cost before scaling",
            "alternatives_rejected": ["Build the complete product first"],
        },
        "evidence_refs": source["evidence_refs"],
        "assumptions": ["External market response is not yet verified"],
    }


def receipt(normalized: dict, replayed: bool = False) -> dict:
    return {
        "record": {
            "decision_id": "D-TEST",
            "ts": "2026-08-21T05:01:00+00:00",
            "request_id": normalized["request_id"],
        },
        "replayed": replayed,
    }


def unlimited() -> executive_mcp_server.MutationRateLimit:
    return executive_mcp_server.MutationRateLimit(limit=1000)


def test_tools_list_exposes_one_business_capability_and_no_identity_override() -> None:
    response = executive_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        writer=None,
    )
    tools = response["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["decision_submit"]
    schema = tools[0]["inputSchema"]
    assert schema["additionalProperties"] is False
    assert "principal_id" not in schema["properties"]
    assert "scope" not in schema["properties"]
    assert tools[0]["annotations"]["readOnlyHint"] is False
    assert tools[0]["annotations"]["idempotentHint"] is True


def test_submit_pins_executive_identity_and_composes_p5_p6() -> None:
    captured = {}

    def writer(normalized: dict) -> dict:
        captured.update(normalized)
        return receipt(normalized)

    result = executive_mcp_server.submit_decision(
        arguments(),
        writer=writer,
        now=NOW + dt.timedelta(minutes=1),
    )
    assert result["status"] == "committed"
    assert result["route"]["next_owner"] == "hermes-operator"
    assert captured["principal_id"] == "chatgpt-plus-executive"
    assert captured["scope"] == "company_portfolio"
    assert captured["authority"]["action"] == "state.decision.submit"
    assert captured["object_type"] == "DECISION"


def test_transport_rejects_identity_spoofing_and_raw_access() -> None:
    spoofed = arguments()
    spoofed["principal_id"] = "founder"
    rejected = executive_mcp_server.submit_decision(
        spoofed,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=1),
    )
    assert rejected["error"]["code"] == "E_MCP_INPUT_INVALID"

    raw = arguments()
    raw["decision"]["reason"] = r"Inspect C:\DIE\state\DECISIONS.jsonl"
    rejected = executive_mcp_server.submit_decision(
        raw,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=1),
    )
    assert rejected["error"]["code"] == "E_NO_RAW_ACCESS"


def test_unsigned_snapshot_fails_closed_without_calling_writer(monkeypatch) -> None:
    payload = arguments()
    monkeypatch.delenv("DIE_SNAPSHOT_HMAC_KEY")
    monkeypatch.delenv("DIE_SNAPSHOT_HMAC_KEY_ID")
    called = False

    def writer(normalized: dict) -> dict:
        nonlocal called
        called = True
        return receipt(normalized)

    result = executive_mcp_server.submit_decision(
        payload,
        writer=writer,
        now=NOW + dt.timedelta(minutes=1),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_SNAPSHOT_UNTRUSTED"
    assert called is False


def test_jsonrpc_non_object_params_fail_closed() -> None:
    response = executive_mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": ["not", "an", "object"],
        },
        writer=None,
    )
    assert response["error"]["code"] == -32602


def test_unknown_tool_and_rate_limit_fail_before_writer() -> None:
    unknown = executive_mcp_server.call_tool(
        "filesystem_write",
        {},
        writer=None,
        rate_limit=unlimited(),
    )
    assert unknown["isError"] is True
    unknown_body = json.loads(unknown["content"][0]["text"])
    assert unknown_body["error"]["code"] == "E_MCP_TOOL_NOT_FOUND"

    limiter = executive_mcp_server.MutationRateLimit(limit=1)
    first = executive_mcp_server.call_tool(
        "decision_submit",
        arguments(),
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=1),
        rate_limit=limiter,
    )
    second = executive_mcp_server.call_tool(
        "decision_submit",
        arguments(),
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=1),
        rate_limit=limiter,
    )
    assert first["isError"] is False
    assert json.loads(second["content"][0]["text"])["error"]["code"] == (
        "E_MCP_RATE_LIMIT"
    )


def test_append_only_commit_is_replay_safe_and_does_not_change_events(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(die_event, "STATE", tmp_path)
    events = tmp_path / "EVENTS.jsonl"
    events.write_text('{"seq":1,"event_id":"E-000001"}\n', encoding="utf-8")
    before_events = events.read_bytes()

    payload = arguments()
    first = executive_mcp_server.submit_decision(
        payload,
        writer=die_event.commit_normalized_decision,
        now=NOW + dt.timedelta(minutes=1),
    )
    second = executive_mcp_server.submit_decision(
        payload,
        writer=die_event.commit_normalized_decision,
        now=NOW + dt.timedelta(minutes=1),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "DECISIONS.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert len(rows) == 1
    assert first["canonical_mutation"] is True
    assert second["canonical_mutation"] is False
    assert second["commit"]["record_id"] == first["commit"]["record_id"]
    assert events.read_bytes() == before_events


def test_stdio_mcp_round_trip_uses_isolated_state(tmp_path) -> None:
    die_home = tmp_path / "die-home"
    (die_home / "company").mkdir(parents=True)
    (die_home / "state").mkdir()
    shutil.copy(
        ROOT / "company" / "identity-registry.json",
        die_home / "company" / "identity-registry.json",
    )
    events = die_home / "state" / "EVENTS.jsonl"
    events.write_text('{"seq":1,"event_id":"E-000001"}\n', encoding="utf-8")
    before_events = events.read_bytes()

    realtime = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    payload = arguments(realtime)
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "decision_submit", "arguments": payload},
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "decision_submit", "arguments": payload},
        },
    ]
    stdin = "\n".join(json.dumps(row) for row in messages) + "\n"
    env = os.environ.copy()
    env["DIE_HOME"] = str(die_home)
    env["DIE_SNAPSHOT_HMAC_KEY"] = TEST_SIGNING_KEY
    env["DIE_SNAPSHOT_HMAC_KEY_ID"] = "executive-line2-test-v1"

    completed = subprocess.run(
        [sys.executable, str(BIN / "die_executive_mcp.py")],
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        cwd=ROOT,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert responses[0]["result"]["serverInfo"]["name"] == "die-executive-line2"
    assert [tool["name"] for tool in responses[1]["result"]["tools"]] == [
        "decision_submit"
    ]

    first = json.loads(responses[2]["result"]["content"][0]["text"])
    second = json.loads(responses[3]["result"]["content"][0]["text"])
    assert first["status"] == "committed"
    assert first["canonical_mutation"] is True
    assert second["commit"]["record_id"] == first["commit"]["record_id"]
    assert second["canonical_mutation"] is False
    assert len(
        (die_home / "state" / "DECISIONS.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ) == 1
    assert events.read_bytes() == before_events
