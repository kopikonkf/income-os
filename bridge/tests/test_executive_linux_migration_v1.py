from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT / "company" / "executive" / "linux"
UNIT = EXEC / "die-executive-runtime-mcp.service"
INSTALL = EXEC / "install-linux.sh"
BROWSER = EXEC / "operator_browser.mjs"
REGISTRY = ROOT / "company" / "component-registry-v1.json"


def test_die200_systemd_unit_pins_principal_port_and_linux_roots() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert "User=die-executive" in text
    assert "Group=die-runtime" in text
    assert "DIE_HOME=/srv/die" in text
    assert "DIE_STATE_ROOT=/var/lib/die" in text
    assert "DIE_CONFIG_ROOT=/etc/die" in text
    assert "DIE_INSTALL_ROOT=/opt/die" in text
    assert "--principal-id chatgpt-plus-executive --port 8791" in text


def test_die200_systemd_unit_is_loopback_hardened_and_source_readonly() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=strict" in text
    assert "ProtectHome=true" in text
    assert "IPAddressDeny=any" in text
    assert "IPAddressAllow=localhost" in text
    assert "ReadOnlyPaths=/srv/die" in text
    assert "ReadWritePaths=/var/lib/die/state" in text
    assert "CapabilityBoundingSet=" in text


def test_die200_installer_generates_fresh_linux_secrets_and_never_copies_windows_profile() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in text
    assert "runtime-mcp.env" in text
    assert "chmod 0600" in text
    assert "DIE_MCP_BASE_URL=https://executive-linux-precutover.invalid" in text
    assert 'DIE_MCP_OAUTH_REDIRECT_HOSTS="chatgpt.com;openai.com"' in text
    assert "AppData" not in text
    assert "C:\\" not in text
    assert "cookie" not in text.lower()


def test_die200_operator_browser_is_consumer_policy_compliant() -> None:
    text = BROWSER.read_text(encoding="utf-8")
    core = (ROOT / "company" / "browser" / "linux" / "operator_browser_core.mjs").read_text(encoding="utf-8")
    assert "launchPersistentContext" not in text + core
    assert "/var/lib/die/executive/browser-profile" in text
    assert "/usr/bin/google-chrome-stable" in text
    assert "DIE_EXECUTIVE_BROWSER_EXECUTABLE" in text
    assert "DIRECT_SPAWN_LOOPBACK_CDP" in core
    assert "--remote-debugging-address=127.0.0.1" in core
    assert "--remote-debugging-port=0" in core
    assert "connectOverCDP" in core
    assert "--no-sandbox" not in core
    assert "--disable-blink-features=AutomationControlled" not in core
    assert "operator-controlled-acquisition-only" in core
    forbidden = [
        "/backend-api/",
        "/api/auth/session",
        "accessToken",
        "sentinel",
        "proof-token",
        "conversation request",
        "document.cookie",
        "localStorage",
    ]
    for token in forbidden:
        assert token not in text


def test_die200_operator_browser_never_submits_prompt_or_extracts_output() -> None:
    text = BROWSER.read_text(encoding="utf-8") + (ROOT / "company" / "browser" / "linux" / "operator_browser_core.mjs").read_text(encoding="utf-8")
    assert ".fill(" not in text
    assert ".press(" not in text
    assert ".click(" not in text
    assert "fetch(" not in text
    assert "innerText" not in text
    assert "textContent" not in text
    assert "evaluate(" not in text


def test_die200_registry_still_defers_architect_and_separates_executive() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    architect = payload["components"]["architect"]
    executive = payload["components"]["executive"]
    assert architect["status"] == "DEFERRED_SOURCE_IMPORT"
    assert architect["migration_task"] == "MX-053"
    assert executive["migration_task"] == "DIE-200"
    assert executive["logical_root"] == "company/executive"
