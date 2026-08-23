"""Wake auth/session canon: secret boundary and thread governance regression."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))
import wake_division01 as wake  # noqa: E402


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_web_jwt_and_sentinel_token_never_cross_page_boundary() -> None:
    prepare = wake.JS_PREPARE
    assert "accessToken: sess.accessToken" not in prepare
    assert "reqToken: req.token" not in prepare
    assert "globalThis.__dieWakeReqToken = req.token" in prepare

    js = wake.build_wake_js(
        {
            "deviceId": "device-1",
            "accessToken": "MUST_NOT_CROSS",
            "reqToken": "MUST_NOT_CROSS_EITHER",
        },
        "safe briefing",
        "conversation-1",
        "proof-1",
    )
    assert "MUST_NOT_CROSS" not in js
    assert "MUST_NOT_CROSS_EITHER" not in js
    assert "fetch('/api/auth/session'" in js
    assert "globalThis.__dieWakeReqToken" in js


def test_generated_inpage_javascript_is_syntactically_valid() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    js = wake.build_wake_js(
        {"deviceId": "device-1"},
        "briefing",
        "conversation-1",
        "proof-1",
    )
    wrapped = "(async () => {\n" + js + "\nreturn __ret;\n})()"
    result = subprocess.run(
        [node, "--check", "-"],
        input=wrapped,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_thread_rotation_preserves_exactly_one_active_mapping(
    tmp_path,
    monkeypatch,
) -> None:
    state = tmp_path / "wake.json"
    monkeypatch.setattr(wake, "WAKE_JSON", state)
    monkeypatch.setattr(wake, "PRINCIPAL_ID", "division-head-division01")
    monkeypatch.setattr(wake, "DIVISION_ID", "DIVISION-01")

    wake.save_conv_id("thread-1")
    wake.save_conv_id("thread-2", previous="thread-1")

    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["schema_version"] == "die.wake.thread.v1"
    assert data["principal_id"] == "division-head-division01"
    assert data["division_id"] == "DIVISION-01"
    assert data["conversation_id"] == "thread-2"
    assert data["lifecycle_state"] == "active"
    assert data["generation"] == 2
    assert data["history"] == [{
        "conversation_id": "thread-1",
        "lifecycle_state": "superseded",
        "superseded_by": "thread-2",
        "at": data["history"][0]["at"],
    }]


def test_thread_state_fails_closed_on_principal_or_division_mismatch(
    tmp_path,
    monkeypatch,
) -> None:
    state = tmp_path / "wake.json"
    state.write_text(json.dumps({
        "principal_id": "other-principal",
        "division_id": "DIVISION-02",
        "conversation_id": "thread-x",
    }), encoding="utf-8")
    monkeypatch.setattr(wake, "WAKE_JSON", state)
    monkeypatch.setattr(wake, "PRINCIPAL_ID", "division-head-division01")
    monkeypatch.setattr(wake, "DIVISION_ID", "DIVISION-01")

    with pytest.raises(RuntimeError, match="PRINCIPAL_MISMATCH"):
        wake.load_wake_state()


def test_cdp_and_operator_contracts_are_fail_closed() -> None:
    health = _source("bin/wake_brave_health.ps1")
    division_skill = _source("skills/wake-chatgpt/SKILL.md")
    executive_skill = _source("skills/wake-executive/SKILL.md")
    oauth = _source("bin/div01_oauth_login.mjs")

    assert '"--remote-debugging-address=127.0.0.1"' in health
    assert "NOT part of Runtime MCP" in division_skill
    assert "NOT part of Runtime MCP" in executive_skill
    assert "jangan blind retry" in division_skill
    assert "jangan blind retry" in executive_skill
    assert "runtime wake does NOT use this" in oauth
    assert "refresh_token" in oauth
    assert "console.log(tok" not in oauth


def test_canon_documents_required_auth_and_scaling_boundaries() -> None:
    architecture = _source("docs/architecture/WAKE_AUTH_SESSION_SECURITY_V1.md")
    runbook = _source("docs/operations/WAKE_AUTH_SESSION_ROTATION_V1.md")

    for required in (
        "APPROVE WITH MANDATORY CONTROLS",
        "Web JWT",
        "credential-equivalent",
        "continuity memory container",
        "not Company Truth",
        "one browser process with many profiles",
        "on-demand browser slots",
        "current single-principal pilot",
        "division_id -> exactly_one_active_thread",
    ):
        assert required in architecture
    for required in (
        "Normal expiry",
        "Suspected compromise",
        "Rotation",
        "Revocation",
        "Never record",
    ):
        assert required in runbook
