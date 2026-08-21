"""Safety contract for Executive MCP Phase B2B1 secret provisioning tooling."""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "executive-mcp"
PROVISION = OPS / "Set-DIEExecutiveMcpSecrets.ps1"
VERIFY = OPS / "Test-DIEExecutiveMcpSecrets.ps1"
RUNBOOK = ROOT / "docs" / "operations" / "EXECUTIVE_MCP_SECRET_PROVISIONING_V1.md"

FIXED_ROOT = r"C:\ProgramData\DIE\ExecutiveMCP"
EXPECTED_FILES = {
    r"C:\ProgramData\DIE\ExecutiveMCP\secrets\line1\control-plane-api-key",
    r"C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\control-plane-api-key",
    r"C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\snapshot-hmac-key",
    r"C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\snapshot-hmac-key-id",
}
FORBIDDEN_ORCHESTRATION = re.compile(
    r"(?im)\b("
    r"New-Service|Start-Service|Register-ScheduledTask|"
    r"New-ScheduledTask|schtasks(?:\.exe)?|Start-Process"
    r")\b"
)
FORBIDDEN_TUNNEL_EXECUTION = re.compile(
    r"(?im)(tunnel-client(?:\.exe)?\s+(?:doctor|run|init)|"
    r"\&\s*\$TunnelClientPath)"
)
ENVIRONMENT_ENUMERATION = re.compile(
    r"(?im)(Get-ChildItem\s+Env:|GetEnvironmentVariables|"
    r"GetEnvironmentVariable\s*\()"
)
EMBEDDED_TUNNEL_ID = re.compile(r"(?i)\btunnel_[0-9a-f]{16,}\b")


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


def test_phase_b2b1_manifest_exists() -> None:
    for path in (PROVISION, VERIFY, RUNBOOK):
        assert path.is_file(), path


def test_provisioner_is_plan_first_fixed_path_and_explicitly_gated() -> None:
    source = PROVISION.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Provision")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert "[switch]$ConfirmInteractiveProvisioning" in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "Provision mode requires -ConfirmInteractiveProvisioning" in source
    assert "[Console]::IsInputRedirected" in source
    for name in (
        "control-plane-api-key",
        "snapshot-hmac-key",
        "snapshot-hmac-key-id",
    ):
        assert f'"{name}"' in source
    assert EMBEDDED_TUNNEL_ID.search(source) is None


def test_secret_input_is_no_echo_confirmed_and_not_plaintext_stringified() -> None:
    source = PROVISION.read_text(encoding="utf-8")
    assert "Read-Host -Prompt $Prompt -AsSecureString" in source
    assert "SecureStringToBSTR" in source
    assert "Marshal]::ReadInt16" in source
    assert "ZeroFreeBSTR" in source
    assert "[Array]::Clear" in source
    assert "Read-ConfirmedSecretBytes" in source
    assert "Test-ByteArraysEqual" in source
    assert "PtrToString" not in source
    assert "NetworkCredential" not in source
    assert "Get-Content" not in source
    assert "ReadAllText" not in source
    assert ENVIRONMENT_ENUMERATION.search(source) is None


def test_secret_contract_and_lane_isolation_are_fail_closed() -> None:
    source = PROVISION.read_text(encoding="utf-8")
    assert 'id = "line1-control-plane-api-key"' in source
    assert 'id = "line2-control-plane-api-key"' in source
    assert 'id = "line2-snapshot-hmac-key"' in source
    assert 'minimum_bytes = 32' in source
    assert 'id = "line2-snapshot-hmac-key-id"' in source
    assert "Test-AsciiKeyId" in source
    assert "Assert-DirectoryEmpty" in source
    assert "FileMode]::CreateNew" in source
    assert "FileShare]::None" in source
    assert "refuses to overwrite an existing protected file" in source
    assert "Provisioning is forbidden while tunnel-client is running" in source
    assert "rotation_supported = $false" in source


def test_mutation_is_limited_to_fixed_secret_files_and_acl_rollback() -> None:
    source = PROVISION.read_text(encoding="utf-8")
    assert "Write-ProtectedBytes" in source
    assert "icacls.exe" in source
    assert "/inheritance:r" in source
    assert '"*S-1-5-18:F"' in source
    assert '"*S-1-5-32-544:F"' in source
    assert "Remove-Item -LiteralPath $createdPath -Force" in source
    assert "Set-Content" not in source
    assert "Out-File" not in source
    assert "Add-Content" not in source
    assert "Invoke-WebRequest" not in source
    assert "Invoke-RestMethod" not in source
    assert FORBIDDEN_ORCHESTRATION.search(source) is None
    assert FORBIDDEN_TUNNEL_EXECUTION.search(source) is None


def test_metadata_validator_never_reads_or_mutates_secret_values() -> None:
    source = VERIFY.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Installed")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "Test-DirectoryHasExactFiles" in source
    assert "Get-Item -LiteralPath $path).Length" in source
    assert "secret_values_read = $false" in source
    assert "profile_contents_read = $false" in source
    assert "tunnel_client_process_absent" in source
    assert "Get-Content" not in source
    assert "ReadAllText" not in source
    for mutation in (
        "New-Item",
        "Set-Content",
        "Out-File",
        "Add-Content",
        "Remove-Item",
        "Move-Item",
        "Copy-Item",
        "icacls.exe",
    ):
        assert mutation not in source
    assert FORBIDDEN_ORCHESTRATION.search(source) is None
    assert FORBIDDEN_TUNNEL_EXECUTION.search(source) is None
    assert ENVIRONMENT_ENUMERATION.search(source) is None
    assert EMBEDDED_TUNNEL_ID.search(source) is None


def test_scripts_cannot_initialize_or_execute_tunnels() -> None:
    for path in (PROVISION, VERIFY):
        source = path.read_text(encoding="utf-8")
        assert "tunnel identity" not in source.lower() or (
            "tunnel_identity_requested_or_read = $false" in source
        )
        assert "profile init" not in source.lower()
        assert "tunnel-client doctor" not in source.lower()
        assert "tunnel-client run" not in source.lower()
        assert "CONTROL_PLANE_API_KEY" not in source
        assert "DIE_SNAPSHOT_HMAC_KEY" not in source
        assert "DIE_SNAPSHOT_HMAC_KEY_ID" not in source


def test_runbook_reserves_real_provisioning_for_founder() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert FIXED_ROOT in text
    assert "Phase B2B1 repository tooling only; no provisioning executed" in text
    assert "Real values must never pass through ChatGPT" in text
    assert "Tunnel identities and profile initialization are deliberately deferred to B2C" in text
    assert "Do not run Provision or Installed during B2B1 tooling validation" in text
    assert "Neither command may be run through chat or Architect MCP" in text
    assert "commit, push, or create a pull request without separate publication" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_b2b1_plans_are_machine_readable_and_side_effect_free() -> None:
    provision = _run_plan(PROVISION)
    verify = _run_plan(VERIFY)

    assert provision["schema_version"] == "die.executive.mcp.secret-provisioning.v1"
    assert provision["mode"] == "Plan"
    assert provision["install_root"] == FIXED_ROOT
    assert {item["path"] for item in provision["secret_files"]} == EXPECTED_FILES
    assert provision["programdata_accessed"] is False
    assert provision["prompts_displayed"] is False
    assert provision["writes_performed"] is False
    assert provision["secret_files_created"] is False
    assert provision["secret_values_read"] is False
    assert provision["tunnel_identity_requested_or_read"] is False
    assert provision["tunnel_profiles_initialized"] is False
    assert provision["tunnel_client_doctor_invoked"] is False
    assert provision["tunnel_client_run_invoked"] is False
    assert provision["mcp_services_started"] is False
    assert provision["windows_service_or_task_created"] is False
    assert provision["external_mutation_performed"] is False

    assert verify["schema_version"] == (
        "die.executive.mcp.secret-provisioning.preflight.v1"
    )
    assert verify["mode"] == "Plan"
    assert set(verify["expected_secret_files"]) == EXPECTED_FILES
    assert verify["programdata_accessed"] is False
    assert verify["secret_values_read"] is False
    assert verify["profile_contents_read"] is False
    assert verify["writes_performed"] is False
    assert verify["tunnel_identity_requested_or_read"] is False
    assert verify["tunnel_profiles_initialized"] is False
    assert verify["tunnel_client_doctor_invoked"] is False
    assert verify["tunnel_client_run_invoked"] is False
    assert verify["mcp_services_started"] is False
    assert verify["windows_service_or_task_created"] is False
    assert verify["external_mutation_performed"] is False
