[CmdletBinding()]
param(
    [ValidateSet("Plan", "Provision")]
    [string]$Mode = "Plan",

    [switch]$ConfirmInteractiveProvisioning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secret-provisioning.v1"
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

$SecretSpecs = @(
    [ordered]@{
        id = "line1-control-plane-api-key"
        lane = "line1"
        purpose = "tunnel control-plane authentication"
        path = Join-Path $Line1SecretsRoot "control-plane-api-key"
        minimum_bytes = 1
        format = "opaque-no-whitespace"
    },
    [ordered]@{
        id = "line2-control-plane-api-key"
        lane = "line2"
        purpose = "tunnel control-plane authentication"
        path = Join-Path $Line2SecretsRoot "control-plane-api-key"
        minimum_bytes = 1
        format = "opaque-no-whitespace"
    },
    [ordered]@{
        id = "line2-snapshot-hmac-key"
        lane = "line2"
        purpose = "snapshot HMAC signing"
        path = Join-Path $Line2SecretsRoot "snapshot-hmac-key"
        minimum_bytes = 32
        format = "opaque-no-whitespace"
    },
    [ordered]@{
        id = "line2-snapshot-hmac-key-id"
        lane = "line2"
        purpose = "snapshot HMAC key identifier"
        path = Join-Path $Line2SecretsRoot "snapshot-hmac-key-id"
        minimum_bytes = 1
        maximum_bytes = 128
        format = "ascii-key-id"
    }
)

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
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
            existing_files_overwritten = $false
            rotation_supported = $false
            partial_write_rollback = $true
            secret_values_returned = $false
        }
        acl_contract = [ordered]@{
            inheritance_disabled = $true
            inherited_rules_allowed = $false
            access_type = "Allow"
            principals = @("S-1-5-18", "S-1-5-32-544", "current-operator")
            rights = "FullControl"
        }
        programdata_accessed = $false
        prompts_displayed = $false
        writes_performed = $false
        secret_files_created = $false
        secret_values_read = $false
        tunnel_identity_requested_or_read = $false
        tunnel_profiles_initialized = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "B2B1 secret provisioning requires Windows."
}
if (-not $ConfirmInteractiveProvisioning) {
    throw "Provision mode requires -ConfirmInteractiveProvisioning."
}
if ([Console]::IsInputRedirected) {
    throw "Provision mode requires a directly attached interactive console."
}
if ($Host.UI -eq $null) {
    throw "Provision mode requires an interactive PowerShell host."
}

function Get-CurrentOperatorSid {
    return [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}

function Assert-RestrictedAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("Container", "Leaf")][string]$PathType,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    if (-not (Test-Path -LiteralPath $Path -PathType $PathType)) {
        throw "Required protected path is missing: $Path"
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

function Assert-DirectoryEmpty {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (@(Get-ChildItem -LiteralPath $Path -Force).Count -ne 0) {
        throw "Initial provisioning refuses a non-empty directory: $Path"
    }
}

function Protect-SecretFileAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentSid
    )

    & icacls.exe $Path /inheritance:r | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to disable inherited ACLs on a protected file."
    }
    & icacls.exe $Path /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" "*$($CurrentSid):F" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to apply the restrictive ACL to a protected file."
    }
}

function Read-SecureBytes {
    param([Parameter(Mandatory = $true)][string]$Prompt)

    $secureValue = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [IntPtr]::Zero
    $characters = $null
    try {
        $length = $secureValue.Length
        $characters = New-Object char[] $length
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
        for ($index = 0; $index -lt $length; $index++) {
            $characters[$index] = [char][System.Runtime.InteropServices.Marshal]::ReadInt16(
                $bstr,
                $index * 2
            )
        }
        $encoding = New-Object System.Text.UTF8Encoding($false, $true)
        $bytes = $encoding.GetBytes($characters)
        return ,$bytes
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
    for ($index = 0; $index -lt $Bytes.Length; $index++) {
        $value = [int]$Bytes[$index]
        $alphaNumeric = (
            ($value -ge 48 -and $value -le 57) -or
            ($value -ge 65 -and $value -le 90) -or
            ($value -ge 97 -and $value -le 122)
        )
        if ($index -eq 0) {
            if (-not $alphaNumeric) {
                return $false
            }
        }
        elseif (-not ($alphaNumeric -or @(46, 58, 95, 45) -contains $value)) {
            return $false
        }
    }
    return $true
}

function Read-ConfirmedSecretBytes {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Spec
    )

    $first = $null
    $second = $null
    try {
        $first = Read-SecureBytes -Prompt "Enter $($Spec.id)"
        $second = Read-SecureBytes -Prompt "Confirm $($Spec.id)"
        if (-not (Test-ByteArraysEqual -First $first -Second $second)) {
            throw "Confirmed entries did not match for $($Spec.id)."
        }
        if ($first.Length -lt [int]$Spec.minimum_bytes -or $first.Length -gt 8192) {
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

    $created = $false
    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $created = $true
        $stream.Write($Bytes, 0, $Bytes.Length)
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null

        Protect-SecretFileAcl -Path $Path -CurrentSid $CurrentSid
        Assert-RestrictedAcl -Path $Path -PathType "Leaf" -CurrentSid $CurrentSid
        return $Path
    }
    catch {
        if ($stream -ne $null) {
            $stream.Dispose()
        }
        if ($created -and (Test-Path -LiteralPath $Path -PathType Leaf)) {
            Remove-Item -LiteralPath $Path -Force
        }
        throw
    }
}

$currentSid = Get-CurrentOperatorSid
$protectedDirectories = @(
    $InstallRoot,
    $ConfigRoot,
    $SecretsRoot,
    $LogsRoot,
    $RuntimeRoot,
    $Line1ConfigRoot,
    $Line2ConfigRoot,
    $Line1SecretsRoot,
    $Line2SecretsRoot,
    $Line1LogsRoot,
    $Line2LogsRoot,
    $Line1RuntimeRoot,
    $Line2RuntimeRoot
)
foreach ($directory in $protectedDirectories) {
    Assert-RestrictedAcl -Path $directory -PathType "Container" -CurrentSid $currentSid
}
foreach ($directory in @(
    $Line1ConfigRoot,
    $Line2ConfigRoot,
    $Line1SecretsRoot,
    $Line2SecretsRoot,
    $Line1LogsRoot,
    $Line2LogsRoot,
    $Line1RuntimeRoot,
    $Line2RuntimeRoot
)) {
    Assert-DirectoryEmpty -Path $directory
}
if ($null -ne (Get-Process -Name "tunnel-client" -ErrorAction SilentlyContinue)) {
    throw "Provisioning is forbidden while tunnel-client is running."
}
foreach ($spec in $SecretSpecs) {
    if (Test-Path -LiteralPath $spec.path) {
        throw "Initial provisioning refuses to overwrite an existing protected file."
    }
}

$material = @{}
$createdPaths = @()
try {
    foreach ($spec in $SecretSpecs) {
        $material[$spec.id] = Read-ConfirmedSecretBytes -Spec $spec
    }
    foreach ($spec in $SecretSpecs) {
        $createdPaths += Write-ProtectedBytes -Path $spec.path -Bytes $material[$spec.id] -CurrentSid $currentSid
    }

    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Provision"
        provisioned_ids = @($SecretSpecs | ForEach-Object { $_.id })
        created_file_count = $createdPaths.Count
        acl_restricted = $true
        secret_values_returned = $false
        tunnel_identity_requested_or_read = $false
        tunnel_profiles_initialized = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 6
}
catch {
    foreach ($createdPath in $createdPaths) {
        if (Test-Path -LiteralPath $createdPath -PathType Leaf) {
            Remove-Item -LiteralPath $createdPath -Force
        }
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
