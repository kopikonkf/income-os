"""Two-principal Runtime MCP Windows activation contract v1."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import shutil
import subprocess

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "runtime-mcp"
INITIALIZE = OPS / "Initialize-DIERuntimeMcpActivation.ps1"
INSTALL = OPS / "Install-DIERuntimeMcpServices.ps1"
INVOKE = OPS / "Invoke-DIERuntimeMcp.ps1"
VERIFY = OPS / "Test-DIERuntimeMcpActivation.ps1"
SERVICE_HOST = OPS / "die-windows-service.py"
RUNBOOK = ROOT / "docs" / "operations" / "RUNTIME_MCP_ACTIVATION_V1.md"

FIXED_ROOT = r"C:\ProgramData\DIE\RuntimeMCP"
EXPECTED_BINDINGS = {
    "chatgpt-plus-executive": 8791,
    "division-head-division01": 8792,
}
RESERVED_PORTS = {8787, 8789, 8790}
FORBIDDEN_DEV = re.compile(
    r"(?i)\b(repository_write|git_write|test_execution|service_control|credential_read|architect_dev)\b"
)
FORBIDDEN_WAKE_OR_TUNNEL = re.compile(
    r"(?i)(wake_chatgpt|agent-browser|BrowserOS|tunnel-client(?:\.exe)?\s+(?:init|doctor|run))"
)


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


def test_activation_manifest_exists() -> None:
    for path in (INITIALIZE, INSTALL, INVOKE, VERIFY, SERVICE_HOST, RUNBOOK):
        assert path.is_file(), path


def test_provisioning_is_plan_first_interactive_and_fail_closed() -> None:
    source = INITIALIZE.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Provision")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert "[switch]$ConfirmInteractiveProvisioning" in source
    assert f'$InstallRoot = "{FIXED_ROOT}"' in source
    assert "Read-Host -Prompt $Prompt -AsSecureString" in source
    assert "SecureStringToBSTR" in source
    assert "ZeroFreeBSTR" in source
    assert "Test-ByteArraysEqual" in source
    assert "[Array]::Clear" in source
    assert "FileMode]::CreateNew" in source
    assert "Initial provisioning refuses to alter an existing RuntimeMCP root" in source
    assert "secret_values_returned = $false" in source
    assert "Start-Service" not in source
    assert "New-Service" not in source
    assert "Register-ScheduledTask" not in source
    assert FORBIDDEN_WAKE_OR_TUNNEL.search(source) is None


def test_per_principal_secret_and_acl_contract() -> None:
    source = INITIALIZE.read_text(encoding="utf-8")
    for lane in ("executive", "division01"):
        assert f'id = "{lane}"' in source
    assert 'id = "$($lane.id)-mcp-token"' in source
    assert 'id = "$($lane.id)-mcp-login-password"' in source
    assert 'id = "$($lane.id)-snapshot-hmac-key"' in source
    assert 'id = "$($lane.id)-snapshot-hmac-key-id"' in source
    assert '"S-1-5-18", "S-1-5-32-544", $CurrentSid' in source
    assert "/inheritance:r" in source
    assert "(OI)(CI)F" in source
    assert "minimum_bytes = 32" in source
    assert "minimum_bytes = 16" in source
    assert "opaque-no-whitespace" in source
    assert "ascii-key-id" in source


def test_service_installer_uses_repo_native_scm_host_without_secrets() -> None:
    source = INSTALL.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Install")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert "[switch]$ConfirmServiceInstall" in source
    assert 'name = "DIERuntimeMCPExecutive"' in source
    assert 'name = "DIERuntimeMCPDivision01"' in source
    assert "die-windows-service.py" in source
    assert "Invoke-DIERuntimeMcp.ps1" in source
    assert "New-Service" in source
    assert "-BinaryPathName $binaryPath" in source
    assert "-StartupType Automatic" in source
    assert 'StartName -ne "LocalSystem"' in source
    assert "sc.exe create" not in source
    assert "sc.exe failure" in source
    assert "sc.exe delete" in source
    assert "Start-Service" not in source
    assert "Register-ScheduledTask" not in source
    assert "DIE_MCP_TOKEN" not in source
    assert "DIE_SNAPSHOT_HMAC_KEY" not in source
    assert "Get-Content" not in source
    assert "ReadAllText" not in source
    assert "secret_values_read = $false" in source
    assert "service_binary_contains_secret = $false" in source
    assert FORBIDDEN_WAKE_OR_TUNNEL.search(source) is None


def test_launcher_pins_identity_port_and_only_required_runtime_environment() -> None:
    source = INVOKE.read_text(encoding="utf-8")
    for principal, port in EXPECTED_BINDINGS.items():
        assert f'"{principal}"' in source
        assert f"port = {port}" in source
    assert not RESERVED_PORTS & {int(value) for value in re.findall(r"port = (\d+)", source)}
    assert "[ValidateSet(" in source
    assert "DIE_MCP_TOKEN" in source
    assert "DIE_MCP_LOGIN_PASSWORD" in source
    assert "DIE_MCP_BASE_URL" in source
    assert "DIE_MCP_OAUTH_CLIENT_ID" in source
    assert "DIE_SNAPSHOT_HMAC_KEY" in source
    assert "DIE_SNAPSHOT_HMAC_KEY_ID" in source
    assert "income_os_bridge.runtime_mcp_server" in source
    assert "https://executive-mcp.aethers.web.id" in source
    assert "https://division01-mcp.aethers.web.id" in source
    assert "--principal-id $PrincipalId" in source
    assert "--port ([int]$binding.port)" in source
    assert FORBIDDEN_DEV.search(source) is None
    assert FORBIDDEN_WAKE_OR_TUNNEL.search(source) is None


def test_service_host_is_scm_aware_and_owns_child_tree() -> None:
    source = SERVICE_HOST.read_text(encoding="utf-8")
    assert "StartServiceCtrlDispatcherW" in source
    assert "RegisterServiceCtrlHandlerExW" in source
    assert "SetServiceStatus" in source
    assert "CreateJobObjectW" in source
    assert "AssignProcessToJobObject" in source
    assert "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in source
    assert "TerminateJobObject" in source
    assert '"service.host.child_started"' in source
    assert '"command"' not in source.split("def _write_event", 1)[1].split("def _report_status", 1)[0]
    assert "token" not in source.lower()

    spec = importlib.util.spec_from_file_location("die_windows_service", SERVICE_HOST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module._parse_args(
        [
            "--service-name",
            "TestService",
            "--working-directory",
            r"C:\DIE",
            "--event-log-path",
            r"C:\ProgramData\DIE\RuntimeMCP\logs\test.jsonl",
            "--",
            "python.exe",
            "-V",
        ]
    )
    assert args.command == ["python.exe", "-V"]


def test_verifier_has_metadata_only_installed_gate_and_bounded_live_probe() -> None:
    source = VERIFY.read_text(encoding="utf-8")
    assert '[ValidateSet("Plan", "Installed", "Live")]' in source
    assert '[string]$Mode = "Plan"' in source
    assert "secret_values_read = $false" in source
    assert "secret_values_returned = $false" in source
    assert "Test-Unauthenticated401" in source
    assert 'method = "initialize"' in source
    assert 'method = "tools/list"' in source
    assert 'name = "context_snapshot"' in source
    assert "expected_tool_count" in source
    assert '"HMAC-SHA256"' in source
    assert "snapshot_id" in source
    assert "Start-Service" not in source
    assert "Stop-Service" not in source
    assert FORBIDDEN_WAKE_OR_TUNNEL.search(source) is None


def test_verifier_array_wraps_an_empty_strict_mode_pipeline() -> None:
    source = VERIFY.read_text(encoding="utf-8")
    pattern = re.compile(
        r"@\(\s*\$secretChecks\s*\|\s*Where-Object\s*\{.*?\}\s*\)\.Count\s*-eq\s*0",
        re.DOTALL,
    )
    assert pattern.search(source)
    assert re.search(
        r"(?<!@)\(\$secretChecks\s*\|\s*Where-Object.*?\)\.Count",
        source,
        re.DOTALL,
    ) is None


def test_runbook_preserves_activation_boundaries() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert FIXED_ROOT in text
    assert "127.0.0.1:8791" in text
    assert "127.0.0.1:8792" in text
    assert "Architect must never receive or display a real secret value" in text
    assert "BrowserOS wake" in text
    assert "P2 tunnel" in text
    assert "M-001 remains unselected" in text
    assert "Founder merge" in text
    assert "Aether Caddy is not" in text
    assert "four values per principal" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_plans_are_machine_readable_and_side_effect_free() -> None:
    provision = _run_plan(INITIALIZE)
    install = _run_plan(INSTALL)
    verify = _run_plan(VERIFY)

    assert provision["schema_version"] == "die.runtime-mcp.activation.v1"
    assert provision["mode"] == "Plan"
    assert provision["install_root"] == FIXED_ROOT
    assert {row["principal_id"]: row["port"] for row in provision["principals"]} == EXPECTED_BINDINGS
    assert len(provision["secret_files"]) == 8
    assert provision["writes_performed"] is False
    assert provision["secret_values_read"] is False
    assert provision["services_created"] is False
    assert provision["services_started"] is False

    assert install["schema_version"] == "die.runtime-mcp.services.v1"
    assert install["mode"] == "Plan"
    assert {row["principal_id"]: row["port"] for row in install["services"]} == EXPECTED_BINDINGS
    assert install["secret_values_read"] is False
    assert install["services_created"] is False
    assert install["services_started"] is False

    assert verify["schema_version"] == "die.runtime-mcp.activation.preflight.v1"
    assert verify["mode"] == "Plan"
    assert {row["principal_id"]: row["port"] for row in verify["expected_services"]} == EXPECTED_BINDINGS
    assert verify["programdata_accessed"] is False
    assert verify["secret_values_read"] is False
    assert verify["writes_performed"] is False
    assert verify["services_started_or_stopped"] is False
