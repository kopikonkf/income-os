$ErrorActionPreference = 'Stop'

$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path $Edge)) { throw "EDGE_NOT_FOUND:$Edge" }

$MuxiaRoot = if ($env:MUXIA_ROOT) { $env:MUXIA_ROOT } else { 'C:\DIE\workspaces\MUXIA-B04\muxia-root' }
$ProfileId = if ($env:MUXIA_PROFILE_ID) { $env:MUXIA_PROFILE_ID } else { 'chatgpt-a' }
$ProfileDir = Join-Path $MuxiaRoot "profiles\$ProfileId\edge-auth"
$StateDir = Join-Path $MuxiaRoot 'state'
$Receipt = Join-Path $StateDir 'mx032-edge-auth-bootstrap.json'

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

# Intentionally no remote-debugging, automation, stealth, or bypass flags during auth bootstrap.
$proc = Start-Process -FilePath $Edge -ArgumentList @("--user-data-dir=$ProfileDir", 'https://chatgpt.com/auth/login') -PassThru
Start-Sleep -Seconds 2

$window = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
$record = [ordered]@{
  schema = 'die.muxia.mx032.edge-auth-bootstrap.v1'
  task_id = 'MX-032-R1'
  mode = 'OPERATOR_CONTROLLED_NORMAL_EDGE'
  browser = 'Microsoft Edge Stable'
  browser_path = $Edge
  browser_pid = $proc.Id
  session_id = if ($window) { $window.SessionId } else { $null }
  profile_id = $ProfileId
  profile_dir = $ProfileDir
  provider_url = 'https://chatgpt.com/auth/login'
  remote_debugging_enabled = $false
  playwright_attached = $false
  automation_flags_added = $false
  credential_values_read_by_muxia = $false
  bypass_attempted = $false
  opened_at = (Get-Date).ToUniversalTime().ToString('o')
  status = 'WAITING_OPERATOR_LOGIN'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $Receipt -Encoding UTF8
$record | ConvertTo-Json -Depth 5
