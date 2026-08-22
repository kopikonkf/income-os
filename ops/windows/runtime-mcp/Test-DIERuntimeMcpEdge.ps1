[CmdletBinding()]
param(
    [ValidateSet("Plan", "Configured", "Public")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.runtime-mcp.edge.verification.v1"
$CloudflaredPath = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$CloudflaredConfig = "C:\Users\aethers\.cloudflared\config.yml"
$TunnelId = "8f53133f-d1c8-48d6-b5bf-4dbe6f65b816"
$TunnelTarget = "${TunnelId}.cfargotunnel.com"
$Mappings = @(
    [ordered]@{
        principal_id = "chatgpt-plus-executive"
        hostname = "executive-mcp.aethers.web.id"
        upstream = "http://localhost:8791"
        expected_tool_count = 18
    },
    [ordered]@{
        principal_id = "division-head-division01"
        hostname = "division01-mcp.aethers.web.id"
        upstream = "http://localhost:8792"
        expected_tool_count = 6
    }
)

function New-BaseReceipt {
    param([Parameter(Mandatory = $true)][string]$ReceiptMode)

    return [ordered]@{
        schema_version = $SchemaVersion
        mode = $ReceiptMode
        mappings = $Mappings
        direct_cloudflared_ingress = $true
        principal_pinning = "one-hostname-one-principal-one-loopback-upstream"
        anti_cross_routing = "exact-host-and-upstream-match"
        shared_endpoint = $false
        aether_caddy_dependency = $false
        p2_tunnel_client_dependency = $false
        paid_infrastructure_required = $false
        secret_values_read = $false
        secret_values_returned = $false
        writes_performed = $false
        services_started_or_stopped = $false
        wake_invoked = $false
        external_mutation_performed = $false
    }
}

if ($Mode -eq "Plan") {
    $receipt = New-BaseReceipt -ReceiptMode "Plan"
    $receipt.cloudflare_config_accessed = $false
    $receipt.dns_queried = $false
    $receipt.public_requests_performed = $false
    $receipt | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP edge verification requires Windows."
}

if ($Mode -eq "Configured") {
    if (-not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) {
        throw "The existing cloudflared executable is missing."
    }
    if (-not (Test-Path -LiteralPath $CloudflaredConfig -PathType Leaf)) {
        throw "The existing cloudflared configuration is missing."
    }
    $source = [System.IO.File]::ReadAllText($CloudflaredConfig)
    $rows = @()
    $ready = $true
    foreach ($mapping in $Mappings) {
        $hostnamePattern = "(?m)^\s*-\s*hostname:\s*" + [regex]::Escape($mapping.hostname) + "\s*$"
        $routePattern = (
            "(?ms)^\s*-\s*hostname:\s*" + [regex]::Escape($mapping.hostname) +
            "\s*\r?\n\s*service:\s*" + [regex]::Escape($mapping.upstream) + "\s*(?:\r?\n|$)"
        )
        $routeCount = ([regex]::Matches($source, $hostnamePattern)).Count
        $routeExact = $routeCount -eq 1 -and $source -match $routePattern
        $records = @(
            Resolve-DnsName -Name $mapping.hostname -Type CNAME -ErrorAction SilentlyContinue |
                Where-Object { $_.Type -eq "CNAME" }
        )
        $targets = @($records | ForEach-Object { $_.NameHost.TrimEnd(".") })
        $dnsExact = $targets -contains $TunnelTarget
        $rowReady = $routeExact -and $dnsExact
        if (-not $rowReady) {
            $ready = $false
        }
        $rows += [ordered]@{
            principal_id = $mapping.principal_id
            hostname = $mapping.hostname
            upstream = $mapping.upstream
            route_count = $routeCount
            route_exact = $routeExact
            dns_target_exact = $dnsExact
            ready = $rowReady
        }
    }
    $terminalDeny = $source -match "(?m)^\s*-\s*service:\s*http_status:404\s*$"
    & $CloudflaredPath tunnel --config $CloudflaredConfig ingress validate | Out-Null
    $ingressValid = $LASTEXITCODE -eq 0
    $service = Get-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
    $ready = $ready -and $terminalDeny -and $ingressValid -and $null -ne $service

    $receipt = New-BaseReceipt -ReceiptMode "Configured"
    $receipt.ready = $ready
    $receipt.routes = $rows
    $receipt.terminal_deny_default = $terminalDeny
    $receipt.cloudflared_ingress_valid = $ingressValid
    $receipt.cloudflared_service_present = $null -ne $service
    $receipt.cloudflare_config_accessed = $true
    $receipt.dns_queried = $true
    $receipt.public_requests_performed = $false
    $receipt | ConvertTo-Json -Depth 8
    if (-not $ready) {
        exit 2
    }
    exit 0
}

function Invoke-UnauthenticatedProbe {
    param([Parameter(Mandatory = $true)][string]$Uri)

    try {
        Invoke-WebRequest `
            -UseBasicParsing `
            -Method Post `
            -Uri $Uri `
            -ContentType "application/json" `
            -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' `
            -TimeoutSec 15 | Out-Null
        return $false
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode -eq 401
        }
        return $false
    }
}

$publicRows = @()
$publicReady = $true
foreach ($mapping in $Mappings) {
    $baseUrl = "https://$($mapping.hostname)"
    $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/health" -TimeoutSec 15
    $authority = Invoke-RestMethod `
        -Method Get `
        -Uri "$baseUrl/.well-known/oauth-authorization-server/mcp" `
        -TimeoutSec 15
    $resource = Invoke-RestMethod `
        -Method Get `
        -Uri "$baseUrl/.well-known/oauth-protected-resource/mcp" `
        -TimeoutSec 15
    $unauth401 = Invoke-UnauthenticatedProbe -Uri "$baseUrl/mcp"
    $rowReady = (
        $health.ok -eq $true -and
        $health.principal_id -eq $mapping.principal_id -and
        [int]$health.tools -eq [int]$mapping.expected_tool_count -and
        $authority.issuer -eq $baseUrl -and
        $resource.resource -eq "$baseUrl/mcp" -and
        $unauth401
    )
    if (-not $rowReady) {
        $publicReady = $false
    }
    $publicRows += [ordered]@{
        principal_id = $mapping.principal_id
        hostname = $mapping.hostname
        health_ok = $health.ok
        tool_count = $health.tools
        expected_tool_count = $mapping.expected_tool_count
        issuer_exact = $authority.issuer -eq $baseUrl
        resource_exact = $resource.resource -eq "$baseUrl/mcp"
        unauthenticated_status_401 = $unauth401
        ready = $rowReady
    }
}

$receipt = New-BaseReceipt -ReceiptMode "Public"
$receipt.ready = $publicReady
$receipt.public = $publicRows
$receipt.cloudflare_config_accessed = $false
$receipt.dns_queried = $false
$receipt.public_requests_performed = $true
$receipt | ConvertTo-Json -Depth 8
if (-not $publicReady) {
    exit 2
}
