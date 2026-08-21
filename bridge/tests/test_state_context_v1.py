"""P5 v1: authority, context snapshot, provenance, evidence, and freshness."""

from __future__ import annotations

import datetime as dt

import pytest

from income_os_bridge import authority, mcp_server, projection, snapshot, state_request

NOW = dt.datetime(2026, 8, 21, 1, 0, tzinfo=dt.timezone.utc)


def surface(name: str, data: object, trust: str = "VERIFIED") -> dict:
    return {
        "surface": name,
        "as_of": "2026-08-21T01:00:00Z",
        "completeness": "complete",
        "source_trust": trust,
        "sources": [f"file:{name}.json"],
        "notes": [],
        "data": data,
    }


def executive_authority() -> dict:
    return authority.authorize(
        "chatgpt-plus-executive",
        "context.snapshot.read",
        "company_portfolio",
    )


def fresh_snapshot() -> dict:
    return snapshot.build(
        executive_authority(),
        {
            "system_state": surface("system_state", {"autonomy_level": "A0"}),
            "recent_events": surface(
                "recent_events",
                {
                    "events": [{"event_id": "E-000280", "seq": 280}],
                    "since_seq": 279,
                    "next_seq": 280,
                    "truncated": False,
                },
            ),
        },
        [
            {
                "evidence_id": "EVREF-D-0018",
                "kind": "decision_support",
                "ref": "workspaces/T-0002/evidence.txt",
                "claim": "Supports decision D-0018",
                "trust": "ASSUMED",
                "observed_at": "2026-08-21T00:30:00Z",
            }
        ],
        now=NOW,
        ttl_s=900,
    )


def test_registry_authorizes_executive_snapshot() -> None:
    granted = executive_authority()
    assert granted["capability"] == "semantic_observation"
    assert granted["scope"] == "company_portfolio"


def test_registry_rejects_unknown_principal_and_uninstantiated_template() -> None:
    with pytest.raises(authority.AuthorizationError) as unknown:
        authority.authorize("unknown-agent", "context.snapshot.read")
    assert unknown.value.code == "E_UNAUTHORIZED_PRINCIPAL"

    with pytest.raises(authority.AuthorizationError) as template:
        authority.authorize("division-head-template", "context.snapshot.read")
    assert template.value.code == "E_UNINSTANTIATED_TEMPLATE"


def test_snapshot_is_versioned_typed_bounded_and_fresh() -> None:
    result = fresh_snapshot()
    assert result["schema_version"] == "die.context.snapshot.v1"
    assert result["snapshot_version"] == 1
    assert result["snapshot_id"].startswith("SNAP-")
    assert result["principal"]["principal_id"] == "chatgpt-plus-executive"
    assert result["source_cursor"]["events_next_seq"] == 280
    assert result["provenance"][0]["type"] == "file"
    assert result["evidence_refs"][0]["kind"] == "decision_support"
    assert result["freshness"]["ttl_s"] == 900
    assert snapshot.assert_fresh(result, now=NOW + dt.timedelta(seconds=899)) is result


def test_expired_snapshot_is_rejected() -> None:
    result = fresh_snapshot()
    with pytest.raises(snapshot.SnapshotError) as stale:
        snapshot.assert_fresh(result, now=NOW + dt.timedelta(seconds=900))
    assert stale.value.code == "E_STALE_SNAPSHOT"


def test_projection_builds_only_authorized_semantic_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        projection,
        "system_state",
        lambda: surface("system_state", {"autonomy_level": "A0"}),
    )
    monkeypatch.setattr(
        projection,
        "system_health",
        lambda: surface("system_health", {"gateway_running": True}),
    )
    monkeypatch.setattr(
        projection,
        "active_missions",
        lambda status="any": surface("active_missions", []),
    )
    monkeypatch.setattr(
        projection,
        "recent_events",
        lambda since_seq=0, limit=20, min_class="INFO": surface(
            "recent_events",
            {
                "events": [],
                "since_seq": since_seq,
                "next_seq": since_seq,
                "truncated": False,
            },
        ),
    )
    monkeypatch.setattr(
        projection,
        "_jlines",
        lambda path, n=None: [
            {
                "decision_id": "D-TEST",
                "ts": "2026-08-21T00:30:00Z",
                "evidence_ref": "evidence/test.txt",
            }
        ],
    )

    result = projection.context_snapshot(
        "chatgpt-plus-executive",
        "company_portfolio",
        100,
        20,
    )
    assert result["data"]["system_health"]["gateway_running"] is True
    assert result["source_cursor"]["events_since_seq"] == 100
    assert result["evidence_refs"][0]["evidence_id"] == "EVREF-D-TEST"

    with pytest.raises(authority.AuthorizationError) as denied:
        projection.context_snapshot("founder", "company", 0, 20)
    assert denied.value.code == "E_FORBIDDEN_ACTION"


def test_semantic_decision_request_is_validated_not_committed() -> None:
    source = fresh_snapshot()
    request = {
        "schema_version": "die.state.request.v1",
        "request_id": "REQ-EXEC-0001",
        "principal_id": "chatgpt-plus-executive",
        "scope": "company_portfolio",
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": {
            "decision_class": "NOW",
            "recommendation": "Run the cheapest falsification experiment",
        },
        "source_snapshot": source,
        "evidence_refs": source["evidence_refs"],
        "assumptions": ["Market response is not yet verified"],
    }

    result = state_request.validate_and_normalize(
        request,
        now=NOW + dt.timedelta(minutes=5),
    )

    assert result["accepted"] is True
    assert result["commit_status"] == "validated_not_committed"
    assert result["writer"] == "die-state-manager"
    assert result["normalized"]["source_snapshot"]["snapshot_id"] == source["snapshot_id"]


def test_semantic_request_rejects_stale_snapshot() -> None:
    source = fresh_snapshot()
    request = {
        "schema_version": "die.state.request.v1",
        "request_id": "REQ-EXEC-0002",
        "principal_id": "chatgpt-plus-executive",
        "scope": "company_portfolio",
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": {"decision_class": "NEXT"},
        "source_snapshot": source,
        "evidence_refs": [],
    }

    with pytest.raises(state_request.StateRequestError) as rejected:
        state_request.validate_and_normalize(
            request,
            now=NOW + dt.timedelta(minutes=16),
        )
    assert rejected.value.code == "E_STALE_SNAPSHOT"


def test_mcp_returns_authority_error_not_generic_degradation() -> None:
    result = mcp_server.call_tool(
        "context_snapshot",
        {"principal_id": "unknown-agent"},
    )
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("E_UNAUTHORIZED_PRINCIPAL:")



def test_decision_reader_accepts_utf8_bom(tmp_path) -> None:
    path = tmp_path / "DECISIONS.jsonl"
    path.write_bytes(
        b'\xef\xbb\xbf{"decision_id":"D-BOM","evidence_ref":"evidence/bom.txt"}\n'
    )
    assert projection._jlines(path)[0]["decision_id"] == "D-BOM"


def test_snapshot_propagates_truncated_source_status() -> None:
    recent = surface(
        "recent_events",
        {"events": [], "since_seq": 0, "next_seq": 0, "truncated": True},
    )
    recent["completeness"] = "truncated"
    result = snapshot.build(
        executive_authority(),
        {"recent_events": recent},
        now=NOW,
    )
    assert result["completeness"] == "truncated"



def test_evidence_reference_removes_host_absolute_paths(monkeypatch) -> None:
    monkeypatch.setattr(
        projection,
        "_jlines",
        lambda path, n=None: [
            {
                "decision_id": "D-PATH",
                "ts": "2026-08-21T00:30:00Z",
                "evidence_ref": r"C:\DIE\bridge\report.md;D:\private\proof.txt",
            }
        ],
    )
    ref = projection._decision_evidence_refs()[0]["ref"]
    assert "C:" not in ref
    assert "D:" not in ref
    assert ref.startswith("repo:/bridge/report.md")
    assert "[PATH_REDACTED]" in ref


def test_jsonl_reader_skips_one_bad_line_without_losing_good_rows(tmp_path) -> None:
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        '{"decision_id":"D-GOOD-1"}\nnot-json\n{"decision_id":"D-GOOD-2"}\n',
        encoding="utf-8",
    )
    assert [row["decision_id"] for row in projection._jlines(path)] == [
        "D-GOOD-1",
        "D-GOOD-2",
    ]



def test_semantic_request_rejects_raw_host_path() -> None:
    source = fresh_snapshot()
    request = {
        "schema_version": "die.state.request.v1",
        "request_id": "REQ-EXEC-RAW1",
        "principal_id": "chatgpt-plus-executive",
        "scope": "company_portfolio",
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": {"recommendation": r"Inspect C:\DIE\state\EVENTS.jsonl"},
        "source_snapshot": source,
        "evidence_refs": [],
    }

    with pytest.raises(state_request.StateRequestError) as rejected:
        state_request.validate_and_normalize(
            request,
            now=NOW + dt.timedelta(minutes=1),
        )
    assert rejected.value.code == "E_NO_RAW_ACCESS"
