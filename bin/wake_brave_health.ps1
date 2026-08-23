# Health check / starter for the Division-01 wake Brave instance.
# If :9333 is dead, starts Brave (Profile "plus") with remote debugging.
# Safe to run repeatedly (idempotent). Log: C:\DIE\logs\wake_brave_health.log
$ErrorActionPreference = "SilentlyContinue"
$log = "C:\DIE\logs\wake_brave_health.log"
New-Item -ItemType Directory -Force -Path "C:\DIE\logs" | Out-Null

function Log($m) { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK') $m" }

function Test-Cdp {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:9333/json/version" -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

if (Test-Cdp) {
    Log "OK cdp 9333 alive"
    exit 0
}

Log "CDP 9333 DEAD - starting brave wake instance"
$brave = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
$ud = "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\User Data"
Start-Process $brave -ArgumentList @(
    "--remote-debugging-port=9333",
    "--user-data-dir=`"$ud`"",
    '--profile-directory="Profile 3"',
    "--no-first-run",
    "--window-position=-32000,-32000",
    "https://chatgpt.com/"
)
Start-Sleep -Seconds 8
if (Test-Cdp) { Log "OK cdp 9333 started" } else { Log "FAIL cdp 9333 still down" }
