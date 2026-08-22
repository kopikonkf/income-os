[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("chatgpt-plus-executive", "division-head-division01")]
    [string]$PrincipalId,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = "C:\DIE"
$InstallRoot = "C:\ProgramData\DIE\RuntimeMCP"
$Bindings = @{
    "chatgpt-plus-executive" = [ordered]@{
        lane = "executive"
        port = 8791
    }
    "division-head-division01" = [ordered]@{
        lane = "division01"
        port = 8792
    }
}

if ($env:OS -ne "Windows_NT") {
    throw "Runtime MCP launcher requires Windows."
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Configured Python interpreter is missing."
}
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
    throw "Canonical DIE repository root is missing."
}

$binding = $Bindings[$PrincipalId]
$secretsRoot = Join-Path (Join-Path $InstallRoot "secrets") $binding.lane
$tokenPath = Join-Path $secretsRoot "mcp-token"
$hmacPath = Join-Path $secretsRoot "snapshot-hmac-key"
$keyIdPath = Join-Path $secretsRoot "snapshot-hmac-key-id"
foreach ($path in @($tokenPath, $hmacPath, $keyIdPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "A required Runtime MCP secret file is missing."
    }
}

$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
$token = $utf8.GetString([System.IO.File]::ReadAllBytes($tokenPath))
$hmacKey = $utf8.GetString([System.IO.File]::ReadAllBytes($hmacPath))
$keyId = $utf8.GetString([System.IO.File]::ReadAllBytes($keyIdPath))
if ($token.Length -lt 32 -or $token -match "\s") {
    throw "Runtime MCP token violates the local secret contract."
}
if ($hmacKey.Length -lt 32 -or $hmacKey -match "\s") {
    throw "Snapshot HMAC key violates the local secret contract."
}
if ($keyId -cnotmatch "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$") {
    throw "Snapshot HMAC key identifier violates the local secret contract."
}

$previousPythonPath = $env:PYTHONPATH
$previousDieHome = $env:DIE_HOME
$previousPrincipal = $env:DIE_RUNTIME_PRINCIPAL_ID
$previousToken = $env:DIE_MCP_TOKEN
$previousHmac = $env:DIE_SNAPSHOT_HMAC_KEY
$previousKeyId = $env:DIE_SNAPSHOT_HMAC_KEY_ID
try {
    $env:PYTHONPATH = Join-Path $RepoRoot "bridge"
    $env:DIE_HOME = $RepoRoot
    $env:DIE_RUNTIME_PRINCIPAL_ID = $PrincipalId
    $env:DIE_MCP_TOKEN = $token
    $env:DIE_SNAPSHOT_HMAC_KEY = $hmacKey
    $env:DIE_SNAPSHOT_HMAC_KEY_ID = $keyId

    & $PythonPath -m income_os_bridge.runtime_mcp_server `
        --principal-id $PrincipalId `
        --port ([int]$binding.port)
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:DIE_HOME = $previousDieHome
    $env:DIE_RUNTIME_PRINCIPAL_ID = $previousPrincipal
    $env:DIE_MCP_TOKEN = $previousToken
    $env:DIE_SNAPSHOT_HMAC_KEY = $previousHmac
    $env:DIE_SNAPSHOT_HMAC_KEY_ID = $previousKeyId
    $token = $null
    $hmacKey = $null
    $keyId = $null
}
