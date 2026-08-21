"""Safety contract for Executive MCP Activation Phase B2A secure runtime v1."""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "executive-mcp"
INITIALIZE = OPS / "Initialize-DIEExecutiveMcpSecureRuntime.ps1"
VERIFY = OPS / "Test-DIEExecutiveMcpSecureRuntime.ps1"
RUNBOOK = ROOT / "docs" / "operations" / "EXECUTIVE_MCP_SECURE_RUNTIME_V1.md"

FIXED_ROOT = r"C:\ProgramData\DIE\ExecutiveMCP"
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


def test_phase_b2a_manifest_exists() -> None:
    for path in (INITIALIZE, VERIFY, RUNBOOK):
        assert path.is_file(), path


def test_initializer_is_plan_first_and_fixed_path_only() -> None:
    source = INITIALIZE.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Apply")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    for child in ("config", "secrets", "logs", "runtime", "line1", "line2"):
        assert f'"{child}"' in source
    assert "writes_performed = $false" in source
    assert "secret_files_created = $false" in source
    assert "profile_files_created = $false" in source
    assert "external_mutation_performed = $false" in source
    assert "control-plane-api-key" not in source
    assert "snapshot-hmac-key" not in source
    assert "snapshot-hmac-key-id" not in source
    assert EMBEDDED_TUNNEL_ID.search(source) is None


def test_apply_mutation_is_limited_to_directories_and_acls() -> None:
    source = INITIALIZE.read_text(encoding="utf-8")
    assert "New-Item -ItemType Directory" in source
    assert "icacls.exe" in source
    for mutation in (
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
    assert FORBIDDEN_ORCHESTRATION.search(source) is None
    assert FORBIDDEN_TUNNEL_EXECUTION.search(source) is None


def test_initializer_fails_closed_on_topology_and_acl_contracts() -> None:
    source = INITIALIZE.read_text(encoding="utf-8")
    assert "Assert-RestrictedAcl" in source
    assert "Assert-LaneDirectoryEmpty" in source
    assert "Assert-RootSafe" in source
    assert "Get-ChildItem -LiteralPath $Path -Force" in source
    assert "B2A refuses to alter a non-empty lane directory" in source
    assert "unexpected entries" in source
    assert "AreAccessRulesProtected" in source
    assert "Inherited ACL rule is forbidden" in source
    assert "Only explicit Allow ACL rules are accepted" in source
    assert "Unexpected ACL principal is forbidden" in source
    assert '"S-1-5-18", "S-1-5-32-544", $CurrentSid' in source
    assert "/inheritance:r" in source
    assert "(OI)(CI)F" in source


def test_verifier_is_metadata_only_and_checks_empty_isolated_lanes() -> None:
    source = VERIFY.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Installed")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "Test-RootContainsOnlyLaneDirectories" in source
    assert "contains_no_entries" in source
    assert "tunnel_client_process_absent" in source
    assert "secret_values_read = $false" in source
    assert "profile_contents_read = $false" in source
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
    assert "Get-Content" not in source
    assert "ReadAllText" not in source
    assert FORBIDDEN_ORCHESTRATION.search(source) is None
    assert FORBIDDEN_TUNNEL_EXECUTION.search(source) is None
    assert EMBEDDED_TUNNEL_ID.search(source) is None


def test_no_script_can_initialize_or_execute_a_tunnel() -> None:
    for path in (INITIALIZE, VERIFY):
        source = path.read_text(encoding="utf-8")
        assert "profile init" not in source.lower()
        assert "tunnel-client doctor" not in source.lower()
        assert "tunnel-client run" not in source.lower()
        assert "CONTROL_PLANE_API_KEY" not in source
        assert "DIE_SNAPSHOT_HMAC_KEY" not in source
        assert "DIE_SNAPSHOT_HMAC_KEY_ID" not in source


def test_runbook_preserves_b2a_boundary() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert FIXED_ROOT in text
    assert "Every lane directory must remain empty" in text
    assert "B2B and later phases require separate Founder authorization" in text
    assert "does not create configuration files" in text
    assert "tunnel profiles" in text
    assert "No real key, HMAC material, or tunnel" in text
    assert "identity may be pasted into chat" in text
    assert "commit, push, or create a pull request without separate publication" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_b2a_plans_are_machine_readable_and_write_free() -> None:
    initialize = _run_plan(INITIALIZE)
    verify = _run_plan(VERIFY)

    assert initialize["schema_version"] == "die.executive.mcp.secure-runtime.v1"
    assert initialize["mode"] == "Plan"
    assert initialize["install_root"] == FIXED_ROOT
    assert initialize["writes_performed"] is False
    assert initialize["secret_files_created"] is False
    assert initialize["profile_files_created"] is False
    assert initialize["credentials_requested_or_read"] is False
    assert initialize["tunnel_identity_requested_or_read"] is False
    assert initialize["tunnel_profiles_initialized"] is False
    assert initialize["tunnel_client_doctor_invoked"] is False
    assert initialize["tunnel_client_run_invoked"] is False
    assert initialize["mcp_services_started"] is False
    assert initialize["windows_service_or_task_created"] is False
    assert initialize["external_mutation_performed"] is False
    assert len(initialize["created_or_hardened_directories"]) == 9

    assert verify["schema_version"] == (
        "die.executive.mcp.secure-runtime.preflight.v1"
    )
    assert verify["mode"] == "Plan"
    assert verify["programdata_accessed"] is False
    assert verify["secret_values_read"] is False
    assert verify["profile_contents_read"] is False
    assert verify["writes_performed"] is False
    assert verify["tunnel_profiles_initialized"] is False
    assert verify["tunnel_client_doctor_invoked"] is False
    assert verify["tunnel_client_run_invoked"] is False
    assert verify["mcp_services_started"] is False
    assert verify["windows_service_or_task_created"] is False
    assert verify["external_mutation_performed"] is False
