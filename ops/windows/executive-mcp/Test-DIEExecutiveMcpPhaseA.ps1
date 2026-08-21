[CmdletBinding()]
param(
    [ValidateSet("Plan", "Installed")]
    [string]$Mode = "Plan",

    [switch]$SkipOutboundCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.activation.phase-a.preflight.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$BinPath = Join-Path $InstallRoot "bin"
$ConfigPath = Join-Path $InstallRoot "config"
$LogsPath = Join-Path $InstallRoot "logs"
$RuntimePath = Join-Path $InstallRoot "runtime"
$ClientPath = Join-Path $BinPath "tunnel-client.exe"
$ManifestPath = Join-Path $BinPath "tunnel-client.install.json"
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$Line1Bootstrap = Join-Path $RepoRoot "bin\die_executive_line1_mcp.py"
$Line2Bootstrap = Join-Path $RepoRoot "bin\die_executive_mcp.py"

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Invoke-CapturedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $output = (& $Path @Arguments 2>&1 | Out-String).Trim()
    return [pscustomobject]@{
        exit_code = $LASTEXITCODE
        output = $output
    }
}

function Test-TcpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutMs = 5000
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Test-RestrictedAcl {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        return $false
    }
    return @($acl.Access | Where-Object { $_.IsInherited }).Count -eq 0
}

$python = Get-Command python -ErrorAction SilentlyContinue
$checks = [ordered]@{
    running_on_windows = $env:OS -eq "Windows_NT"
    processor_is_amd64 = $env:PROCESSOR_ARCHITECTURE -eq "AMD64"
    repository_root_present = Test-Path -LiteralPath $RepoRoot -PathType Container
    line1_bootstrap_present = Test-Path -LiteralPath $Line1Bootstrap -PathType Leaf
    line2_bootstrap_present = Test-Path -LiteralPath $Line2Bootstrap -PathType Leaf
    python_present = $null -ne $python
    tunnel_client_process_absent = $null -eq (Get-Process -Name "tunnel-client" -ErrorAction SilentlyContinue)
}

if ($SkipOutboundCheck) {
    $checks["api_openai_com_443_reachable"] = $true
}
else {
    $checks["api_openai_com_443_reachable"] = Test-TcpEndpoint -HostName "api.openai.com" -Port 443
}

$evidence = [ordered]@{
    install_root = $InstallRoot
    line1_bootstrap = $Line1Bootstrap
    line2_bootstrap = $Line2Bootstrap
    outbound_probe = if ($SkipOutboundCheck) { "skipped" } else { "unauthenticated TCP api.openai.com:443" }
}

if ($Mode -eq "Installed") {
    foreach ($directory in @($InstallRoot, $BinPath, $ConfigPath, $LogsPath, $RuntimePath)) {
        $leafName = Split-Path -Leaf $directory
        if ($directory -eq $InstallRoot) {
            $leafName = "root"
        }
        $checks["directory_$($leafName)_present"] = Test-Path -LiteralPath $directory -PathType Container
        $checks["directory_$($leafName)_acl_restricted"] = Test-RestrictedAcl -Path $directory
    }

    $checks["client_binary_present"] = Test-Path -LiteralPath $ClientPath -PathType Leaf
    $checks["install_manifest_present"] = Test-Path -LiteralPath $ManifestPath -PathType Leaf

    if ($checks["client_binary_present"] -and $checks["install_manifest_present"]) {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
        $actualBinarySha256 = (Get-FileHash -LiteralPath $ClientPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $checks["manifest_schema_matches"] = $manifest.schema_version -eq "die.executive.mcp.activation.phase-a.v1"
        $checks["manifest_source_is_official"] = $manifest.source.repository -eq "https://github.com/openai/tunnel-client"
        $checks["binary_sha256_matches_manifest"] = $actualBinarySha256 -eq $manifest.verification.installed_binary_sha256

        $versionResult = Invoke-CapturedCommand -Path $ClientPath -Arguments @("--version")
        if ($versionResult.exit_code -ne 0) {
            $versionResult = Invoke-CapturedCommand -Path $ClientPath -Arguments @("version")
        }
        $helpResult = Invoke-CapturedCommand -Path $ClientPath -Arguments @("help", "quickstart")
        $releaseVersion = ([string]$manifest.source.release_tag).TrimStart("v")

        $checks["version_command_succeeds"] = $versionResult.exit_code -eq 0
        $checks["version_matches_manifest_release"] = $versionResult.output -match [regex]::Escape($releaseVersion)
        $checks["quickstart_help_succeeds"] = $helpResult.exit_code -eq 0 -and -not [string]::IsNullOrWhiteSpace($helpResult.output)
        $checks["quickstart_help_matches_manifest"] = (Get-StringSha256 -Value $helpResult.output) -eq $manifest.verification.help_output_sha256

        $evidence["release_tag"] = $manifest.source.release_tag
        $evidence["release_url"] = $manifest.source.release_url
        $evidence["asset_url"] = $manifest.source.asset_url
        $evidence["binary_sha256"] = $actualBinarySha256
        $evidence["version_output"] = $versionResult.output
        $evidence["help_command"] = "tunnel-client.exe help quickstart"
        $evidence["authenticode_status"] = $manifest.verification.authenticode_status
    }

    $checks["bootstrap_workspace_clean"] = @(
        Get-ChildItem -LiteralPath $RuntimePath -Directory -Filter "phase-a-*" -ErrorAction SilentlyContinue
    ).Count -eq 0
}

$failedChecks = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
$result = [ordered]@{
    schema_version = $SchemaVersion
    mode = $Mode
    ready = $failedChecks.Count -eq 0
    checks = $checks
    failed_checks = $failedChecks
    evidence = $evidence
    secret_values_returned = $false
    tunnel_profiles_initialized = $false
    tunnel_created_or_modified = $false
    mcp_services_started = $false
    windows_service_or_task_created = $false
}

$result | ConvertTo-Json -Depth 7
if ($failedChecks.Count -gt 0) {
    exit 2
}
