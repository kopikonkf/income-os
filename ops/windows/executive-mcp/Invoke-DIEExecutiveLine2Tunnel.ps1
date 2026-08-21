[CmdletBinding()]
param(
    [ValidateSet("Plan", "Run")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.lane-wrapper.line2.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$BinPath = Join-Path $InstallRoot "bin"
$ConfigPath = Join-Path $InstallRoot "config\line2"
$SecretsPath = Join-Path $InstallRoot "secrets\line2"
$LogsPath = Join-Path $InstallRoot "logs\line2"
$RuntimePath = Join-Path $InstallRoot "runtime\line2"
$TunnelClientPath = Join-Path $BinPath "tunnel-client.exe"
$ProfileFile = Join-Path $ConfigPath "executive-line2.yaml"
$ControlPlaneKeyFile = Join-Path $SecretsPath "control-plane-api-key"
$ControlPlaneKeyRef = "file:$ControlPlaneKeyFile"
$SnapshotHmacKeyFile = Join-Path $SecretsPath "snapshot-hmac-key"
$SnapshotHmacKeyIdFile = Join-Path $SecretsPath "snapshot-hmac-key-id"
$LogFile = Join-Path $LogsPath "tunnel-client.jsonl"
$PidFile = Join-Path $RuntimePath "tunnel-client.pid"
$HealthListenAddress = "127.0.0.1:18102"
$RepoRoot = "C:\DIE"
$BootstrapPath = Join-Path $RepoRoot "bin\die_executive_mcp.py"

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        lane = "line2"
        install_root = $InstallRoot
        tunnel_client = $TunnelClientPath
        profile_file = $ProfileFile
        control_plane_api_key_ref = $ControlPlaneKeyRef
        snapshot_hmac_key_file = $SnapshotHmacKeyFile
        snapshot_hmac_key_id_file = $SnapshotHmacKeyIdFile
        bootstrap = $BootstrapPath
        health_listen_address = $HealthListenAddress
        log_file = $LogFile
        pid_file = $PidFile
        hmac_injection = "process-scoped"
        hmac_cleared_on_exit = $true
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

function Read-ProtectedSecret {
    param([Parameter(Mandatory = $true)][string]$Path)

    $value = [System.IO.File]::ReadAllText($Path)
    $value = $value.TrimEnd([char[]]@([char]13, [char]10))
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "A required protected secret file is empty."
    }
    return $value
}

foreach ($directory in @($InstallRoot, $BinPath, $ConfigPath, $SecretsPath, $LogsPath, $RuntimePath)) {
    Assert-RestrictedAcl -Path $directory -PathType "Container"
}
foreach ($file in @(
    $TunnelClientPath,
    $ProfileFile,
    $ControlPlaneKeyFile,
    $SnapshotHmacKeyFile,
    $SnapshotHmacKeyIdFile
)) {
    Assert-RestrictedAcl -Path $file -PathType "Leaf"
}
if (-not (Test-Path -LiteralPath $BootstrapPath -PathType Leaf)) {
    throw "Line 2 MCP bootstrap is missing: $BootstrapPath"
}
if ((Get-Item -LiteralPath $ControlPlaneKeyFile).Length -le 0) {
    throw "The Line 2 control-plane key file is empty."
}

$hmacKey = $null
$hmacKeyId = $null
$exitCode = 1
try {
    $hmacKey = Read-ProtectedSecret -Path $SnapshotHmacKeyFile
    $hmacKeyId = Read-ProtectedSecret -Path $SnapshotHmacKeyIdFile

    if ([System.Text.Encoding]::UTF8.GetByteCount($hmacKey) -lt 32) {
        throw "Snapshot HMAC key material must contain at least 32 bytes."
    }
    if ($hmacKeyId -notmatch "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$") {
        throw "Snapshot HMAC key identifier format is invalid."
    }

    # File-backed control-plane auth stays with tunnel-client. HMAC is scoped only
    # to this wrapper process, tunnel-client, and its Line 2 MCP child.
    [Environment]::SetEnvironmentVariable("CONTROL_PLANE_API_KEY", $null, "Process")
    [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "Process")
    [Environment]::SetEnvironmentVariable("DIE_HOME", $RepoRoot, "Process")
    [Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $hmacKey, "Process")
    [Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $hmacKeyId, "Process")

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
    $exitCode = $LASTEXITCODE
}
finally {
    [Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY", $null, "Process")
    [Environment]::SetEnvironmentVariable("DIE_SNAPSHOT_HMAC_KEY_ID", $null, "Process")
    $hmacKey = $null
    $hmacKeyId = $null
}
exit $exitCode
