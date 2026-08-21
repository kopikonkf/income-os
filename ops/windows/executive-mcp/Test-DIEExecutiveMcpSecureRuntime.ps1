[CmdletBinding()]
param(
    [ValidateSet("Plan", "Installed")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secure-runtime.preflight.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$ConfigRoot = Join-Path $InstallRoot "config"
$SecretsRoot = Join-Path $InstallRoot "secrets"
$LogsRoot = Join-Path $InstallRoot "logs"
$RuntimeRoot = Join-Path $InstallRoot "runtime"
$LaneDirectories = @(
    (Join-Path $ConfigRoot "line1"),
    (Join-Path $ConfigRoot "line2"),
    (Join-Path $SecretsRoot "line1"),
    (Join-Path $SecretsRoot "line2"),
    (Join-Path $LogsRoot "line1"),
    (Join-Path $LogsRoot "line2"),
    (Join-Path $RuntimeRoot "line1"),
    (Join-Path $RuntimeRoot "line2")
)

function Test-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
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

function Test-RootContainsOnlyLaneDirectories {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }

    $entries = @(Get-ChildItem -LiteralPath $Path -Force)
    if ($entries.Count -ne 2) {
        return $false
    }
    foreach ($entry in $entries) {
        if (-not $entry.PSIsContainer -or @("line1", "line2") -notcontains $entry.Name) {
            return $false
        }
    }
    return $true
}

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        directories_to_verify = @($SecretsRoot) + $LaneDirectories
        programdata_accessed = $false
        secret_values_read = $false
        profile_contents_read = $false
        writes_performed = $false
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
    throw "B2A secure-runtime Installed verification requires Windows."
}

$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$checks = [ordered]@{
    install_root_present = Test-Path -LiteralPath $InstallRoot -PathType Container
    install_root_acl_restricted = Test-RestrictedAcl -Path $InstallRoot -CurrentSid $currentSid
    config_root_acl_restricted = Test-RestrictedAcl -Path $ConfigRoot -CurrentSid $currentSid
    logs_root_acl_restricted = Test-RestrictedAcl -Path $LogsRoot -CurrentSid $currentSid
    runtime_root_acl_restricted = Test-RestrictedAcl -Path $RuntimeRoot -CurrentSid $currentSid
    secrets_root_present = Test-Path -LiteralPath $SecretsRoot -PathType Container
    secrets_root_acl_restricted = Test-RestrictedAcl -Path $SecretsRoot -CurrentSid $currentSid
    config_root_contains_only_lane_directories = Test-RootContainsOnlyLaneDirectories -Path $ConfigRoot
    secrets_root_contains_only_lane_directories = Test-RootContainsOnlyLaneDirectories -Path $SecretsRoot
    logs_root_contains_only_lane_directories = Test-RootContainsOnlyLaneDirectories -Path $LogsRoot
    runtime_root_contains_only_lane_directories = Test-RootContainsOnlyLaneDirectories -Path $RuntimeRoot
    tunnel_client_process_absent = $null -eq (Get-Process -Name "tunnel-client" -ErrorAction SilentlyContinue)
}

foreach ($directory in $LaneDirectories) {
    $relative = $directory.Substring($InstallRoot.Length + 1).Replace("\", "_")
    $checks["directory_$($relative)_present"] = Test-Path -LiteralPath $directory -PathType Container
    $checks["directory_$($relative)_acl_restricted"] = Test-RestrictedAcl -Path $directory -CurrentSid $currentSid

    $entries = @()
    if (Test-Path -LiteralPath $directory -PathType Container) {
        $entries = @(Get-ChildItem -LiteralPath $directory -Force)
    }
    $checks["directory_$($relative)_contains_no_entries"] = $entries.Count -eq 0
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
        install_root = $InstallRoot
        verified_directories = @($SecretsRoot) + $LaneDirectories
        secret_values_read = $false
        profile_contents_read = $false
    }
    safety = [ordered]@{
        writes_performed = $false
        credentials_requested_or_read = $false
        tunnel_identity_requested_or_read = $false
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
