[CmdletBinding()]
param(
    [ValidateSet("Plan", "Installed", "Live")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.runtime-mcp.activation.preflight.v1"
$RepoRoot = "C:\DIE"
$InstallRoot = "C:\ProgramData\DIE\RuntimeMCP"
$ServiceHostPath = Join-Path $RepoRoot "ops\windows\runtime-mcp\die-windows-service.py"
$LauncherPath = Join-Path $RepoRoot "ops\windows\runtime-mcp\Invoke-DIERuntimeMcp.ps1"
$Services = @(
    [ordered]@{
        name = "DIERuntimeMCPExecutive"
        principal_id = "chatgpt-plus-executive"
        lane = "executive"
        port = 8791
        tool_count = 18
        scope = "company_portfolio"
    },
    [ordered]@{
        name = "DIERuntimeMCPDivision01"
        principal_id = "division-head-division01"
        lane = "division01"
        port = 8792
        tool_count = 6
        scope = "single_division"
    }
)
$ReservedPorts = @(8787, 8789, 8790)

if ($Mode -eq "Plan") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        expected_services = @(
            $Services | ForEach-Object {
                [ordered]@{
                    name = $_.name
                    principal_id = $_.principal_id
                    host = "127.0.0.1"
                    port = $_.port
                    expected_tool_count = $_.tool_count
                    scope = $_.scope
                }
            }
        )
        reserved_ports = $ReservedPorts
        installed_checks_executed = $false
        live_checks_executed = $false
        programdata_accessed = $false
        secret_values_read = $false
        secret_values_returned = $false
        writes_performed = $false
        services_started_or_stopped = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP activation verification requires Windows."
}

$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value

function Test-RestrictedAcl {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        return $false
    }
    $allowedSids = @("S-1-5-18", "S-1-5-32-544", $currentSid)
    $observedSids = @()
    foreach ($rule in $acl.Access) {
        if (
            $rule.IsInherited -or
            $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow
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

function Get-SecretMetadataChecks {
    param([Parameter(Mandatory = $true)][System.Collections.IDictionary]$ServiceSpec)

    $root = Join-Path (Join-Path $InstallRoot "secrets") $ServiceSpec.lane
    $specs = @(
        [ordered]@{ name = "mcp-token"; minimum = 32; maximum = 8192 },
        [ordered]@{ name = "mcp-login-password"; minimum = 16; maximum = 8192 },
        [ordered]@{ name = "snapshot-hmac-key"; minimum = 32; maximum = 8192 },
        [ordered]@{ name = "snapshot-hmac-key-id"; minimum = 1; maximum = 128 }
    )
    $rows = @()
    foreach ($spec in $specs) {
        $path = Join-Path $root $spec.name
        $exists = Test-Path -LiteralPath $path -PathType Leaf
        $length = if ($exists) { (Get-Item -LiteralPath $path).Length } else { 0 }
        $rows += [ordered]@{
            name = $spec.name
            exists = $exists
            length_valid = (
                $exists -and
                $length -ge $spec.minimum -and
                $length -le $spec.maximum
            )
            acl_restricted = if ($exists) { Test-RestrictedAcl -Path $path } else { $false }
        }
    }
    return ,$rows
}

$installedRows = @()
$installedReady = Test-RestrictedAcl -Path $InstallRoot
foreach ($service in $Services) {
    $cim = Get-CimInstance Win32_Service -Filter "Name='$($service.name)'" -ErrorAction SilentlyContinue
    $secretChecks = Get-SecretMetadataChecks -ServiceSpec $service
    $serviceExists = $null -ne $cim
    $pathValid = (
        $serviceExists -and
        $cim.PathName.Contains($ServiceHostPath) -and
        $cim.PathName.Contains($LauncherPath) -and
        $cim.PathName.Contains($service.principal_id) -and
        -not $cim.PathName.Contains("DIE_MCP_TOKEN") -and
        -not $cim.PathName.Contains("DIE_SNAPSHOT_HMAC_KEY")
    )
    $rowReady = (
        $serviceExists -and
        $cim.StartMode -eq "Auto" -and
        $cim.StartName -eq "LocalSystem" -and
        $pathValid -and
        @(
            $secretChecks | Where-Object {
                -not $_.exists -or
                -not $_.length_valid -or
                -not $_.acl_restricted
            }
        ).Count -eq 0
    )
    if (-not $rowReady) {
        $installedReady = $false
    }
    $installedRows += [ordered]@{
        name = $service.name
        principal_id = $service.principal_id
        port = $service.port
        exists = $serviceExists
        state = if ($serviceExists) { $cim.State } else { "Missing" }
        startup_automatic = if ($serviceExists) { $cim.StartMode -eq "Auto" } else { $false }
        account_local_system = if ($serviceExists) { $cim.StartName -eq "LocalSystem" } else { $false }
        command_contract_valid = $pathValid
        secret_metadata = $secretChecks
        ready = $rowReady
    }
}

if ($Mode -eq "Installed") {
    [ordered]@{
        schema_version = $SchemaVersion
        mode = "Installed"
        ready = $installedReady
        install_root_acl_restricted = Test-RestrictedAcl -Path $InstallRoot
        services = $installedRows
        secret_values_read = $false
        secret_values_returned = $false
        writes_performed = $false
        services_started_or_stopped = $false
        wake_invoked = $false
        tunnel_invoked = $false
        external_mutation_performed = $false
    } | ConvertTo-Json -Depth 10
    if (-not $installedReady) {
        exit 2
    }
    exit 0
}

if (-not $installedReady) {
    throw "Live verification requires an Installed preflight PASS."
}

function Invoke-JsonRpc {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Payload
    )

    $headers = @{ Authorization = "Bearer $Token" }
    $body = $Payload | ConvertTo-Json -Depth 8 -Compress
    return Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:$Port/mcp" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 15
}

function Test-Unauthenticated401 {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        Invoke-WebRequest `
            -UseBasicParsing `
            -Method Post `
            -Uri "http://127.0.0.1:$Port/mcp" `
            -ContentType "application/json" `
            -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' `
            -TimeoutSec 10 | Out-Null
        return $false
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode -eq 401
        }
        return $false
    }
}

$liveRows = @()
$liveReady = $true
foreach ($service in $Services) {
    $cim = Get-CimInstance Win32_Service -Filter "Name='$($service.name)'"
    if ($cim.State -ne "Running") {
        throw "Runtime MCP service $($service.name) is not running."
    }
    $tokenPath = Join-Path (
        Join-Path (Join-Path $InstallRoot "secrets") $service.lane
    ) "mcp-token"
    $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
    $token = $utf8.GetString([System.IO.File]::ReadAllBytes($tokenPath))
    try {
        $unauth401 = Test-Unauthenticated401 -Port $service.port
        $initialize = Invoke-JsonRpc -Port $service.port -Token $token -Payload ([ordered]@{
            jsonrpc = "2.0"
            id = 1
            method = "initialize"
            params = @{}
        })
        $tools = Invoke-JsonRpc -Port $service.port -Token $token -Payload ([ordered]@{
            jsonrpc = "2.0"
            id = 2
            method = "tools/list"
            params = @{}
        })
        $context = Invoke-JsonRpc -Port $service.port -Token $token -Payload ([ordered]@{
            jsonrpc = "2.0"
            id = 3
            method = "tools/call"
            params = [ordered]@{
                name = "context_snapshot"
                arguments = @{}
            }
        })
        $snapshot = $context.result.content[0].text | ConvertFrom-Json
        $rowReady = (
            $unauth401 -and
            $initialize.result.serverInfo.name -eq "die-runtime-decision-mcp" -and
            $tools.result.tools.Count -eq $service.tool_count -and
            $snapshot.schema_version -eq "die.context.snapshot.v1" -and
            $snapshot.principal.principal_id -eq $service.principal_id -and
            $snapshot.principal.scope -eq $service.scope -and
            $snapshot.integrity.algorithm -eq "HMAC-SHA256" -and
            -not [string]::IsNullOrWhiteSpace($snapshot.integrity.signature)
        )
        if (-not $rowReady) {
            $liveReady = $false
        }
        $liveRows += [ordered]@{
            name = $service.name
            principal_id = $service.principal_id
            port = $service.port
            unauthenticated_status_401 = $unauth401
            initialize_server = $initialize.result.serverInfo.name
            tool_count = $tools.result.tools.Count
            expected_tool_count = $service.tool_count
            snapshot_schema = $snapshot.schema_version
            snapshot_id = $snapshot.snapshot_id
            snapshot_principal = $snapshot.principal.principal_id
            snapshot_scope = $snapshot.principal.scope
            snapshot_signed = (
                $snapshot.integrity.algorithm -eq "HMAC-SHA256" -and
                -not [string]::IsNullOrWhiteSpace($snapshot.integrity.signature)
            )
            ready = $rowReady
        }
    }
    finally {
        $token = $null
    }
}

[ordered]@{
    schema_version = $SchemaVersion
    mode = "Live"
    ready = $liveReady
    services = $liveRows
    secret_values_read = $true
    secret_values_returned = $false
    writes_performed = $false
    services_started_or_stopped = $false
    wake_invoked = $false
    tunnel_invoked = $false
    external_mutation_performed = $false
} | ConvertTo-Json -Depth 10
if (-not $liveReady) {
    exit 2
}
