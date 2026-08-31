from __future__ import annotations

from pathlib import Path

import pytest

from income_os_bridge import runtime_mcp_server

ROOT = Path(__file__).resolve().parents[2]
EXEC_UNIT = ROOT / "company" / "executive" / "linux" / "die-executive-runtime-mcp-staging.service"
DIV_UNIT = ROOT / "company" / "division" / "division001" / "linux" / "die-division01-runtime-mcp-staging.service"
EXEC_INSTALL = ROOT / "company" / "executive" / "linux" / "install-staging.sh"
DIV_INSTALL = ROOT / "company" / "division" / "division001" / "linux" / "install-staging.sh"
RUNBOOK = ROOT / "docs" / "operations" / "RUNTIME_MCP_LINUX_STAGING_V1.md"


def test_staging_control_policy_defaults_enabled_and_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DIE_MCP_CONTROL_POLICY", raising=False)
    assert runtime_mcp_server._runtime_control_policy() == "enabled"
    monkeypatch.setenv("DIE_MCP_CONTROL_POLICY", "staging-read-only")
    assert runtime_mcp_server._runtime_control_policy() == "staging-read-only"
    monkeypatch.setenv("DIE_MCP_CONTROL_POLICY", "maybe")
    with pytest.raises(runtime_mcp_server.RuntimeMcpError) as raised:
        runtime_mcp_server._runtime_control_policy()
    assert raised.value.code == "E_RUNTIME_CONTROL_POLICY"
    with pytest.raises(runtime_mcp_server.RuntimeMcpError):
        runtime_mcp_server._runtime_control_policy("unexpected")


def test_staging_read_only_preserves_tool_parity_but_blocks_control_writer() -> None:
    assert len(runtime_mcp_server.tool_definitions("chatgpt-plus-executive")) == 18
    assert len(runtime_mcp_server.tool_definitions("division-head-division01")) == 6
    assert len(runtime_mcp_server.tool_definitions("die-lnx-executive-001")) == 18
    assert len(runtime_mcp_server.tool_definitions("die-lnx-division-001")) == 6
    writer_calls: list[dict] = []

    result = runtime_mcp_server.call_tool(
        "challenge",
        {},
        principal_id="die-lnx-executive-001",
        writer=lambda row: writer_calls.append(row) or {},
        control_policy="staging-read-only",
    )
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("E_STAGING_READ_ONLY:")
    assert writer_calls == []

    division = runtime_mcp_server.call_tool(
        "propose_mission",
        {},
        principal_id="die-lnx-division-001",
        writer=lambda row: writer_calls.append(row) or {},
        control_policy="staging-read-only",
    )
    assert division["content"][0]["text"].startswith("E_STAGING_READ_ONLY:")
    assert writer_calls == []


def test_modern_protocol_discovery_and_tool_catalog_are_dual_era_compatible() -> None:
    discover = runtime_mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": "discover-1",
            "method": "server/discover",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientInfo": {"name": "chatgpt", "version": "test"},
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
            },
        },
        principal_id="die-lnx-division-001",
        writer=None,
        control_policy="staging-read-only",
        protocol_version="2026-07-28",
    )
    assert discover is not None
    result = discover["result"]
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28"]
    assert result["capabilities"] == {"tools": {}}
    assert result["ttlMs"] == 0 and result["cacheScope"] == "private"
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["version"] == "1.3.0"

    modern_tools = runtime_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        principal_id="die-lnx-division-001",
        writer=None,
        control_policy="staging-read-only",
        protocol_version="2026-07-28",
    )
    assert modern_tools is not None
    assert modern_tools["result"]["resultType"] == "complete"
    assert modern_tools["result"]["ttlMs"] == 0
    assert modern_tools["result"]["cacheScope"] == "private"
    assert len(modern_tools["result"]["tools"]) == 6

    legacy_tools = runtime_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
        principal_id="division-head-division01",
        writer=None,
    )
    assert legacy_tools is not None
    assert "resultType" not in legacy_tools["result"]
    assert len(legacy_tools["result"]["tools"]) == 6


def test_initialize_negotiates_current_legacy_protocol_when_requested() -> None:
    response = runtime_mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "legacy-client", "version": "1.0"},
            },
        },
        principal_id="die-lnx-executive-001",
        writer=None,
        control_policy="staging-read-only",
    )
    assert response is not None
    assert response["result"]["protocolVersion"] == "2025-11-25"


def test_initialize_discloses_server_pinned_staging_control_policy() -> None:
    response = runtime_mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        principal_id="die-lnx-executive-001",
        writer=None,
        control_policy="staging-read-only",
    )
    assert response is not None
    instructions = response["result"]["instructions"]
    assert "die-lnx-executive-001" in instructions
    assert "Control policy: staging-read-only" in instructions
    assert "No raw or DEV access" in instructions


def test_staging_units_are_isolated_read_only_and_do_not_replace_existing_ports() -> None:
    expected = [
        (EXEC_UNIT, "die-lnx-executive-001", "8891", "/etc/die/staging/executive/runtime-mcp.env"),
        (DIV_UNIT, "die-lnx-division-001", "8892", "/etc/die/staging/division01/runtime-mcp.env"),
    ]
    for path, principal, port, env_file in expected:
        text = path.read_text(encoding="utf-8")
        assert "WorkingDirectory=/opt/die/staging/income-os" in text
        assert f"EnvironmentFile={env_file}" in text
        assert f"--principal-id {principal} --port {port}" in text
        assert "Environment=PYTHONDONTWRITEBYTECODE=1" in text
        assert "IPAddressDeny=any" in text and "IPAddressAllow=localhost" in text
        assert "ReadOnlyPaths=/opt/die/staging/income-os /var/lib/die/state" in text
        assert "ReadWritePaths=" not in text
        assert "cloudflared" not in text.lower()
        assert "wake" not in text.lower()
    assert "--port 8791" not in EXEC_UNIT.read_text(encoding="utf-8")
    assert "--port 8792" not in DIV_UNIT.read_text(encoding="utf-8")


def test_staging_installers_pin_domains_generate_private_secrets_and_never_start() -> None:
    expected = [
        (EXEC_INSTALL, "https://executive-mcp.aethers.biz.id", "die-executive-runtime-mcp-staging.service"),
        (DIV_INSTALL, "https://division01-mcp.aethers.biz.id", "die-division01-runtime-mcp-staging.service"),
    ]
    for path, base_url, service in expected:
        text = path.read_text(encoding="utf-8")
        assert 'STAGING_DIE_HOME="${STAGING_DIE_HOME:-/opt/die/staging/income-os}"' in text
        assert "git -C \"$STAGING_DIE_HOME\" status --porcelain" in text
        assert "secrets.token_urlsafe(48)" in text
        assert "secrets.token_urlsafe(32)" in text
        assert "chmod 0600 \"$ENV_FILE\"" in text
        assert f"DIE_MCP_BASE_URL={base_url}" in text
        assert "DIE_MCP_CONTROL_POLICY=staging-read-only" in text
        assert ("chatgpt-die-lnx-executive-001" in text) or ("chatgpt-die-lnx-division-001" in text)
        assert f'systemctl disable "{service}"' in text
        assert f'systemctl stop "{service}"' in text
        assert "systemctl start" not in text
        assert "systemctl enable" not in text
        assert "SECRET_VALUES_RETURNED=NO" in text
        assert "echo \"$token\"" not in text and "echo \"$login\"" not in text
        assert "cloudflared" not in text.lower()


def test_staging_runbook_keeps_mx062_windows_and_wake_outside_scope() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "`/srv/die` is not pulled, rebuilt, or restarted" in text
    assert "Executive 18, Division01 6" in text
    assert "E_STAGING_READ_ONLY" in text
    assert "MCP-LNX-002" in text
    assert "no Cloudflare activation" in text
    assert "no browser wake" in text
