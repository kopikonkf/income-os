[CmdletBinding()]
param(
    [ValidateSet("Plan", "Provision")]
    [string]$Mode = "Plan",

    [switch]$ConfirmInteractiveProvisioning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.runtime-mcp.activation.v1"
$InstallRoot = "C:\ProgramData\DIE\RuntimeMCP"
$Lanes = @(
    [ordered]@{
        id = "executive"
        principal_id = "chatgpt-plus-executive"
        port = 8791
    },
    [ordered]@{
        id = "division01"
        principal_id = "division-head-division01"
        port = 8792
    }
)
$TopLevelDirectories = @("config", "secrets", "logs", "runtime")
$SecretNames = @("mcp-token", "snapshot-hmac-key", "snapshot-hmac-key-id")

function Get-LaneRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$LaneId
    )
    return Join-Path (Join-Path $InstallRoot $Kind) $LaneId
}

$ProtectedDirectories = @($InstallRoot)
foreach ($kind in $TopLevelDirectories) {
    $ProtectedDirectories += Join-Path $InstallRoot $kind
    foreach ($lane in $Lanes) {
        $ProtectedDirectories += Get-LaneRoot -Kind $kind -LaneId $lane.id
    }
}

$SecretSpecs = @()
foreach ($lane in $Lanes) {
    $secretRoot = Get-LaneRoot -Kind "secrets" -LaneId $lane.id
    $SecretSpecs += [ordered]@{
        id = "$($lane.id)-mcp-token"
        lane = $lane.id
        purpose = "principal-pinned Runtime MCP bearer authentication"
        path = Join-Path $secretRoot "mcp-token"
        minimum_bytes = 32
        maximum_bytes = 8192
        format = "opaque-no-whitespace"
    }
    $SecretSpecs += [ordered]@{
        id = "$($lane.id)-snapshot-hmac-key"
        lane = $lane.id
        purpose = "principal-pinned context snapshot HMAC signing"
        path = Join-Path $secretRoot "snapshot-hmac-key"
        minimum_bytes = 32
        maximum_bytes = 8192
        format = "opaque-no-whitespace"
    }
    $SecretSpecs += [ordered]@{
        id = "$($lane.id)-snapshot-hmac-key-id"
        lane = $lane.id
        purpose = "context snapshot HMAC key identifier"
        path = Join-Path $secretRoot "snapshot-hmac-key-id"
        minimum_bytes = 1
        maximum_bytes = 128
        format = "ascii-key-id"
    }
}

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        principals = @(
            $Lanes | ForEach-Object {
                [ordered]@{
                    lane = $_.id
                    principal_id = $_.principal_id
                    host = "127.0.0.1"
                    port = $_.port
                }
            }
        )
        protected_directories = $ProtectedDirectories
        secret_files = @(
            $SecretSpecs | ForEach-Object {
                [ordered]@{
                    id = $_.id
                    lane = $_.lane
                    purpose = $_.purpose
                    path = $_.path
                    format = $_.format
                }
            }
        )
        execution_contract = [ordered]@{
            operator = "Founder or explicitly delegated local VPS operator"
            interactive_console_required = $true
            explicit_confirmation_switch_required = $true
            prompts_use_secure_string = $true
            confirmation_entry_required = $true
            existing_root_overwritten = $false
            secret_values_returned = $false
            partial_provision_rollback = $true
        }
        acl_contract = [ordered]@{
            inheritance_disabled = $true
            inherited_rules_allowed = $false
            access_type = "Allow"
            principals = @("S-1-5-18", "S-1-5-32-544", "current-operator")
            rights = "FullControl"
        }
        reserved_ports = @(8787, 8789, 8790)
        programdata_accessed = $false
        prompts_displayed = $false
        writes_performed = $false
        secret_files_created = $false
        secret_values_read = $false
        services_created = $false
        services_started = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP provisioning requires Windows."
}
if (-not $ConfirmInteractiveProvisioning) {
    throw "Provision mode requires -ConfirmInteractiveProvisioning."
}
if ([Console]::IsInputRedirected -or $Host.UI -eq $null) {
    throw "Provision mode requires a directly attached interactive PowerShell console."
}
if (Test-Path -LiteralPath $InstallRoot) {
    throw "Initial provisioning refuses to alter an existing RuntimeMCP root."
}
foreach ($lane in $Lanes) {
    $serviceName = if ($lane.id -eq "executive") {
        "DIERuntimeMCPExecutive"
    }
    else {
        "DIERuntimeMCPDivision01"
    }
    if ($null -ne (Get-Service -Name $serviceName -ErrorAction SilentlyContinue)) {
        throw "Initial provisioning refuses an existing Runtime MCP service."
    }
}

function Get-CurrentOperatorSid {
    return [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}

function Protect-PathAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid,
        [Parameter(Mandatory = $true)][bool]$Container
    )

    & icacls.exe $Path /inheritance:r | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to disable inherited ACLs on a protected path."
    }
    if ($Container) {
        & icacls.exe $Path /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*$($CurrentSid):(OI)(CI)F" | Out-Null
    }
    else {
        & icacls.exe $Path /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" "*$($CurrentSid):F" | Out-Null
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to apply the restrictive ACL to a protected path."
    }
}

function Assert-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

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
        try {
            $sid = $rule.IdentityReference.Translate(
                [System.Security.Principal.SecurityIdentifier]
            ).Value
        }
        catch {
            throw "Unable to resolve an ACL principal on a protected path."
        }
        if ($allowedSids -notcontains $sid) {
            throw "Unexpected ACL principal is forbidden: $Path"
        }
        $observedSids += $sid
    }
    foreach ($requiredSid in $allowedSids) {
        if ($observedSids -notcontains $requiredSid) {
            throw "Required ACL principal is missing: $Path"
        }
    }
}

function Read-SecureBytes {
    param([Parameter(Mandatory = $true)][string]$Prompt)

    $secureValue = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [IntPtr]::Zero
    $characters = $null
    try {
        $characters = New-Object char[] $secureValue.Length
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
        for ($index = 0; $index -lt $secureValue.Length; $index++) {
            $characters[$index] = [char][System.Runtime.InteropServices.Marshal]::ReadInt16(
                $bstr,
                $index * 2
            )
        }
        $encoding = New-Object System.Text.UTF8Encoding($false, $true)
        return ,$encoding.GetBytes($characters)
    }
    finally {
        if ($characters -ne $null) {
            [Array]::Clear($characters, 0, $characters.Length)
        }
        if ($bstr -ne [IntPtr]::Zero) {
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        if ($secureValue -ne $null) {
            $secureValue.Dispose()
        }
    }
}

function Test-ByteArraysEqual {
    param(
        [Parameter(Mandatory = $true)][byte[]]$First,
        [Parameter(Mandatory = $true)][byte[]]$Second
    )

    if ($First.Length -ne $Second.Length) {
        return $false
    }
    $difference = 0
    for ($index = 0; $index -lt $First.Length; $index++) {
        $difference = $difference -bor ($First[$index] -bxor $Second[$index])
    }
    return $difference -eq 0
}

function Test-NoAsciiWhitespace {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)

    foreach ($value in $Bytes) {
        if (@(9, 10, 11, 12, 13, 32) -contains [int]$value) {
            return $false
        }
    }
    return $true
}

function Test-AsciiKeyId {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)

    if ($Bytes.Length -lt 1 -or $Bytes.Length -gt 128) {
        return $false
    }
    $text = [System.Text.Encoding]::ASCII.GetString($Bytes)
    return $text -cmatch "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
}

function Read-ConfirmedSecretBytes {
    param([Parameter(Mandatory = $true)][System.Collections.IDictionary]$Spec)

    $first = $null
    $second = $null
    try {
        $first = Read-SecureBytes -Prompt "Enter $($Spec.id)"
        $second = Read-SecureBytes -Prompt "Confirm $($Spec.id)"
        if (-not (Test-ByteArraysEqual -First $first -Second $second)) {
            throw "Confirmed entries did not match for $($Spec.id)."
        }
        if (
            $first.Length -lt [int]$Spec.minimum_bytes -or
            $first.Length -gt [int]$Spec.maximum_bytes
        ) {
            throw "Protected value length violates the contract for $($Spec.id)."
        }
        if ($Spec.format -eq "opaque-no-whitespace" -and -not (Test-NoAsciiWhitespace -Bytes $first)) {
            throw "Whitespace is forbidden for $($Spec.id)."
        }
        if ($Spec.format -eq "ascii-key-id" -and -not (Test-AsciiKeyId -Bytes $first)) {
            throw "The snapshot HMAC key identifier format is invalid."
        }
        [Array]::Clear($second, 0, $second.Length)
        $second = $null
        return ,$first
    }
    catch {
        if ($first -ne $null) {
            [Array]::Clear($first, 0, $first.Length)
        }
        throw
    }
    finally {
        if ($second -ne $null) {
            [Array]::Clear($second, 0, $second.Length)
        }
    }
}

function Write-ProtectedBytes {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][byte[]]$Bytes,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    $stream = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($Bytes, 0, $Bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
    Protect-PathAcl -Path $Path -CurrentSid $CurrentSid -Container $false
    Assert-RestrictedAcl -Path $Path -CurrentSid $CurrentSid
}

$currentSid = Get-CurrentOperatorSid
$material = @{}
$rootCreated = $false
try {
    New-Item -ItemType Directory -Path $InstallRoot | Out-Null
    $rootCreated = $true
    foreach ($directory in $ProtectedDirectories | Select-Object -Skip 1) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
    foreach ($directory in $ProtectedDirectories) {
        Protect-PathAcl -Path $directory -CurrentSid $currentSid -Container $true
        Assert-RestrictedAcl -Path $directory -CurrentSid $currentSid
    }
    foreach ($spec in $SecretSpecs) {
        $material[$spec.id] = Read-ConfirmedSecretBytes -Spec $spec
    }
    foreach ($spec in $SecretSpecs) {
        Write-ProtectedBytes -Path $spec.path -Bytes $material[$spec.id] -CurrentSid $currentSid
    }

    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Provision"
        install_root = $InstallRoot
        provisioned_ids = @($SecretSpecs | ForEach-Object { $_.id })
        created_file_count = $SecretSpecs.Count
        acl_restricted = $true
        secret_values_returned = $false
        services_created = $false
        services_started = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 6
}
catch {
    if ($rootCreated -and (Test-Path -LiteralPath $InstallRoot)) {
        Remove-Item -LiteralPath $InstallRoot -Recurse -Force
    }
    throw
}
finally {
    foreach ($entry in @($material.GetEnumerator())) {
        if ($entry.Value -ne $null) {
            [Array]::Clear($entry.Value, 0, $entry.Value.Length)
        }
    }
    $material.Clear()
}
