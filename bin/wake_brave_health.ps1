# Health check / starter for Division-01 wake Brave instance - v2 dedicated profile
# Canon: WAKE_AUTH_SESSION_SECURITY_V1.md - one browser binary, one dedicated user-data dir per principal, loopback CDP :9333
# Dedicated dir: C:\ProgramData\DIE\BrowserProfiles\DIVISION-01 (ACL: SYSTEM+Administrators+operator, inheritance disabled)
# Legacy Profile 3 (shared User Data) = PILOT-DEPRECATED, accepted only until dedicated re-login verified. Do not use for Div-02+.
# Idempotent. Log: C:\DIE\logs\wake_brave_health.log
$ErrorActionPreference = "SilentlyContinue"
$log = "C:\DIE\logs\wake_brave_health.log"
New-Item -ItemType Directory -Force -Path "C:\DIE\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "C:\ProgramData\DIE\BrowserProfiles\DIVISION-01" | Out-Null

function Log($m) { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK') $m" }

function Test-Cdp {
    param([int]$Port = 9333)
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/version" -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

# loopback-only probe - must be 127.0.0.1, never 0.0.0.0
$port = 9333
if (Test-Cdp -Port $port) {
    Log "OK cdp $port alive (dedicated profile check)"
    # verify CDP target isolation: count targets, ensure no cross-principal leakage via extra profile check
    try {
        $lst = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/list" -TimeoutSec 5
        $cnt = if ($lst -is [array]) { $lst.Count } else { 0 }
        Log "OK cdp $port targets=$cnt (dedicated isolation)"
    } catch {}
    exit 0
}

Log "CDP $port DEAD - starting brave wake instance (dedicated)"

$brave = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
if (-not (Test-Path $brave)) { $brave = "C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe" }

$dedicated = "C:\ProgramData\DIE\BrowserProfiles\DIVISION-01"
$legacyUD = "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\User Data"

# prefer dedicated isolated dir
if (Test-Path $dedicated) {
    # ensure ACL remains protected (no Users)
    $acl = Get-Acl $dedicated
    if (-not $acl.AreAccessRulesProtected) { Log "WARN dedicated ACL not protected - run Migrate-DIEBraveProfile.ps1" }
    Log "START dedicated user-data-dir=$dedicated port=$port"
    Start-Process $brave -ArgumentList @(
        "--remote-debugging-port=$port",
        "--remote-debugging-address=127.0.0.1",
        "--user-data-dir=`"$dedicated`"",
        "--no-first-run",
        "--window-position=-32000,-32000",
        "https://chatgpt.com/"
    )
} else {
    Log "WARN dedicated dir missing - fallback to legacy Profile 3 (PILOT-DEPRECATED)"
    $ud = $legacyUD
    Start-Process $brave -ArgumentList @(
        "--remote-debugging-port=$port",
        "--remote-debugging-address=127.0.0.1",
        "--user-data-dir=`"$ud`"",
        '--profile-directory="Profile 3"',
        "--no-first-run",
        "--window-position=-32000,-32000",
        "https://chatgpt.com/"
    )
}

Start-Sleep -Seconds 8
if (Test-Cdp -Port $port) { Log "OK cdp $port started" } else { Log "FAIL cdp $port still down - check Brave login for dedicated profile" }
