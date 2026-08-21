[CmdletBinding()]
param(
    [ValidateSet("Plan", "Apply")]
    [string]$Mode = "Plan",

    [switch]$SkipReleaseDiscovery
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.activation.phase-a.v1"
$OfficialRepository = "https://github.com/openai/tunnel-client"
$OfficialReleaseApi = "https://api.github.com/repos/openai/tunnel-client/releases/latest"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$BinPath = Join-Path $InstallRoot "bin"
$ConfigPath = Join-Path $InstallRoot "config"
$LogsPath = Join-Path $InstallRoot "logs"
$RuntimePath = Join-Path $InstallRoot "runtime"
$ClientPath = Join-Path $BinPath "tunnel-client.exe"
$ManifestPath = Join-Path $BinPath "tunnel-client.install.json"

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
    $exitCode = $LASTEXITCODE
    return [pscustomobject]@{
        command = "$([System.IO.Path]::GetFileName($Path)) $($Arguments -join ' ')"
        exit_code = $exitCode
        output = $output
    }
}

function Get-OfficialTunnelClientRelease {
    $headers = @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "DIE-ExecutiveMCP-PhaseA-v1"
        "X-GitHub-Api-Version" = "2022-11-28"
    }
    $release = Invoke-RestMethod -Method Get -Uri $OfficialReleaseApi -Headers $headers

    if ($release.draft -or $release.prerelease) {
        throw "Latest release is not a stable public release."
    }
    if ($release.html_url -notmatch '^https://github\.com/openai/tunnel-client/releases/tag/') {
        throw "Release source is outside the official openai/tunnel-client repository."
    }

    $assetPattern = '^tunnel-client-v[0-9]+\.[0-9]+\.[0-9]+-windows-amd64\.zip$'
    $assets = @($release.assets | Where-Object { $_.name -match $assetPattern })
    if ($assets.Count -ne 1) {
        throw "Expected exactly one official Windows AMD64 tunnel-client archive."
    }

    $checksumAssets = @($release.assets | Where-Object { $_.name -eq "SHA256SUMS.txt" })
    if ($checksumAssets.Count -ne 1) {
        throw "Expected the official SHA256SUMS.txt release asset."
    }

    $asset = $assets[0]
    $checksumAsset = $checksumAssets[0]
    $releaseSegment = [regex]::Escape([string]$release.tag_name)
    if ($asset.browser_download_url -notmatch "^https://github\.com/openai/tunnel-client/releases/download/$releaseSegment/") {
        throw "Archive URL is outside the official release."
    }
    if ($checksumAsset.browser_download_url -notmatch "^https://github\.com/openai/tunnel-client/releases/download/$releaseSegment/") {
        throw "Checksum URL is outside the official release."
    }

    return [pscustomobject]@{
        tag = [string]$release.tag_name
        published_at = [string]$release.published_at
        release_url = [string]$release.html_url
        asset_name = [string]$asset.name
        asset_url = [string]$asset.browser_download_url
        asset_size = [int64]$asset.size
        checksum_name = [string]$checksumAsset.name
        checksum_url = [string]$checksumAsset.browser_download_url
    }
}

function Get-ExpectedArchiveSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$ChecksumFile,
        [Parameter(Mandatory = $true)][string]$AssetName
    )

    foreach ($line in Get-Content -LiteralPath $ChecksumFile) {
        if ($line -match '^(?<hash>[A-Fa-f0-9]{64})\s+\*?(?<name>.+)$') {
            if ($Matches.name.Trim() -eq $AssetName) {
                return $Matches.hash.ToLowerInvariant()
            }
        }
    }
    throw "Official checksum entry was not found for $AssetName."
}

function Protect-DirectoryAcl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CurrentUserSid
    )

    & icacls.exe $Path /inheritance:r | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to disable inherited ACLs on $Path."
    }

    & icacls.exe $Path /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*$($CurrentUserSid):(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to apply the restrictive ACL on $Path."
    }
}

$plannedDirectories = @($BinPath, $ConfigPath, $LogsPath, $RuntimePath)
$release = $null
if (-not $SkipReleaseDiscovery) {
    $release = Get-OfficialTunnelClientRelease
}
elseif ($Mode -eq "Apply") {
    throw "Release discovery cannot be skipped in Apply mode."
}

if ($Mode -eq "Plan") {
    [pscustomobject]@{
        schema_version = $SchemaVersion
        mode = "Plan"
        install_root = $InstallRoot
        directories = $plannedDirectories
        official_repository = $OfficialRepository
        release = $release
        actions = @(
            "Create fixed non-secret runtime directories",
            "Apply protected ACLs for SYSTEM, Administrators, and the invoking identity",
            "Download the official Windows AMD64 release archive and SHA256SUMS.txt",
            "Verify official archive checksum, binary version, and quickstart help",
            "Install tunnel-client.exe and its non-secret verification manifest under bin"
        )
        writes_performed = $false
        tunnel_profiles_initialized = $false
        tunnel_created_or_modified = $false
        credentials_requested_or_read = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
    } | ConvertTo-Json -Depth 6
    exit 0
}

if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    throw "Phase A v1 currently supports Windows AMD64 only."
}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$currentSid = $identity.User.Value

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
foreach ($directory in $plannedDirectories) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
Protect-DirectoryAcl -Path $InstallRoot -CurrentUserSid $currentSid
foreach ($directory in $plannedDirectories) {
    Protect-DirectoryAcl -Path $directory -CurrentUserSid $currentSid
}

$workPath = Join-Path $RuntimePath ("phase-a-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $workPath $release.asset_name
$checksumPath = Join-Path $workPath $release.checksum_name
$extractPath = Join-Path $workPath "expanded"

New-Item -ItemType Directory -Path $workPath -Force | Out-Null
try {
    Invoke-WebRequest -UseBasicParsing -Uri $release.checksum_url -OutFile $checksumPath
    Invoke-WebRequest -UseBasicParsing -Uri $release.asset_url -OutFile $archivePath

    $expectedArchiveSha256 = Get-ExpectedArchiveSha256 -ChecksumFile $checksumPath -AssetName $release.asset_name
    $actualArchiveSha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualArchiveSha256 -ne $expectedArchiveSha256) {
        throw "Official archive SHA-256 mismatch."
    }

    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force
    $clientCandidates = @(Get-ChildItem -LiteralPath $extractPath -Filter "tunnel-client.exe" -File -Recurse)
    if ($clientCandidates.Count -ne 1) {
        throw "Expected exactly one tunnel-client.exe in the official archive."
    }

    $candidatePath = $clientCandidates[0].FullName
    $candidateSha256 = (Get-FileHash -LiteralPath $candidatePath -Algorithm SHA256).Hash.ToLowerInvariant()

    $versionResult = Invoke-CapturedCommand -Path $candidatePath -Arguments @("--version")
    if ($versionResult.exit_code -ne 0) {
        $versionResult = Invoke-CapturedCommand -Path $candidatePath -Arguments @("version")
    }
    if ($versionResult.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($versionResult.output)) {
        throw "The downloaded tunnel-client did not provide a successful version response."
    }

    $releaseVersion = $release.tag.TrimStart("v")
    if ($versionResult.output -notmatch [regex]::Escape($releaseVersion)) {
        throw "The downloaded tunnel-client version does not match the official release tag."
    }

    $helpResult = Invoke-CapturedCommand -Path $candidatePath -Arguments @("help", "quickstart")
    if ($helpResult.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($helpResult.output)) {
        throw "The downloaded tunnel-client did not provide successful quickstart help."
    }

    Copy-Item -LiteralPath $candidatePath -Destination $ClientPath -Force
    $installedSha256 = (Get-FileHash -LiteralPath $ClientPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($installedSha256 -ne $candidateSha256) {
        throw "Installed tunnel-client SHA-256 differs from the verified binary."
    }

    $signature = Get-AuthenticodeSignature -LiteralPath $ClientPath
    $manifest = [ordered]@{
        schema_version = $SchemaVersion
        installed_at_utc = [DateTime]::UtcNow.ToString("o")
        source = [ordered]@{
            repository = $OfficialRepository
            release_tag = $release.tag
            published_at = $release.published_at
            release_url = $release.release_url
            asset_name = $release.asset_name
            asset_url = $release.asset_url
            checksum_asset_url = $release.checksum_url
        }
        verification = [ordered]@{
            official_archive_sha256 = $expectedArchiveSha256
            downloaded_archive_sha256 = $actualArchiveSha256
            installed_binary_sha256 = $installedSha256
            authenticode_status = [string]$signature.Status
            signer_subject = if ($null -ne $signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
            version_command = $versionResult.command
            version_output = $versionResult.output
            version_exit_code = $versionResult.exit_code
            help_command = $helpResult.command
            help_output_sha256 = Get-StringSha256 -Value $helpResult.output
            help_exit_code = $helpResult.exit_code
        }
        installation = [ordered]@{
            root = $InstallRoot
            binary_path = $ClientPath
            directories = $plannedDirectories
            invoking_identity_sid = $currentSid
            acl_inheritance_disabled = $true
        }
        safety = [ordered]@{
            tunnel_profiles_initialized = $false
            tunnel_created_or_modified = $false
            credentials_requested_or_read = $false
            mcp_services_started = $false
            windows_service_or_task_created = $false
        }
    }

    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
    Protect-DirectoryAcl -Path $BinPath -CurrentUserSid $currentSid

    [pscustomobject]@{
        schema_version = $SchemaVersion
        mode = "Apply"
        release_tag = $release.tag
        binary_path = $ClientPath
        manifest_path = $ManifestPath
        binary_sha256 = $installedSha256
        version_verified = $true
        help_verified = $true
        acl_restricted = $true
        tunnel_profiles_initialized = $false
        tunnel_created_or_modified = $false
        credentials_requested_or_read = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
    } | ConvertTo-Json -Depth 5
}
finally {
    if (Test-Path -LiteralPath $workPath) {
        Remove-Item -LiteralPath $workPath -Recurse -Force
    }
}
