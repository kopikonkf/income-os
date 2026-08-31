from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OPS=ROOT/'ops'/'linux'/'runtime-mcp'
CONFIG=OPS/'cloudflared-linux-mcp.yml'
UNIT=OPS/'die-runtime-mcp-cloudflared.service'
INSTALL=OPS/'install-cloudflared-staging.sh'
RUNBOOK=ROOT/'docs'/'operations'/'RUNTIME_MCP_LINUX_CLOUDFLARE_STAGING_V1.md'

def test_ingress_is_exact_two_principal_allowlist_plus_terminal_404() -> None:
    text=CONFIG.read_text(encoding='utf-8')
    assert text.count('hostname:')==2
    assert 'executive-mcp.aethers.biz.id' in text and 'http://127.0.0.1:8891' in text
    assert 'division01-mcp.aethers.biz.id' in text and 'http://127.0.0.1:8892' in text
    assert text.rstrip().endswith('- service: http_status:404')
    for forbidden in ['9110','9333','8790','aethers.web.id','architect','DevTools','wake']:
        assert forbidden.lower() not in text.lower()

def test_unit_uses_systemd_credentials_and_never_places_token_in_argv() -> None:
    text=UNIT.read_text(encoding='utf-8')
    assert 'User=die-cloudflared' in text
    assert 'LoadCredential=linux-mcp.token:/etc/die/staging/cloudflare/linux-mcp.token' in text
    assert '--token-file %d/linux-mcp.token' in text
    assert '--token ' not in text
    assert 'TUNNEL_TOKEN=' not in text
    assert '--config /etc/die/staging/cloudflare/linux-mcp.yml' in text
    assert '--metrics 127.0.0.1:20290' in text
    assert 'NoNewPrivileges=true' in text
    assert 'ProtectSystem=strict' in text

def test_installer_requires_existing_private_token_and_never_starts_service() -> None:
    text=INSTALL.read_text(encoding='utf-8')
    assert '[[ -s "$TOKEN_FILE" ]]' in text
    assert 'chmod 0600 "$TOKEN_FILE"' in text
    assert 'cloudflared tunnel ingress validate' in text
    assert 'TOKEN_VALUE_RETURNED=NO' in text
    assert 'systemctl disable die-runtime-mcp-cloudflared.service' in text
    assert 'systemctl stop die-runtime-mcp-cloudflared.service' in text
    assert 'systemctl start' not in text
    assert 'systemctl enable' not in text
    assert 'tunnel token' not in text.lower()

def test_runbook_preserves_windows_wake_architect_and_mcp003_boundary() -> None:
    text=RUNBOOK.read_text(encoding='utf-8')
    assert 'Windows tunnel `aethers`' in text
    assert 'No Architect MCP, CDP port, browser profile, wake endpoint' in text
    assert 'LoadCredential=' in text
    assert 'MCP-LNX-003' in text
