"""Non-secret readiness audit for Executive Line 1/2 MCP activation."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
from typing import Any, Mapping

from . import config, executive_mcp_server, mcp_server, snapshot

SCHEMA_VERSION = "die.executive.mcp.activation.readiness.v1"
ACTIVATION_MODE = "secure_mcp_tunnel"
ACTIVATION_MODE_ENV = "DIE_MCP_ACTIVATION_MODE"
TUNNEL_CLIENT_ENV = "DIE_MCP_TUNNEL_CLIENT"
LINE1_TUNNEL_ID_ENV = "DIE_LINE1_TUNNEL_ID"
LINE2_TUNNEL_ID_ENV = "DIE_LINE2_TUNNEL_ID"
TUNNEL_COMMANDS = ("tunnel-client", "mcp-tunnel")


def _tool_lists() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    line1 = mcp_server._handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    line2 = executive_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        writer=None,
    )
    return line1["result"]["tools"], line2["result"]["tools"]


def _initializations() -> tuple[dict[str, Any], dict[str, Any]]:
    line1 = mcp_server._handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    line2 = executive_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}},
        writer=None,
    )
    return line1["result"], line2["result"]


def _tunnel_client(
    env: Mapping[str, str],
) -> tuple[bool, str]:
    configured = env.get(TUNNEL_CLIENT_ENV, "").strip()
    if configured:
        path = pathlib.Path(configured)
        return path.is_file(), "configured_path"
    for command in TUNNEL_COMMANDS:
        if shutil.which(command):
            return True, "command_path"
    return False, "absent"


def evaluate(
    *,
    env: Mapping[str, str] | None = None,
    root: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return booleans and safe blockers; never return credential values."""

    active_env = os.environ if env is None else env
    die_root = pathlib.Path(root) if root is not None else config.DIE_HOME
    line1_tools, line2_tools = _tool_lists()
    line1_init, line2_init = _initializations()

    line1_names = [tool.get("name") for tool in line1_tools]
    line2_names = [tool.get("name") for tool in line2_tools]
    code_checks = {
        "line1_has_context_snapshot": "context_snapshot" in line1_names,
        "line1_all_tools_read_only": bool(line1_tools)
        and all(
            tool.get("annotations", {}).get("readOnlyHint") is True
            for tool in line1_tools
        ),
        "line2_exact_tool": line2_names == [executive_mcp_server.TOOL_NAME],
        "line2_tool_is_write": (
            line2_tools[0].get("annotations", {}).get("readOnlyHint") is False
            if len(line2_tools) == 1
            else False
        ),
        "line2_tool_is_idempotent": (
            line2_tools[0].get("annotations", {}).get("idempotentHint") is True
            if len(line2_tools) == 1
            else False
        ),
        "server_names_are_distinct": (
            line1_init.get("serverInfo", {}).get("name")
            != line2_init.get("serverInfo", {}).get("name")
        ),
        "line1_instructions_present": bool(line1_init.get("instructions")),
        "line2_instructions_present": bool(line2_init.get("instructions")),
        "line1_bootstrap_present": (
            die_root / "bin" / "die_executive_line1_mcp.py"
        ).is_file(),
        "line2_bootstrap_present": (
            die_root / "bin" / "die_executive_mcp.py"
        ).is_file(),
    }
    code_ready = all(code_checks.values())

    signing_key = active_env.get(snapshot.SIGNING_KEY_ENV, "")
    signing_key_id = active_env.get(snapshot.SIGNING_KEY_ID_ENV, "")
    mode = active_env.get(ACTIVATION_MODE_ENV, "").strip()
    line1_tunnel_id = active_env.get(LINE1_TUNNEL_ID_ENV, "").strip()
    line2_tunnel_id = active_env.get(LINE2_TUNNEL_ID_ENV, "").strip()
    tunnel_client_present, tunnel_client_source = _tunnel_client(active_env)

    prerequisites = {
        "activation_mode_is_secure_mcp_tunnel": mode == ACTIVATION_MODE,
        "snapshot_hmac_key_present_and_minimum_length": (
            len(signing_key.encode("utf-8")) >= 32
        ),
        "snapshot_hmac_key_id_present": bool(signing_key_id),
        "tunnel_client_present": tunnel_client_present,
        "line1_tunnel_id_present": bool(line1_tunnel_id),
        "line2_tunnel_id_present": bool(line2_tunnel_id),
        "tunnel_ids_are_distinct": bool(
            line1_tunnel_id
            and line2_tunnel_id
            and line1_tunnel_id != line2_tunnel_id
        ),
    }

    blockers = [
        name
        for name, passed in {**code_checks, **prerequisites}.items()
        if not passed
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "activation_mode": ACTIVATION_MODE,
        "code_ready": code_ready,
        "activation_ready": code_ready and all(prerequisites.values()),
        "code_checks": code_checks,
        "deployment_prerequisites": prerequisites,
        "tunnel_client_source": tunnel_client_source,
        "line1_tool_count": len(line1_tools),
        "line2_tools": line2_names,
        "blockers": blockers,
        "secret_values_returned": False,
        "deployment_performed": False,
        "registration_performed": False,
    }


def render(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
