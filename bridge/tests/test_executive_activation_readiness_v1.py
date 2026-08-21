"""Activation-readiness contract for separate Executive Line 1/2 MCP lanes."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

from income_os_bridge import (
    activation_readiness,
    executive_mcp_server,
    mcp_server,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIN = ROOT / "bin"


def _complete_env(client: pathlib.Path) -> dict[str, str]:
    return {
        "DIE_MCP_ACTIVATION_MODE": "secure_mcp_tunnel",
        "DIE_MCP_TUNNEL_CLIENT": str(client),
        "DIE_LINE1_TUNNEL_ID": "tunnel-line1-test",
        "DIE_LINE2_TUNNEL_ID": "tunnel-line2-test",
        "DIE_SNAPSHOT_HMAC_KEY": "readiness-test-only-" + ("x" * 48),
        "DIE_SNAPSHOT_HMAC_KEY_ID": "readiness-test-v1",
        "CONTROL_PLANE_API_KEY": "sk-test-only-" + ("y" * 48),
        "DIE_OPENAI_TUNNELS_READ_USE_GRANTED": "true",
        "DIE_OPENAI_TUNNEL_WORKSPACE_ASSOCIATED": "true",
        "DIE_CHATGPT_DEVELOPER_MODE_ENABLED": "true",
    }


def test_line1_metadata_is_read_only_and_line2_is_confirmed_write() -> None:
    line1_init = mcp_server._handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    line1_list = mcp_server._handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    line2_init = executive_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}},
        writer=None,
    )
    line2_list = executive_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
        writer=None,
    )

    assert "context_snapshot" in line1_init["result"]["instructions"]
    assert all(
        tool["annotations"]["readOnlyHint"] is True
        for tool in line1_list["result"]["tools"]
    )
    assert "explicit user confirmation" in line2_init["result"]["instructions"]
    assert [tool["name"] for tool in line2_list["result"]["tools"]] == [
        "decision_submit"
    ]
    assert line2_list["result"]["tools"][0]["annotations"]["readOnlyHint"] is False
    assert line2_list["result"]["tools"][0]["annotations"]["idempotentHint"] is True


def test_line1_rejects_non_object_jsonrpc_params() -> None:
    response = mcp_server._handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": ["not", "an", "object"],
        }
    )
    assert response["error"]["code"] == -32602


def test_live_shape_is_code_ready_but_activation_blocked_without_secrets() -> None:
    result = activation_readiness.evaluate(env={}, root=ROOT)
    assert result["schema_version"] == "die.executive.mcp.activation.readiness.v1.1"
    assert result["code_ready"] is True
    assert result["activation_ready"] is False
    assert result["secret_values_returned"] is False
    assert result["deployment_performed"] is False
    assert "snapshot_hmac_key_present_and_minimum_length" in result["blockers"]
    assert "control_plane_api_key_present_and_minimum_length" in result["blockers"]
    assert "tunnel_client_present" in result["blockers"]


def test_v1_prerequisites_cannot_bypass_official_control_plane_gate(tmp_path) -> None:
    client = tmp_path / "tunnel-client.exe"
    client.write_bytes(b"test placeholder")
    env = _complete_env(client)
    control_plane_key = env.pop("CONTROL_PLANE_API_KEY")
    env.pop("DIE_OPENAI_TUNNELS_READ_USE_GRANTED")
    env.pop("DIE_OPENAI_TUNNEL_WORKSPACE_ASSOCIATED")
    env.pop("DIE_CHATGPT_DEVELOPER_MODE_ENABLED")

    result = activation_readiness.evaluate(env=env, root=ROOT)
    encoded = json.dumps(result)
    assert result["activation_ready"] is False
    assert {
        "control_plane_api_key_present_and_minimum_length",
        "tunnels_read_use_permissions_attested",
        "target_chatgpt_workspace_association_attested",
        "chatgpt_developer_mode_attested",
    }.issubset(result["blockers"])
    assert control_plane_key not in encoded


def test_readiness_succeeds_with_complete_injected_prerequisites(tmp_path) -> None:
    client = tmp_path / "tunnel-client.exe"
    client.write_bytes(b"test placeholder")
    env = _complete_env(client)
    signing_secret = env["DIE_SNAPSHOT_HMAC_KEY"]
    control_plane_secret = env["CONTROL_PLANE_API_KEY"]

    result = activation_readiness.evaluate(env=env, root=ROOT)
    encoded = json.dumps(result)
    assert result["activation_ready"] is True
    assert result["blockers"] == []
    assert all(result["control_plane_prerequisites"].values())
    assert signing_secret not in encoded
    assert control_plane_secret not in encoded
    assert "tunnel-line1-test" not in encoded
    assert "tunnel-line2-test" not in encoded


def test_duplicate_tunnel_ids_fail_closed(tmp_path) -> None:
    client = tmp_path / "tunnel-client.exe"
    client.write_bytes(b"test placeholder")
    env = _complete_env(client)
    env["DIE_LINE2_TUNNEL_ID"] = env["DIE_LINE1_TUNNEL_ID"]

    result = activation_readiness.evaluate(env=env, root=ROOT)
    assert result["activation_ready"] is False
    assert "tunnel_ids_are_distinct" in result["blockers"]


def test_line1_stdio_bootstrap_initializes_and_lists_read_only_tools() -> None:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    completed = subprocess.run(
        [sys.executable, str(BIN / "die_executive_line1_mcp.py")],
        input="\n".join(json.dumps(row) for row in messages) + "\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=os.environ.copy(),
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert responses[0]["result"]["serverInfo"]["name"] == "income-os-bridge"
    assert responses[0]["result"]["serverInfo"]["version"] == "0.5.0"
    assert all(
        tool["annotations"]["readOnlyHint"] is True
        for tool in responses[1]["result"]["tools"]
    )
