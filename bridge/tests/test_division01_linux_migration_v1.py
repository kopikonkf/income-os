from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIV = ROOT / "company" / "division" / "division001" / "linux"
UNIT = DIV / "die-division01-runtime-mcp.service"
INSTALL = DIV / "install-linux.sh"
BROWSER = DIV / "operator_browser.mjs"
REGISTRY = ROOT / "company" / "component-registry-v1.json"
IDENTITY = ROOT / "company" / "division" / "division001" / "IDENTITY.md"


def test_die201_systemd_unit_pins_principal_port_and_linux_roots() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert "User=die-division01" in text
    assert "Group=die-runtime" in text
    assert "DIE_HOME=/srv/die" in text
    assert "DIE_STATE_ROOT=/var/lib/die" in text
    assert "DIE_CONFIG_ROOT=/etc/die" in text
    assert "DIE_INSTALL_ROOT=/opt/die" in text
    assert "--principal-id division-head-division01 --port 8792" in text


def test_die201_systemd_unit_is_loopback_hardened_and_source_readonly() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=strict" in text
    assert "ProtectHome=true" in text
    assert "IPAddressDeny=any" in text
    assert "IPAddressAllow=localhost" in text
    assert "ReadOnlyPaths=/srv/die" in text
    assert "ReadWritePaths=/var/lib/die/state" in text
    assert "CapabilityBoundingSet=" in text


def test_die201_installer_uses_fresh_linux_secrets_and_excludes_oauth_estate() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in text
    assert "runtime-mcp.env" in text
    assert "chmod 0600" in text
    assert "DIE_MCP_BASE_URL=https://division01-linux-precutover.invalid" in text
    assert 'DIE_MCP_OAUTH_REDIRECT_HOSTS="chatgpt.com;openai.com"' in text
    assert "D:\\\\OAUTH is not Division01" in text
    assert 'if [[ ! -d "$STATE_DIR" ]]' in text
    assert 'install -d -o root -g "$SERVICE_GROUP" -m 2770 "$STATE_DIR"' in text
    assert 'chown -R root:"$SERVICE_GROUP" "$STATE_DIR"' in text
    assert 'install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 2770 "$STATE_DIR"' not in text
    assert "AppData" not in text
    assert "cookie" not in text.lower()


def test_die201_operator_browser_is_consumer_policy_compliant() -> None:
    text = BROWSER.read_text(encoding="utf-8")
    core = (ROOT / "company" / "browser" / "linux" / "operator_browser_core.mjs").read_text(encoding="utf-8")
    assert "launchPersistentContext" not in text + core
    assert "/var/lib/die/division01/browser-profile" in text
    assert "/usr/bin/google-chrome-stable" in text
    assert "DIE_DIVISION01_BROWSER_EXECUTABLE" in text
    assert "DIRECT_SPAWN_LOOPBACK_CDP" in core
    assert "--remote-debugging-address=127.0.0.1" in core
    assert "--remote-debugging-port=0" in core
    assert "connectOverCDP" in core
    assert "--no-sandbox" not in core
    assert "--disable-blink-features=AutomationControlled" not in core
    assert "operator-controlled-acquisition-only" in core
    assert "division-head-division01" in text
    forbidden = [
        "/backend-api/",
        "/api/auth/session",
        "accessToken",
        "sentinel",
        "proof-token",
        "document.cookie",
        "localStorage",
    ]
    for token in forbidden:
        assert token not in text


def test_die201_operator_browser_never_submits_prompt_or_extracts_output() -> None:
    text = BROWSER.read_text(encoding="utf-8") + (ROOT / "company" / "browser" / "linux" / "operator_browser_core.mjs").read_text(encoding="utf-8")
    assert ".fill(" not in text
    assert ".press(" not in text
    assert ".click(" not in text
    assert "fetch(" not in text
    assert "innerText" not in text
    assert "textContent" not in text
    assert "evaluate(" not in text


def test_die201_identity_and_registry_keep_oauth_separate_and_principal_stable() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    division = payload["components"]["division01"]
    assert division["principal_id"] == "division-head-division01"
    assert division["migration_task"] == "DIE-201"
    assert division["logical_root"] == "company/division/division001"
    identity = IDENTITY.read_text(encoding="utf-8")
    assert "`D:\\OAUTH` is not Division01" in identity
    assert "127.0.0.1:8792" in identity
    assert "private backend" in identity
    assert "automated prompt submission" in identity
