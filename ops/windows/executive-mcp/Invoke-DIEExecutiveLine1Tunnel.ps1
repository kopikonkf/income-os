[CmdletBinding()]
param(
    [ValidateSet("Plan", "Run")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.lane-wrapper.line1.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$BinPath = Join-Path $InstallRoot "bin"
$ConfigPath = Join-Path $InstallRoot "config\line1"
$SecretsPath = Join-Path $InstallRoot "secrets\line1"
$LogsPath = Join-Path $InstallRoot "logs\line1"
$RuntimePath = Join-Path $InstallRoot "runtime\line1"
$TunnelClientPath = Join-Path $BinPath "tunnel-client.exe"
$ProfileFile = Join-Path $ConfigPath "executive-line1.yaml"
$ControlPlaneKeyFile = Join-Path $SecretsPath "control-plane-api-key"
$ControlPlaneKeyRef = "file:$ControlPlaneKeyFile"
$LogFile = Join-Path $LogsPath "tunnel-client.jsonl"
$PidFile = Join-Path $RuntimePath "tunnel-client.pid"
$HealthListenAddress = "127.0.0.1:18101"
$RepoRoot = "C:\DIE"
$BootstrapPath = Join-Path $RepoRoot "bin\die_executive_line1_mcp.py"

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        lane = "line1"
        install_root = $InstallRoot
        tunnel_client = $TunnelClientPath
        profile_file = $ProfileFile
        control_plane_api_key_ref = $ControlPlaneKeyRef
        bootstrap = $BootstrapPath
        health_listen_address = $HealthListenAddress
        log_file = $LogFile
        pid_file = $PidFile
        hmac_access = "prohibited"
        writes_performed = $false
        files_read = $false
        environment_values_read = $false
        tunnel_client_run_invoked = $false
        mcp_service_started = $false
    } | ConvertTo-Json -Depth 5
    exit 0
}

function Assert-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("Container", "Leaf")][string]$PathType
    )

    if (-not (Test-Path -LiteralPath $Path -PathType $PathType)) {
        throw "Required protected path is missing: $Path"
    }

    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        throw "ACL inheritance must be disabled: $Path"
    }

    $currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $allowedSids = @("S-1-5-18", "S-1-5-32-544", $currentSid)
    foreach ($rule in $acl.Access) {
        if ($rule.IsInherited) {
            throw "Inherited ACL rule is forbidden: $Path"
        }
        if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
            throw "Only explicit Allow ACL rules are accepted: $Path"
        }
        try {
            $sid = $rule.IdentityReference.Translate(
                [System.Security.Principal.SecurityIdentifier]
            ).Value
        }
        catch {
            throw "Unable to resolve an ACL principal on $Path"
        }
        if ($allowedSids -notcontains $sid) {
            throw "Unexpected ACL principal is forbidden on $Path"
        }
    }
}

foreach ($directory in @($InstallRoot, $BinPath, $ConfigPath, $SecretsPath, $LogsPath, $RuntimePath)) {
    Assert-RestrictedAcl -Path $directory -PathType "Container"
}
foreach ($file in @($TunnelClientPath, $ProfileFile, $ControlPlaneKeyFile)) {
    Assert-RestrictedAcl -Path $file -PathType "Leaf"
}
if (-not (Test-Path -LiteralPath $BootstrapPath -PathType Leaf)) {
    throw "Line 1 MCP bootstrap is missing: $BootstrapPath"
}
if ((Get-Item -LiteralPath $ControlPlaneKeyFile).Length -le 0) {
    throw "The Line 1 control-plane key file is empty."
}

# The read-only lane must never inherit mutation-signing material or fallback API keys.
[Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $null, "Process")
[Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $null, "Process")
[Environment]::SetEnvironmentVariable("CONTROL_PLANE_API_KEY", $null, "Process")
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "Process")
[Environment]::SetEnvironmentVariable("DIE_HOME", $RepoRoot, "Process")

$arguments = @(
    "run",
    "--profile-file", $ProfileFile,
    "--control-plane.api-key", $ControlPlaneKeyRef,
    "--health.listen-addr", $HealthListenAddress,
    "--log.file", $LogFile,
    "--log.format", "json",
    "--log.level", "info",
    "--pid.file", $PidFile
)

& $TunnelClientPath @arguments
exit $LASTEXITCODE
