"""Safety contract for Executive MCP Activation Phase B1 secure-config v1."""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "executive-mcp"
PLAN = OPS / "New-DIEExecutiveMcpSecureConfigPlan.ps1"
LINE1 = OPS / "Invoke-DIEExecutiveLine1Tunnel.ps1"
LINE2 = OPS / "Invoke-DIEExecutiveLine2Tunnel.ps1"
PREFLIGHT = OPS / "Test-DIEExecutiveMcpSecureConfig.ps1"
RUNBOOK = ROOT / "docs" / "operations" / "EXECUTIVE_MCP_SECURE_CONFIG_V1.md"

FIXED_ROOT = r"C:\ProgramData\DIE\ExecutiveMCP"
LINE1_KEY_REF = (
    r"file:C:\ProgramData\DIE\ExecutiveMCP"
    r"\secrets\line1\control-plane-api-key"
)
LINE2_KEY_REF = (
    r"file:C:\ProgramData\DIE\ExecutiveMCP"
    r"\secrets\line2\control-plane-api-key"
)
FORBIDDEN_ORCHESTRATION = re.compile(
    r"(?im)\b("
    r"New-Service|Start-Service|Register-ScheduledTask|"
    r"New-ScheduledTask|schtasks(?:\.exe)?|Start-Process"
    r")\b"
)
ENVIRONMENT_ENUMERATION = re.compile(
    r"(?im)(Get-ChildItem\s+Env:|GetEnvironmentVariables|"
    r"GetEnvironmentVariable\s*\()"
)
EMBEDDED_TUNNEL_ID = re.compile(r"(?i)\\btunnel_[0-9a-f]{16,}\\b")


def _powershell() -> str | None:
    return shutil.which("powershell.exe") or shutil.which("powershell")


def _run_plan(script: pathlib.Path) -> dict[str, object]:
    executable = _powershell()
    assert executable is not None
    completed = subprocess.run(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Mode",
            "Plan",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_phase_b1_manifest_exists() -> None:
    for path in (PLAN, LINE1, LINE2, PREFLIGHT, RUNBOOK):
        assert path.is_file(), path


def test_secure_config_compiler_is_plan_only_and_write_free() -> None:
    source = PLAN.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "writes_performed = $false" in source
    assert "credentials_requested_or_read = $false" in source
    assert "tunnel_identity_requested_or_read = $false" in source
    assert "tunnel_profiles_initialized = $false" in source
    assert "tunnel_client_doctor_invoked = $false" in source
    assert "tunnel_client_run_invoked = $false" in source
    for mutation in (
        "New-Item",
        "Set-Content",
        "Out-File",
        "Add-Content",
        "Remove-Item",
        "Move-Item",
        "Copy-Item",
        "Invoke-WebRequest",
        "Invoke-RestMethod",
    ):
        assert mutation not in source
    assert "Get-Content" not in source
    assert "ReadAllText" not in source
    assert EMBEDDED_TUNNEL_ID.search(source) is None


def test_plan_defines_fixed_isolated_lanes_and_acl_contract() -> None:
    source = PLAN.read_text(encoding="utf-8")
    assert r'$ConfigPath = Join-Path $InstallRoot "config"' in source
    assert r'$SecretsPath = Join-Path $InstallRoot "secrets"' in source
    assert "127.0.0.1:18101" in source
    assert "127.0.0.1:18102" in source
    assert '"S-1-5-18"' in source
    assert '"S-1-5-32-544"' in source
    assert "inheritance_disabled = $true" in source
    assert "inherited_rules_allowed = $false" in source
    assert '"Everyone", "BUILTIN\\Users", "Authenticated Users"' in source
    assert '"file:$controlPlaneKeyFile"' in source
    assert '"snapshot-hmac-key"' in source
    assert '"snapshot-hmac-key-id"' in source


def test_wrappers_are_plan_first_and_lane_isolated() -> None:
    line1 = LINE1.read_text(encoding="utf-8")
    line2 = LINE2.read_text(encoding="utf-8")
    for source, lane in ((line1, "line1"), (line2, "line2")):
        assert '[ValidateSet("Plan", "Run")]' in source
        assert '[string]$Mode = "Plan"' in source
        assert f'$ConfigPath = Join-Path $InstallRoot "config\\{lane}"' in source
        assert f'$SecretsPath = Join-Path $InstallRoot "secrets\\{lane}"' in source
        assert '"--profile-file", $ProfileFile' in source
        assert '"--control-plane.api-key", $ControlPlaneKeyRef' in source
        assert "writes_performed = $false" in source
        assert "files_read = $false" in source
        assert "tunnel_client_run_invoked = $false" in source
        assert "--allow-remote-ui" not in source
        assert "--open-web-ui" not in source
        assert "--log.http-raw-unsafe" not in source
        assert FORBIDDEN_ORCHESTRATION.search(source) is None
        assert ENVIRONMENT_ENUMERATION.search(source) is None
        assert EMBEDDED_TUNNEL_ID.search(source) is None

    assert "ReadAllText" not in line1
    assert "snapshot-hmac-key" not in line1
    assert (
        'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $null, "Process")'
        in line1
    )
    assert (
        'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $null, "Process")'
        in line1
    )

    assert "[System.IO.File]::ReadAllText" in line2
    assert '"snapshot-hmac-key"' in line2
    assert '"snapshot-hmac-key-id"' in line2
    assert 'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $hmacKey, "Process")' in line2
    assert (
        'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $hmacKeyId, "Process")'
        in line2
    )
    assert "finally {" in line2
    assert (
        'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $null, "Process")'
        in line2
    )
    assert (
        'SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $null, "Process")'
        in line2
    )


def test_wrappers_fail_closed_on_acl_and_secret_contracts() -> None:
    line1 = LINE1.read_text(encoding="utf-8")
    line2 = LINE2.read_text(encoding="utf-8")
    for source in (line1, line2):
        assert "AreAccessRulesProtected" in source
        assert "Inherited ACL rule is forbidden" in source
        assert "Only explicit Allow ACL rules are accepted" in source
        assert "Unexpected ACL principal is forbidden" in source
        assert '@("S-1-5-18", "S-1-5-32-544", $currentSid)' in source
        assert (
            'SetEnvironmentVariable("CONTROL_PLANE_API_KEY", $null, "Process")'
            in source
        )
        assert (
            'SetEnvironmentVariable("OPENAI_API_KEY", $null, "Process")'
            in source
        )
    assert "GetByteCount($hmacKey) -lt 32" in line2
    assert "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$" in line2


def test_preflight_executes_plan_modes_only() -> None:
    source = PREFLIGHT.read_text(encoding="utf-8")
    assert "Invoke-PlanJson" in source
    assert "& $ScriptPath -Mode Plan" in source
    assert "-Mode Run" not in source
    assert "programdata_accessed = $false" in source
    assert "secret_values_returned = $false" in source
    assert "tunnel_client_doctor_invoked = $false" in source
    assert "tunnel_client_run_invoked = $false" in source
    assert "mcp_services_started = $false" in source
    assert "windows_service_or_task_created = $false" in source


def test_runbook_preserves_b1_boundary() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "https://developers.openai.com/api/docs/guides/secure-mcp-tunnels" in text
    assert FIXED_ROOT in text
    assert LINE1_KEY_REF in text
    assert LINE2_KEY_REF in text
    assert "B2 requires a separate Founder authorization" in text
    assert "No real key, HMAC material, or tunnel identity may be pasted into chat" in text
    assert "no ProgramData path is created, read, or modified" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_all_b1_plans_are_machine_readable_and_secret_free() -> None:
    plan = _run_plan(PLAN)
    line1 = _run_plan(LINE1)
    line2 = _run_plan(LINE2)

    assert plan["schema_version"] == "die.executive.mcp.secure-config.v1"
    assert plan["mode"] == "Plan"
    assert plan["install_root"] == FIXED_ROOT
    assert plan["safety"]["writes_performed"] is False
    assert plan["safety"]["credentials_requested_or_read"] is False
    assert plan["safety"]["tunnel_identity_requested_or_read"] is False
    assert plan["safety"]["tunnel_profiles_initialized"] is False
    assert plan["safety"]["tunnel_client_doctor_invoked"] is False
    assert plan["safety"]["tunnel_client_run_invoked"] is False

    lanes = {lane["lane"]: lane for lane in plan["lanes"]}
    assert set(lanes) == {"line1", "line2"}
    assert lanes["line1"]["control_plane_api_key_ref"] == LINE1_KEY_REF
    assert lanes["line2"]["control_plane_api_key_ref"] == LINE2_KEY_REF
    assert lanes["line1"]["hmac"]["required"] is False
    assert lanes["line1"]["hmac"]["injection"] == "prohibited"
    assert lanes["line2"]["hmac"]["required"] is True
    assert lanes["line2"]["hmac"]["injection"] == "process-scoped"
    assert lanes["line2"]["hmac"]["cleared_on_exit"] is True

    assert line1["schema_version"] == "die.executive.mcp.lane-wrapper.line1.v1"
    assert line1["mode"] == "Plan"
    assert line1["files_read"] is False
    assert line1["tunnel_client_run_invoked"] is False
    assert line1["hmac_access"] == "prohibited"

    assert line2["schema_version"] == "die.executive.mcp.lane-wrapper.line2.v1"
    assert line2["mode"] == "Plan"
    assert line2["files_read"] is False
    assert line2["tunnel_client_run_invoked"] is False
    assert line2["hmac_injection"] == "process-scoped"


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_b1_preflight_passes_without_runtime_access() -> None:
    completed = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PREFLIGHT),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["schema_version"] == (
        "die.executive.mcp.secure-config.preflight.v1"
    )
    assert result["mode"] == "DryRun"
    assert result["ready"] is True
    assert result["failed_checks"] == []
    assert result["evidence"]["programdata_accessed"] is False
    assert result["evidence"]["secret_values_returned"] is False
    assert result["safety"]["writes_performed"] is False
    assert result["safety"]["tunnel_client_doctor_invoked"] is False
    assert result["safety"]["tunnel_client_run_invoked"] is False
