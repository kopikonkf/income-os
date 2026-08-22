[CmdletBinding()]
param(
    [ValidateSet("Plan", "Install")]
    [string]$Mode = "Plan",

    [string]$PythonPath,

    [switch]$ConfirmServiceInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.runtime-mcp.services.v1"
$RepoRoot = "C:\DIE"
$InstallRoot = "C:\ProgramData\DIE\RuntimeMCP"
$PowerShellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$ServiceHostPath = Join-Path $RepoRoot "ops\windows\runtime-mcp\die-windows-service.py"
$LauncherPath = Join-Path $RepoRoot "ops\windows\runtime-mcp\Invoke-DIERuntimeMcp.ps1"
$Services = @(
    [ordered]@{
        name = "DIERuntimeMCPExecutive"
        display_name = "DIE Runtime MCP - Executive"
        description = "Principal-pinned least-privilege Decision MCP for ChatGPT Executive."
        principal_id = "chatgpt-plus-executive"
        lane = "executive"
        port = 8791
    },
    [ordered]@{
        name = "DIERuntimeMCPDivision01"
        display_name = "DIE Runtime MCP - Division 01"
        description = "Principal-pinned least-privilege Decision MCP for DIVISION-01."
        principal_id = "division-head-division01"
        lane = "division01"
        port = 8792
    }
)
$ReservedPorts = @(8787, 8789, 8790)

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        repo_root = $RepoRoot
        install_root = $InstallRoot
        service_host = $ServiceHostPath
        launcher = $LauncherPath
        services = @(
            $Services | ForEach-Object {
                [ordered]@{
                    name = $_.name
                    display_name = $_.display_name
                    principal_id = $_.principal_id
                    host = "127.0.0.1"
                    port = $_.port
                    startup = "Automatic"
                    account = "LocalSystem"
                    failure_restart_ms = @(5000, 15000, 60000)
                }
            }
        )
        reserved_ports = $ReservedPorts
        execution_contract = [ordered]@{
            explicit_confirmation_switch_required = $true
            provisioned_secret_metadata_required = $true
            service_binary_contains_secret = $false
            existing_service_overwritten = $false
            port_collision_allowed = $false
            rollback_on_partial_install = $true
        }
        programdata_accessed = $false
        secret_values_read = $false
        secret_values_returned = $false
        services_created = $false
        services_started = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP service installation requires Windows."
}
if (-not $ConfirmServiceInstall) {
    throw "Install mode requires -ConfirmServiceInstall."
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Runtime MCP service installation requires an elevated Administrator console."
}
if (-not $PythonPath) {
    $pythonCommand = Get-Command python.exe -ErrorAction Stop
    $PythonPath = $pythonCommand.Source
}
foreach ($path in @($PythonPath, $PowerShellPath, $ServiceHostPath, $LauncherPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "A required activation executable or script is missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $InstallRoot -PathType Container)) {
    throw "Runtime MCP secure root is missing; run interactive Provision first."
}

function Assert-RestrictedAcl {
    param([Parameter(Mandatory = $true)][string]$Path)

    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        throw "ACL inheritance must be disabled: $Path"
    }
    $allowedSids = @("S-1-5-18", "S-1-5-32-544", $identity.User.Value)
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

function Assert-SecretMetadata {
    param([Parameter(Mandatory = $true)][System.Collections.IDictionary]$ServiceSpec)

    $root = Join-Path (Join-Path $InstallRoot "secrets") $ServiceSpec.lane
    $specs = @(
        [ordered]@{ name = "mcp-token"; minimum = 32; maximum = 8192 },
        [ordered]@{ name = "mcp-login-password"; minimum = 16; maximum = 8192 },
        [ordered]@{ name = "snapshot-hmac-key"; minimum = 32; maximum = 8192 },
        [ordered]@{ name = "snapshot-hmac-key-id"; minimum = 1; maximum = 128 }
    )
    Assert-RestrictedAcl -Path $root
    foreach ($spec in $specs) {
        $path = Join-Path $root $spec.name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required secret metadata is missing for $($ServiceSpec.principal_id)."
        }
        $length = (Get-Item -LiteralPath $path).Length
        if ($length -lt $spec.minimum -or $length -gt $spec.maximum) {
            throw "Secret file length violates the activation contract."
        }
        Assert-RestrictedAcl -Path $path
    }
}

foreach ($port in $ReservedPorts) {
    if ($Services.port -contains $port) {
        throw "A Runtime MCP binding collides with an infrastructure-reserved port."
    }
}
foreach ($service in $Services) {
    if ($null -ne (Get-Service -Name $service.name -ErrorAction SilentlyContinue)) {
        throw "Install mode refuses to overwrite an existing Runtime MCP service."
    }
    if ($null -ne (Get-NetTCPConnection -State Listen -LocalPort $service.port -ErrorAction SilentlyContinue)) {
        throw "Runtime MCP port $($service.port) is already occupied."
    }
    Assert-SecretMetadata -ServiceSpec $service
}

$created = @()
try {
    foreach ($service in $Services) {
        $eventLogPath = Join-Path (
            Join-Path (Join-Path $InstallRoot "logs") $service.lane
        ) "service-events.jsonl"
        $binaryPath = (
            '"{0}" "{1}" --service-name {2} --working-directory "{3}" ' +
            '--event-log-path "{4}" -- "{5}" -NoProfile -ExecutionPolicy Bypass ' +
            '-File "{6}" -PrincipalId {7} -PythonPath "{0}"'
        ) -f (
            $PythonPath,
            $ServiceHostPath,
            $service.name,
            $RepoRoot,
            $eventLogPath,
            $PowerShellPath,
            $LauncherPath,
            $service.principal_id
        )

        $null = New-Service `
            -Name $service.name `
            -BinaryPathName $binaryPath `
            -DisplayName $service.display_name `
            -Description $service.description `
            -StartupType Automatic `
            -ErrorAction Stop
        $created += $service.name

        $createdService = Get-CimInstance `
            Win32_Service `
            -Filter "Name='$($service.name)'" `
            -ErrorAction Stop
        if (
            $createdService.StartMode -ne "Auto" -or
            $createdService.StartName -ne "LocalSystem"
        ) {
            throw "Created Runtime MCP service violates the startup/account contract."
        }
        & sc.exe failure $service.name "reset= 86400" "actions= restart/5000/restart/15000/restart/60000" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to configure Windows service recovery."
        }
        & sc.exe failureflag $service.name 1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to enable Windows service failure actions."
        }
    }

    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Install"
        created_services = $created
        startup = "Automatic"
        account = "LocalSystem"
        service_binary_contains_secret = $false
        secret_values_read = $false
        secret_values_returned = $false
        services_started = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 6
}
catch {
    foreach ($serviceName in $created) {
        & sc.exe delete $serviceName | Out-Null
    }
    throw
}
