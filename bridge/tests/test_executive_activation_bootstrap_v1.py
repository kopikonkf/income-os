"""Safety contract for Executive MCP Activation Phase A bootstrap v1."""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "executive-mcp"
INSTALLER = OPS / "Install-DIEExecutiveMcpPhaseA.ps1"
PREFLIGHT = OPS / "Test-DIEExecutiveMcpPhaseA.ps1"
RUNBOOK = (
    ROOT
    / "docs"
    / "operations"
    / "EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md"
)

FIXED_ROOT = r"C:\ProgramData\DIE\ExecutiveMCP"
SECRET_NAMES = (
    "CONTROL_PLANE_API_KEY",
    "DIE_SNAPSHOT_HMAC_KEY",
    "DIE_SNAPSHOT_HMAC_KEY_ID",
)
FORBIDDEN_COMMANDS = re.compile(
    r"(?im)\b("
    r"New-Service|Start-Service|Stop-Service|"
    r"Start-Process|Register-ScheduledTask|"
    r"New-ScheduledTask|schtasks(?:\.exe)?|"
    r"SetEnvironmentVariable"
    r")\b"
)


def _powershell() -> str | None:
    return shutil.which("powershell.exe") or shutil.which("powershell")


def test_phase_a_manifest_exists() -> None:
    assert INSTALLER.is_file()
    assert PREFLIGHT.is_file()
    assert RUNBOOK.is_file()


def test_installer_is_plan_first_and_fixed_to_programdata() -> None:
    source = INSTALLER.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Apply")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "InstallRoot" not in source.partition("param(")[2].partition(")")[0]
    assert "writes_performed = $false" in source
    assert "tunnel_profiles_initialized = $false" in source
    assert "tunnel_created_or_modified = $false" in source
    assert "mcp_services_started = $false" in source
    assert "windows_service_or_task_created = $false" in source


def test_installer_uses_only_official_release_and_verifies_artifacts() -> None:
    source = INSTALLER.read_text(encoding="utf-8")
    assert "https://api.github.com/repos/openai/tunnel-client/releases/latest" in source
    assert "https://github.com/openai/tunnel-client" in source
    assert "SHA256SUMS.txt" in source
    assert "Get-FileHash" in source
    assert "Official archive SHA-256 mismatch" in source
    assert '@("help", "quickstart")' in source
    assert "version does not match the official release tag" in source
    assert "tunnel-client.install.json" in source
    assert "official_archive_sha256" in source
    assert "installed_binary_sha256" in source
    assert "help_output_sha256" in source


def test_scripts_do_not_reference_runtime_secrets_or_activation_commands() -> None:
    source = INSTALLER.read_text(encoding="utf-8") + PREFLIGHT.read_text(
        encoding="utf-8"
    )
    for name in SECRET_NAMES:
        assert name not in source
    assert FORBIDDEN_COMMANDS.search(source) is None
    assert re.search(r"(?im)tunnel-client(?:\.exe)?\s+init\b", source) is None
    assert re.search(r"(?im)tunnel-client(?:\.exe)?\s+doctor\b", source) is None
    assert re.search(r"(?im)tunnel-client(?:\.exe)?\s+run\b", source) is None
    assert "DIE_LINE1_TUNNEL_ID" not in source
    assert "DIE_LINE2_TUNNEL_ID" not in source


def test_preflight_is_unauthenticated_and_reports_safety_flags() -> None:
    source = PREFLIGHT.read_text(encoding="utf-8")
    assert 'Test-TcpEndpoint -HostName "api.openai.com" -Port 443' in source
    assert "Invoke-WebRequest" not in source
    assert "Invoke-RestMethod" not in source
    assert "secret_values_returned = $false" in source
    assert "tunnel_profiles_initialized = $false" in source
    assert "tunnel_created_or_modified = $false" in source
    assert "mcp_services_started = $false" in source
    assert "windows_service_or_task_created = $false" in source


def test_runbook_preserves_phase_a_boundary() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "https://developers.openai.com/api/docs/guides/secure-mcp-tunnels" in text
    assert "https://github.com/openai/tunnel-client" in text
    assert FIXED_ROOT in text
    assert "Phase B requires separate Founder authorization" in text
    assert "No Phase B action is implied" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_installer_dry_run_is_machine_readable_and_write_free() -> None:
    completed = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALLER),
            "-Mode",
            "Plan",
            "-SkipReleaseDiscovery",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["schema_version"] == "die.executive.mcp.activation.phase-a.v1"
    assert result["mode"] == "Plan"
    assert result["install_root"] == FIXED_ROOT
    assert result["writes_performed"] is False
    assert result["tunnel_profiles_initialized"] is False
    assert result["tunnel_created_or_modified"] is False
    assert result["credentials_requested_or_read"] is False
    assert result["mcp_services_started"] is False
    assert result["windows_service_or_task_created"] is False
