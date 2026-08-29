"""Runtime Canon Context Projection v1 regression contract."""

from __future__ import annotations

import copy
import datetime as dt
import json
import shutil
from pathlib import Path

import pytest

from income_os_bridge import (
    authority,
    canon_context,
    config,
    mcp_server,
    projection,
    runtime_mcp_server,
    snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "company" / "identity-registry.json"
MANIFEST = ROOT / "company" / "runtime-canon-context-v1.json"
REPO_SHA = "4e3cf11e2095453c94562e0dfa1cdd731275784e"
NOW = dt.datetime(2026, 8, 24, 8, 0, tzinfo=dt.timezone.utc)


def _grant(principal_id: str, scope: str) -> dict:
    return authority.authorize(
        principal_id,
        "context.snapshot.read",
        scope,
        REGISTRY,
    )


def _surface(name: str, data: object) -> dict:
    return {
        "surface": name,
        "as_of": "2026-08-24T08:00:00Z",
        "completeness": "complete",
        "source_trust": "VERIFIED",
        "sources": [f"semantic:{name}"],
        "notes": [],
        "data": data,
    }


def _copy_canon_fixture(target: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    paths = ["company/runtime-canon-context-v1.json"] + [
        row["path"] for row in manifest["source_documents"]
    ]
    for relative in paths:
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def _patch_semantic_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projection,
        "system_state",
        lambda: _surface("system_state", {"autonomy_level": "A0"}),
    )
    monkeypatch.setattr(
        projection,
        "system_health",
        lambda: _surface("system_health", {"gateway_running": True}),
    )
    monkeypatch.setattr(
        projection,
        "active_missions",
        lambda status="any": _surface(
            "active_missions",
            [{"mission_id": "M-001", "division_id": "DIVISION-01"}],
        ),
    )
    monkeypatch.setattr(
        projection,
        "recent_events",
        lambda since_seq=0, limit=20, min_class="INFO": _surface(
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
        "_decision_evidence_refs",
        lambda limit=20, division_id=None: [],
    )


@pytest.mark.parametrize(
    ("principal_id", "scope", "role_fact"),
    [
        ("chatgpt-plus-executive", "company_portfolio", "EXECUTIVE-ROLE"),
        ("division-head-division01", "single_division", "DIVISION01-ROLE"),
    ],
)
def test_hash_pinned_role_scoped_projection_is_verified(
    monkeypatch: pytest.MonkeyPatch,
    principal_id: str,
    scope: str,
    role_fact: str,
) -> None:
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)

    result = canon_context.build_surface(
        _grant(principal_id, scope),
        now=NOW,
        root=ROOT,
    )
    data = result["data"]

    assert result["source_trust"] == "VERIFIED"
    assert data["load_status"] == "VERIFIED"
    assert data["principal_id"] == principal_id
    assert data["scope"] == scope
    assert data["repository"] == {"sha": REPO_SHA, "source": "DIE_REPO_SHA"}
    assert [row["doc_id"] for row in data["required_documents"]] == [
        "pipeline",
        "atlas",
        "atlas_crossjoin_complement",
        "blueprint",
    ]
    assert [row["doc_id"] for row in data["supporting_documents"]] == [
        "platform_matrix",
        "quantity_workbook",
    ]
    assert all(row["load_status"] == "VERIFIED" for row in (
        data["required_documents"] + data["supporting_documents"]
    ))
    assert role_fact in {row["fact_id"] for row in data["decision_facts"]}
    assert data["matrix_digest"]["acceptance_estimate_status"] == "HYPOTHESIS"
    assert data["workbook_digest"]["classification"] == "HYPOTHESIS"
    assert data["workbook_digest"]["model_status"] == "FORMULA_MECHANICS_PASS"


def test_projection_is_bounded_and_contains_no_raw_documents_or_host_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)
    result = canon_context.build_surface(
        _grant("chatgpt-plus-executive", "company_portfolio"),
        now=NOW,
        root=ROOT,
    )
    encoded = json.dumps(result, ensure_ascii=False).encode("utf-8")

    assert len(encoded) <= config.CANON_CONTEXT_MAX_BYTES
    assert str(ROOT) not in encoded.decode("utf-8")
    assert r"C:\DIE" not in encoded.decode("utf-8")
    assert "raw_content" not in encoded.decode("utf-8")
    assert set(result["data"]) == {
        "schema_version",
        "profile_id",
        "principal_id",
        "scope",
        "repository",
        "manifest",
        "load_status",
        "generated_at",
        "required_documents",
        "supporting_documents",
        "decision_facts",
        "matrix_digest",
        "workbook_digest",
        "receipt_contract",
    }


def test_changed_source_hash_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _copy_canon_fixture(tmp_path)
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)
    atlas = tmp_path / canon_context.ALLOWED_DOCUMENTS["atlas"]
    atlas.write_text(atlas.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    with pytest.raises(canon_context.CanonContextError) as rejected:
        canon_context.build_surface(
            _grant("division-head-division01", "single_division"),
            root=tmp_path,
        )
    assert rejected.value.code == "E_CANON_HASH_MISMATCH"


def test_manifest_cannot_add_an_unallowlisted_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _copy_canon_fixture(tmp_path)
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)
    path = tmp_path / "company" / "runtime-canon-context-v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["source_documents"].append(
        {
            "doc_id": "raw_state",
            "path": "state/DECISIONS.jsonl",
            "sha256": "0" * 64,
            "classification": "CANON",
        }
    )
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(canon_context.CanonContextError) as rejected:
        canon_context.build_surface(
            _grant("chatgpt-plus-executive", "company_portfolio"),
            root=tmp_path,
        )
    assert rejected.value.code == "E_CANON_INVALID"


def test_signed_snapshot_covers_canon_context_and_detects_fact_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "DIE_HOME", ROOT)
    monkeypatch.setattr(config, "IDENTITY_REGISTRY", REGISTRY)
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)
    monkeypatch.setenv(snapshot.SIGNING_KEY_ENV, "k" * 32)
    monkeypatch.setenv(snapshot.SIGNING_KEY_ID_ENV, "canon-test-v1")
    _patch_semantic_surfaces(monkeypatch)

    result = projection.context_snapshot(
        "division-head-division01",
        "single_division",
        0,
        20,
    )
    assert result["data"]["canon_context"]["load_status"] == "VERIFIED"
    assert result["integrity"]["key_id"] == "canon-test-v1"
    assert snapshot.assert_trusted(result, signing_key="k" * 32) is result

    tampered = copy.deepcopy(result)
    tampered["data"]["canon_context"]["decision_facts"][0]["statement"] += " altered"
    with pytest.raises(snapshot.SnapshotError) as rejected:
        snapshot.assert_integrity(tampered)
    assert rejected.value.code == "E_SNAPSHOT_INTEGRITY"


def test_mcp_reports_typed_canon_failure_instead_of_generic_degradation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _copy_canon_fixture(tmp_path)
    monkeypatch.setattr(config, "DIE_HOME", tmp_path)
    monkeypatch.setattr(config, "IDENTITY_REGISTRY", REGISTRY)
    monkeypatch.setenv("DIE_REPO_SHA", REPO_SHA)
    atlas = tmp_path / canon_context.ALLOWED_DOCUMENTS["atlas"]
    atlas.write_text(atlas.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    result = mcp_server.call_tool(
        "context_snapshot",
        {
            "principal_id": "chatgpt-plus-executive",
            "scope": "company_portfolio",
        },
    )
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("E_CANON_HASH_MISMATCH:")


def test_runtime_tool_registry_is_unchanged() -> None:
    executive = runtime_mcp_server.tool_definitions(
        "chatgpt-plus-executive",
        REGISTRY,
    )
    division = runtime_mcp_server.tool_definitions(
        "division-head-division01",
        REGISTRY,
    )

    assert len(executive) == 18
    assert len(division) == 6
    assert "canon_context" not in {row["name"] for row in executive + division}
    assert "context_snapshot" in {row["name"] for row in executive}
    assert "context_snapshot" in {row["name"] for row in division}
