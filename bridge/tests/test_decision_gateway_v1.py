"""P6 v1: stateless Decision Gateway and sole-writer commit contract."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

import pytest

from income_os_bridge import (
    authority,
    decision_gateway,
    snapshot,
    state_request,
)

BIN = pathlib.Path(__file__).resolve().parents[2] / "bin"
sys.path.insert(0, str(BIN))
import die_event  # noqa: E402
import die_decision_gateway as gateway_cli  # noqa: E402
import die_state_request as state_request_cli  # noqa: E402

NOW = dt.datetime(2026, 8, 21, 3, 0, tzinfo=dt.timezone.utc)
TEST_SIGNING_KEY = "p6-test-key-" + ("x" * 48)


@pytest.fixture(autouse=True)
def signed_snapshot_runtime(monkeypatch) -> None:
    monkeypatch.setenv("DIE_SNAPSHOT_HMAC_KEY", TEST_SIGNING_KEY)
    monkeypatch.setenv("DIE_SNAPSHOT_HMAC_KEY_ID", "p6-test-v1")



def surface(name: str, data: object) -> dict:
    return {
        "surface": name,
        "as_of": "2026-08-21T03:00:00Z",
        "completeness": "complete",
        "source_trust": "VERIFIED",
        "sources": [f"file:{name}.json"],
        "notes": [],
        "data": data,
    }


def fresh_snapshot() -> dict:
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
                    "since_seq": 300,
                    "next_seq": 301,
                    "truncated": False,
                },
            ),
        },
        [
            {
                "evidence_id": "EVREF-P6-001",
                "kind": "decision_support",
                "ref": "repo:/evidence/p6-proof.json",
                "claim": "The cheapest falsification experiment is bounded",
                "trust": "VERIFIED",
                "observed_at": "2026-08-21T03:00:00Z",
            }
        ],
        now=NOW,
    )


def raw_request() -> dict:
    source = fresh_snapshot()
    return {
        "schema_version": "die.state.request.v1",
        "request_id": "REQ-P6-0001",
        "principal_id": "chatgpt-plus-executive",
        "scope": "company_portfolio",
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": {
            "decision_class": "strategy",
            "choice": "Run the cheapest falsification experiment",
            "reason": "It minimizes cost before scaling",
            "alternatives_rejected": ["Build the full product before market evidence"],
        },
        "source_snapshot": source,
        "evidence_refs": source["evidence_refs"],
        "assumptions": ["Market response is not yet verified"],
    }


def normalized_wrapper() -> dict:
    return state_request.validate_and_normalize(
        raw_request(),
        now=NOW + dt.timedelta(minutes=1),
    )


def receipt(normalized: dict, replayed: bool = False) -> dict:
    return {
        "record": {
            "decision_id": "D-TEST",
            "ts": "2026-08-21T03:01:00+00:00",
            "request_id": normalized["request_id"],
        },
        "replayed": replayed,
    }


def test_line2_cli_loaders_accept_utf8_bom(tmp_path) -> None:
    path = tmp_path / "payload.json"
    path.write_bytes(b'\xef\xbb\xbf{"ok":true}\n')
    assert state_request_cli._load_payload(str(path)) == {"ok": True}
    assert gateway_cli._load_payload(str(path)) == {"ok": True}


def test_state_request_carries_snapshot_expiry_for_gateway() -> None:
    result = normalized_wrapper()
    assert result["normalized"]["source_snapshot"]["freshness"]["expires_at"] == (
        "2026-08-21T03:15:00Z"
    )


def test_gateway_commits_and_routes_only_to_hermes() -> None:
    captured = {}

    def writer(normalized: dict) -> dict:
        captured.update(normalized)
        return receipt(normalized)

    result = decision_gateway.process(
        normalized_wrapper(),
        writer=writer,
        now=NOW + dt.timedelta(minutes=2),
    )

    assert result["status"] == "committed"
    assert result["writer"] == "die-state-manager"
    assert result["canonical_mutation"] is True
    assert result["commit"]["record_id"] == "D-TEST"
    assert result["route"] == {
        "next_owner": "hermes-operator",
        "status": "ready_for_operational_acceptance",
    }
    assert captured["authority"]["action"] == "state.decision.submit"


def test_gateway_rejects_raw_unnormalized_request() -> None:
    result = decision_gateway.process(
        raw_request(),
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_GATEWAY_INPUT_INVALID"
    assert result["canonical_mutation"] is False


def test_gateway_rejects_stale_normalized_snapshot() -> None:
    result = decision_gateway.process(
        normalized_wrapper(),
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=15),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_STALE_SNAPSHOT"


def test_gateway_reauthorizes_and_rejects_tampering() -> None:
    payload = normalized_wrapper()
    payload["normalized"]["authority"]["capability"] = "capital_allocation"
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_GATEWAY_AUTHORITY_MISMATCH"


def test_gateway_rejects_unsigned_snapshot(monkeypatch) -> None:
    monkeypatch.delenv("DIE_SNAPSHOT_HMAC_KEY")
    monkeypatch.delenv("DIE_SNAPSHOT_HMAC_KEY_ID")
    payload = normalized_wrapper()
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_SNAPSHOT_UNTRUSTED"


def test_gateway_rejects_snapshot_signed_by_wrong_runtime_key(
    monkeypatch,
) -> None:
    payload = normalized_wrapper()
    monkeypatch.setenv("DIE_SNAPSHOT_HMAC_KEY", "wrong-key-" + ("z" * 48))
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_SNAPSHOT_UNTRUSTED"


def test_gateway_rejects_snapshot_content_tampering() -> None:
    payload = normalized_wrapper()
    payload["normalized"]["source_snapshot"]["data"]["system_state"][
        "autonomy_level"
    ] = "A9"
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_SNAPSHOT_INTEGRITY"


def test_gateway_rejects_evidence_absent_from_snapshot() -> None:
    payload = normalized_wrapper()
    payload["normalized"]["evidence_refs"][0]["evidence_id"] = "EVREF-FORGED"
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_EVIDENCE_INVALID"


def test_gateway_rejects_non_commit_ready_decision() -> None:
    payload = normalized_wrapper()
    del payload["normalized"]["object"]["reason"]
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_DECISION_INVALID"


def test_gateway_rechecks_normalized_payload_for_raw_access() -> None:
    payload = normalized_wrapper()
    payload["normalized"]["object"]["reason"] = (
        r"Inspect C:\DIE\state\DECISIONS.jsonl"
    )
    result = decision_gateway.process(
        payload,
        writer=lambda normalized: receipt(normalized),
        now=NOW + dt.timedelta(minutes=2),
    )
    assert result["status"] == "rejected"
    assert result["error"]["code"] == "E_NO_RAW_ACCESS"


def test_gateway_fails_closed_when_writer_is_unavailable_or_fails() -> None:
    unavailable = decision_gateway.process(
        normalized_wrapper(),
        writer=None,
        now=NOW + dt.timedelta(minutes=2),
    )
    assert unavailable["error"]["code"] == "E_STATE_WRITER_UNAVAILABLE"

    def broken_writer(_normalized: dict) -> dict:
        raise OSError("state unavailable")

    failed = decision_gateway.process(
        normalized_wrapper(),
        writer=broken_writer,
        now=NOW + dt.timedelta(minutes=2),
    )
    assert failed["error"]["code"] == "E_STATE_WRITER_FAILED"
    assert "state unavailable" not in failed["error"]["message"]


def test_state_manager_commit_is_append_only_and_replay_safe(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(die_event, "STATE", tmp_path)
    events = tmp_path / "EVENTS.jsonl"
    events.write_text('{"seq":1,"event_id":"E-000001"}\n', encoding="utf-8")
    before_events = events.read_bytes()

    payload = normalized_wrapper()
    first = decision_gateway.process(
        payload,
        writer=die_event.commit_normalized_decision,
        now=NOW + dt.timedelta(minutes=2),
    )
    second = decision_gateway.process(
        payload,
        writer=die_event.commit_normalized_decision,
        now=NOW + dt.timedelta(minutes=2),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "DECISIONS.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["schema_version"] == "die.decision.v1"
    assert rows[0]["request_id"] == "REQ-P6-0001"
    assert rows[0]["decider"] == "chatgpt-plus-executive"
    assert rows[0]["committed_by"] == "die-state-manager"
    assert rows[0]["source_snapshot"]["snapshot_id"].startswith("SNAP-")
    assert rows[0]["evidence_refs"][0]["evidence_id"] == "EVREF-P6-001"
    assert first["commit"]["replayed"] is False
    assert first["canonical_mutation"] is True
    assert second["commit"]["record_id"] == first["commit"]["record_id"]
    assert second["commit"]["replayed"] is True
    assert second["canonical_mutation"] is False
    assert events.read_bytes() == before_events
