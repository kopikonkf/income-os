[CmdletBinding()]
param(
    [ValidateSet("Plan", "ApplyIngress", "ApplyDns")]
    [string]$Mode = "Plan",

    [switch]$ConfirmEdgeMutation,

    [switch]$AllowDnsOverwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.runtime-mcp.edge.v1"
$CloudflaredPath = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$CloudflaredConfig = "C:\Users\aethers\.cloudflared\config.yml"
$TunnelId = "8f53133f-d1c8-48d6-b5bf-4dbe6f65b816"
$TunnelTarget = "${TunnelId}.cfargotunnel.com"
$Mappings = @(
    [ordered]@{
        principal_id = "chatgpt-plus-executive"
        hostname = "executive-mcp.aethers.web.id"
        upstream = "http://localhost:8791"
    },
    [ordered]@{
        principal_id = "division-head-division01"
        hostname = "division01-mcp.aethers.web.id"
        upstream = "http://localhost:8792"
    }
)

function New-Receipt {
    param(
        [Parameter(Mandatory = $true)][string]$ReceiptMode,
        [Parameter(Mandatory = $true)][bool]$ConfigChanged,
        [Parameter(Mandatory = $true)][bool]$DnsChanged
    )

    return [ordered]@{
        schema_version = $SchemaVersion
        mode = $ReceiptMode
        transport = "existing-self-hosted-cloudflared"
        tunnel_id = $TunnelId
        mappings = $Mappings
        principal_pinning = "one-hostname-one-principal-one-loopback-upstream"
        shared_endpoint = $false
        token_based_proxy_routing = $false
        aether_caddy_dependency = $false
        p2_tunnel_client_dependency = $false
        openai_control_plane_api_key_required = $false
        paid_infrastructure_required = $false
        config_changed = $ConfigChanged
        dns_changed = $DnsChanged
        secrets_read = $false
        secret_values_read = $false
        secret_values_returned = $false
        runtime_services_started_or_stopped = $false
        wake_invoked = $false
    }
}

if ($Mode -eq "Plan") {
    $receipt = New-Receipt -ReceiptMode "Plan" -ConfigChanged $false -DnsChanged $false
    $receipt.cloudflare_config_accessed = $false
    $receipt.dns_queried = $false
    $receipt.cloudflared_service_restarted = $false
    $receipt.external_mutation_performed = $false
    $receipt | ConvertTo-Json -Depth 8
    exit 0
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP edge mutation requires Windows."
}
if (-not $ConfirmEdgeMutation) {
    throw "$Mode requires -ConfirmEdgeMutation and separate Founder authorization."
}
if (-not (Test-Path -LiteralPath $CloudflaredPath -PathType Leaf)) {
    throw "The existing cloudflared executable is missing."
}

if ($Mode -eq "ApplyIngress") {
    if (-not (Test-Path -LiteralPath $CloudflaredConfig -PathType Leaf)) {
        throw "The existing cloudflared configuration is missing."
    }

    $original = [System.IO.File]::ReadAllText($CloudflaredConfig)
    if ($original -notmatch "(?m)^\s*ingress:\s*$") {
        throw "Cloudflared configuration has no ingress section."
    }
    if ($original -notmatch "(?m)^\s*-\s*service:\s*http_status:404\s*$") {
        throw "Cloudflared configuration must retain a terminal deny-by-default 404 rule."
    }

    $missing = @()
    foreach ($mapping in $Mappings) {
        $hostnamePattern = "(?m)^\s*-\s*hostname:\s*" + [regex]::Escape($mapping.hostname) + "\s*$"
        $count = ([regex]::Matches($original, $hostnamePattern)).Count
        if ($count -gt 1) {
            throw "Duplicate hostname route is forbidden: $($mapping.hostname)"
        }
        if ($count -eq 1) {
            $routePattern = (
                "(?ms)^\s*-\s*hostname:\s*" + [regex]::Escape($mapping.hostname) +
                "\s*\r?\n\s*service:\s*" + [regex]::Escape($mapping.upstream) + "\s*(?:\r?\n|$)"
            )
            if ($original -notmatch $routePattern) {
                throw "Existing hostname route has the wrong upstream: $($mapping.hostname)"
            }
        }
        else {
            $missing += $mapping
        }
    }

    & $CloudflaredPath tunnel --config $CloudflaredConfig ingress validate | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Existing Cloudflared ingress validation failed."
    }

    if ($missing.Count -eq 0) {
        $receipt = New-Receipt -ReceiptMode "ApplyIngress" -ConfigChanged $false -DnsChanged $false
        $receipt.cloudflare_config_accessed = $true
        $receipt.cloudflared_ingress_validated = $true
        $receipt.cloudflared_service_restarted = $false
        $receipt.external_mutation_performed = $false
        $receipt | ConvertTo-Json -Depth 8
        exit 0
    }

    $lines = @()
    foreach ($mapping in $missing) {
        $lines += "  - hostname: $($mapping.hostname)"
        $lines += "    service: $($mapping.upstream)"
    }
    $fragment = ($lines -join [Environment]::NewLine) + [Environment]::NewLine
    $updated = [regex]::Replace(
        $original,
        "(?m)^(\s*ingress:\s*\r?\n)",
        ('$1' + $fragment),
        1
    )
    $backup = "$CloudflaredConfig.die-runtime-mcp-edge-v1.bak"
    if (Test-Path -LiteralPath $backup) {
        throw "Refusing to overwrite an existing edge backup."
    }

    Copy-Item -LiteralPath $CloudflaredConfig -Destination $backup
    try {
        [System.IO.File]::WriteAllText(
            $CloudflaredConfig,
            $updated,
            (New-Object System.Text.UTF8Encoding($false))
        )
        & $CloudflaredPath tunnel --config $CloudflaredConfig ingress validate | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Cloudflared ingress validation failed."
        }
        $service = Get-Service -Name "Cloudflared" -ErrorAction Stop
        Restart-Service -Name $service.Name -ErrorAction Stop
        Remove-Item -LiteralPath $backup -Force
    }
    catch {
        $failure = $_
        Copy-Item -LiteralPath $backup -Destination $CloudflaredConfig -Force
        try {
            Restart-Service -Name "Cloudflared" -ErrorAction Stop
        }
        catch {
            # The original mutation failure remains authoritative. The restored
            # config is left on disk for a local operator recovery action.
        }
        throw $failure
    }

    $receipt = New-Receipt -ReceiptMode "ApplyIngress" -ConfigChanged $true -DnsChanged $false
    $receipt.cloudflare_config_accessed = $true
    $receipt.cloudflared_ingress_validated = $true
    $receipt.cloudflared_service_restarted = $true
    $receipt.external_mutation_performed = $true
    $receipt | ConvertTo-Json -Depth 8
    exit 0
}

$dnsChanged = $false
foreach ($mapping in $Mappings) {
    $records = @(
        Resolve-DnsName -Name $mapping.hostname -Type CNAME -ErrorAction SilentlyContinue |
            Where-Object { $_.Type -eq "CNAME" }
    )
    $targets = @($records | ForEach-Object { $_.NameHost.TrimEnd(".") })
    if ($targets -contains $TunnelTarget) {
        continue
    }
    if ($targets.Count -gt 0 -and -not $AllowDnsOverwrite) {
        throw "Existing DNS route differs; explicit -AllowDnsOverwrite is required."
    }
    $arguments = @("tunnel", "route", "dns")
    if ($AllowDnsOverwrite) {
        $arguments += "--overwrite-dns"
    }
    $arguments += @($TunnelId, $mapping.hostname)
    & $CloudflaredPath @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Cloudflare tunnel DNS route."
    }
    $dnsChanged = $true
}

$receipt = New-Receipt -ReceiptMode "ApplyDns" -ConfigChanged $false -DnsChanged $dnsChanged
$receipt.cloudflare_config_accessed = $false
$receipt.dns_queried = $true
$receipt.cloudflared_service_restarted = $false
$receipt.external_mutation_performed = $dnsChanged
$receipt | ConvertTo-Json -Depth 8
