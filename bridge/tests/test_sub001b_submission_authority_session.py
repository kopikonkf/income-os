from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "company" / "schemas" / "die.asset.submission-authority.v1.schema.json"
SESSION = ROOT / "company" / "schemas" / "die.asset.submission-session-boundary.v1.schema.json"
DOC = ROOT / "docs" / "operations" / "SUBMISSION_AUTHORITY_SESSION_BOUNDARY_V1.md"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_sub001b_authority_is_exact_founder_package_route_scope() -> None:
    schema = _load(AUTHORITY)
    props = schema["properties"]
    assert props["schema_version"]["const"] == "die.asset.submission-authority.v1"
    assert props["decision"]["enum"] == ["AUTHORIZE_SUBMISSION", "DENY_SUBMISSION"]
    assert props["authority_class"] == {"const": "FOUNDER_EXPLICIT"}
    assert {"package_sha256", "route_id", "platform_profile_sha256", "decision", "authority_class"} <= set(schema["required"])
    scope = props["scope"]["properties"]
    assert scope["package_locked"] == {"const": True}
    assert scope["route_locked"] == {"const": True}
    assert scope["single_submission_attempt"] == {"const": True}


def test_sub001b_authority_forbids_credential_and_implicit_delegation_paths() -> None:
    props = _load(AUTHORITY)["properties"]["credential_boundary"]["properties"]
    assert props["credentials_embedded"] == {"const": False}
    assert props["credential_material_logged"] == {"const": False}
    assert props["cookie_token_extraction_allowed"] == {"const": False}
    assert props["protection_bypass_allowed"] == {"const": False}
    assert props["implicit_delegation_allowed"] == {"const": False}


def test_sub001b_session_is_non_secret_observation_and_recreated_interactively() -> None:
    schema = _load(SESSION)
    props = schema["properties"]
    assert props["schema_version"]["const"] == "die.asset.submission-session-boundary.v1"
    assert props["session_state"]["enum"] == ["UNAVAILABLE", "READY", "EXPIRED", "REAUTH_REQUIRED"]
    assert props["session_mode"]["enum"] == ["EXTERNAL_INTERACTIVE", "EXTERNAL_PROFILE_SESSION"]
    boundary = props["credential_boundary"]["properties"]
    assert boundary["credential_material_present"] == {"const": False}
    assert boundary["credential_material_persisted_by_die"] == {"const": False}
    assert boundary["cookie_token_extraction_allowed"] == {"const": False}
    assert boundary["protection_bypass_allowed"] == {"const": False}
    assert boundary["session_may_be_recreated_interactively"] == {"const": True}
    forbidden_names = {"password", "api_key", "cookie", "token", "secret"}
    assert forbidden_names.isdisjoint(props)


def test_sub001b_doc_keeps_session_separate_from_submission_authority() -> None:
    doc = DOC.read_text(encoding="utf-8")
    for marker in [
        "package existence never implies authority",
        "explicit Founder authority receipt",
        "does not submit",
        "does not publish",
        "Credentials remain external",
        "extracting cookies or tokens",
        "treating an authenticated session as submission authority",
        "No condition above may be repaired by implicit delegation or blind retry",
    ]:
        assert marker in doc


def test_sub001b_graph_is_pre_acceptance_until_validation_seal() -> None:
    tasks = {row["id"]: row for row in _load(GRAPH)["tasks"]}
    assert tasks["SUB-001A"]["status"] == "DONE"
    assert tasks["SUB-001B"]["status"] in {"READY", "DONE"}
    assert tasks["SUB-001C"]["status"] in {"BLOCKED", "READY"}
