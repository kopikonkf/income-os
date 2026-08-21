[CmdletBinding()]
param(
    [ValidateSet("Plan", "Installed")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secret-provisioning.preflight.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$ConfigRoot = Join-Path $InstallRoot "config"
$SecretsRoot = Join-Path $InstallRoot "secrets"
$LogsRoot = Join-Path $InstallRoot "logs"
$RuntimeRoot = Join-Path $InstallRoot "runtime"
$Line1ConfigRoot = Join-Path $ConfigRoot "line1"
$Line2ConfigRoot = Join-Path $ConfigRoot "line2"
$Line1SecretsRoot = Join-Path $SecretsRoot "line1"
$Line2SecretsRoot = Join-Path $SecretsRoot "line2"
$Line1LogsRoot = Join-Path $LogsRoot "line1"
$Line2LogsRoot = Join-Path $LogsRoot "line2"
$Line1RuntimeRoot = Join-Path $RuntimeRoot "line1"
$Line2RuntimeRoot = Join-Path $RuntimeRoot "line2"
$Line1ControlPlaneKey = Join-Path $Line1SecretsRoot "control-plane-api-key"
$Line2ControlPlaneKey = Join-Path $Line2SecretsRoot "control-plane-api-key"
$Line2SnapshotHmacKey = Join-Path $Line2SecretsRoot "snapshot-hmac-key"
$Line2SnapshotHmacKeyId = Join-Path $Line2SecretsRoot "snapshot-hmac-key-id"
$ExpectedSecretFiles = @(
    $Line1ControlPlaneKey,
    $Line2ControlPlaneKey,
    $Line2SnapshotHmacKey,
    $Line2SnapshotHmacKeyId
)

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        expected_secret_files = $ExpectedSecretFiles
        expected_line1_file_count = 1
        expected_line2_file_count = 3
        programdata_accessed = $false
        secret_values_read = $false
        profile_contents_read = $false
        writes_performed = $false
        tunnel_identity_requested_or_read = $false
        tunnel_profiles_initialized = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 5
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "B2B1 Installed verification requires Windows."
}

function Test-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("Container", "Leaf")][string]$PathType,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    if (-not (Test-Path -LiteralPath $Path -PathType $PathType)) {
        return $false
    }

    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        return $false
    }

    $allowedSids = @("S-1-5-18", "S-1-5-32-544", $CurrentSid)
    $observedSids = @()
    foreach ($rule in $acl.Access) {
        if ($rule.IsInherited) {
            return $false
        }
        if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
            return $false
        }
        if (
            ($rule.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -ne
            [System.Security.AccessControl.FileSystemRights]::FullControl
        ) {
            return $false
        }
        try {
            $sid = $rule.IdentityReference.Translate(
                [System.Security.Principal.SecurityIdentifier]
            ).Value
        }
        catch {
            return $false
        }
        if ($allowedSids -notcontains $sid) {
            return $false
        }
        $observedSids += $sid
    }
    foreach ($requiredSid in $allowedSids) {
        if ($observedSids -notcontains $requiredSid) {
            return $false
        }
    }
    return $true
}

function Test-DirectoryHasExactFiles {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string[]]$ExpectedNames
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    $entries = @(Get-ChildItem -LiteralPath $Path -Force)
    if ($entries.Count -ne $ExpectedNames.Count) {
        return $false
    }
    foreach ($entry in $entries) {
        if (-not $entry.PSIsContainer -and $ExpectedNames -contains $entry.Name) {
            continue
        }
        return $false
    }
    return $true
}

function Test-DirectoryEmpty {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (
        (Test-Path -LiteralPath $Path -PathType Container) -and
        @(Get-ChildItem -LiteralPath $Path -Force).Count -eq 0
    )
}

$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$checks = [ordered]@{
    line1_secrets_directory_acl_restricted = Test-RestrictedAcl -Path $Line1SecretsRoot -PathType "Container" -CurrentSid $currentSid
    line2_secrets_directory_acl_restricted = Test-RestrictedAcl -Path $Line2SecretsRoot -PathType "Container" -CurrentSid $currentSid
    line1_secret_topology_exact = Test-DirectoryHasExactFiles -Path $Line1SecretsRoot -ExpectedNames @("control-plane-api-key")
    line2_secret_topology_exact = Test-DirectoryHasExactFiles -Path $Line2SecretsRoot -ExpectedNames @(
        "control-plane-api-key",
        "snapshot-hmac-key",
        "snapshot-hmac-key-id"
    )
    line1_config_directory_empty = Test-DirectoryEmpty -Path $Line1ConfigRoot
    line2_config_directory_empty = Test-DirectoryEmpty -Path $Line2ConfigRoot
    line1_logs_directory_empty = Test-DirectoryEmpty -Path $Line1LogsRoot
    line2_logs_directory_empty = Test-DirectoryEmpty -Path $Line2LogsRoot
    line1_runtime_directory_empty = Test-DirectoryEmpty -Path $Line1RuntimeRoot
    line2_runtime_directory_empty = Test-DirectoryEmpty -Path $Line2RuntimeRoot
    tunnel_client_process_absent = $null -eq (Get-Process -Name "tunnel-client" -ErrorAction SilentlyContinue)
}

foreach ($path in $ExpectedSecretFiles) {
    $id = $path.Substring($SecretsRoot.Length + 1).Replace("\", "_").Replace("-", "_")
    $checks["secret_$($id)_present"] = Test-Path -LiteralPath $path -PathType Leaf
    $checks["secret_$($id)_acl_restricted"] = Test-RestrictedAcl -Path $path -PathType "Leaf" -CurrentSid $currentSid
    $minimumLength = if ($path -eq $Line2SnapshotHmacKey) { 32 } else { 1 }
    $maximumLength = if ($path -eq $Line2SnapshotHmacKeyId) { 128 } else { 8192 }
    $length = if (Test-Path -LiteralPath $path -PathType Leaf) {
        (Get-Item -LiteralPath $path).Length
    }
    else {
        0
    }
    $checks["secret_$($id)_length_contract"] = $length -ge $minimumLength -and $length -le $maximumLength
}

$failedChecks = @(
    $checks.GetEnumerator() |
        Where-Object { -not [bool]$_.Value } |
        ForEach-Object { $_.Key }
)
$ready = $failedChecks.Count -eq 0

[ordered]@{
    schema_version = $SchemaVersion
    mode = "Installed"
    ready = $ready
    checks = $checks
    failed_checks = $failedChecks
    evidence = [ordered]@{
        expected_secret_file_count = 4
        secret_values_read = $false
        profile_contents_read = $false
        tunnel_identity_requested_or_read = $false
    }
    safety = [ordered]@{
        writes_performed = $false
        tunnel_profiles_initialized = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_mutation_performed = $false
    }
} | ConvertTo-Json -Depth 8

if (-not $ready) {
    exit 1
}
