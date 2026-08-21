[CmdletBinding()]
param(
    [ValidateSet("Plan", "Apply")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secure-runtime.v1"
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
$CreatedDirectories = @()
$ExistingDirectories = @()

function Get-CurrentOperatorSid {
    return [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}

function Assert-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Required protected directory is missing: $Path"
    }

    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        throw "ACL inheritance must be disabled: $Path"
    }

    $allowedSids = @("S-1-5-18", "S-1-5-32-544", $CurrentSid)
    $observedSids = @()
    foreach ($rule in $acl.Access) {
        if ($rule.IsInherited) {
            throw "Inherited ACL rule is forbidden: $Path"
        }
        if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
            throw "Only explicit Allow ACL rules are accepted: $Path"
        }
        if (
            ($rule.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::FullControl) -ne
            [System.Security.AccessControl.FileSystemRights]::FullControl
        ) {
            throw "Every ACL rule must grant FullControl: $Path"
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
        $observedSids += $sid
    }

    foreach ($requiredSid in $allowedSids) {
        if ($observedSids -notcontains $requiredSid) {
            throw "Required ACL principal is missing on $Path"
        }
    }
}

function Protect-DirectoryAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    & icacls.exe $Path /inheritance:r | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to disable inherited ACLs on $Path"
    }

    & icacls.exe $Path /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*$($CurrentSid):(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to apply the restrictive ACL on $Path"
    }
}

function Assert-LaneDirectoryEmpty {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Container) {
        $entries = @(Get-ChildItem -LiteralPath $Path -Force)
        if ($entries.Count -ne 0) {
            throw "B2A refuses to alter a non-empty lane directory: $Path"
        }
    }
}

function Assert-RootSafe {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return
    }

    foreach ($entry in @(Get-ChildItem -LiteralPath $Path -Force)) {
        if (-not $entry.PSIsContainer -or @("line1", "line2") -notcontains $entry.Name) {
            throw "B2A refuses to alter a runtime root containing unexpected entries: $Path"
        }
    }
}

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        validated_parent_directories = @($InstallRoot, $ConfigRoot, $LogsRoot, $RuntimeRoot)
        created_or_hardened_directories = @($SecretsRoot) + $LaneDirectories
        acl_contract = [ordered]@{
            inheritance_disabled = $true
            inherited_rules_allowed = $false
            access_type = "Allow"
            principals = @("S-1-5-18", "S-1-5-32-544", "current-operator")
            rights = "FullControl"
        }
        writes_performed = $false
        secret_files_created = $false
        profile_files_created = $false
        credentials_requested_or_read = $false
        tunnel_identity_requested_or_read = $false
        tunnel_profiles_initialized = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 6
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "B2A secure-runtime Apply requires Windows."
}

$currentSid = Get-CurrentOperatorSid
foreach ($parent in @($InstallRoot, $ConfigRoot, $LogsRoot, $RuntimeRoot)) {
    Assert-RestrictedAcl -Path $parent -CurrentSid $currentSid
}

foreach ($root in @($ConfigRoot, $SecretsRoot, $LogsRoot, $RuntimeRoot)) {
    Assert-RootSafe -Path $root
}
foreach ($directory in $LaneDirectories) {
    Assert-LaneDirectoryEmpty -Path $directory
}

foreach ($directory in @($SecretsRoot) + $LaneDirectories) {
    if (Test-Path -LiteralPath $directory -PathType Container) {
        $ExistingDirectories += $directory
    }
    else {
        New-Item -ItemType Directory -Path $directory | Out-Null
        $CreatedDirectories += $directory
    }
    Protect-DirectoryAcl -Path $directory -CurrentSid $currentSid
    Assert-RestrictedAcl -Path $directory -CurrentSid $currentSid
}

[ordered]@{
    schema_version = $SchemaVersion
    mode = "Apply"
    install_root = $InstallRoot
    created_directories = $CreatedDirectories
    existing_directories = $ExistingDirectories
    protected_directories = @($SecretsRoot) + $LaneDirectories
    acl_restricted = $true
    secret_files_created = $false
    profile_files_created = $false
    credentials_requested_or_read = $false
    tunnel_identity_requested_or_read = $false
    tunnel_profiles_initialized = $false
    tunnel_client_doctor_invoked = $false
    tunnel_client_run_invoked = $false
    mcp_services_started = $false
    windows_service_or_task_created = $false
    external_mutation_performed = $false
} | ConvertTo-Json -Depth 6
