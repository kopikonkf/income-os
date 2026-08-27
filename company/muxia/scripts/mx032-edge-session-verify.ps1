$ErrorActionPreference = 'Stop'

$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$MuxiaRoot = if ($env:MUXIA_ROOT) { $env:MUXIA_ROOT } else { 'C:\DIE\workspaces\MUXIA-B04\muxia-root' }
$ProfileId = if ($env:MUXIA_PROFILE_ID) { $env:MUXIA_PROFILE_ID } else { 'chatgpt-a' }
$ProfileDir = Join-Path $MuxiaRoot "profiles\$ProfileId\edge-auth"
$StateDir = Join-Path $MuxiaRoot 'state'
$SessionFile = Join-Path $StateDir 'mx032-edge-session-verify.json'
$DevToolsFile = Join-Path $ProfileDir 'DevToolsActivePort'

if (-not (Test-Path $ProfileDir)) { throw 'EDGE_AUTH_PROFILE_MISSING' }
Remove-Item $DevToolsFile -Force -ErrorAction SilentlyContinue

# Relaunch same authenticated profile, now with loopback CDP only for sanitized state verification.
$args = @(
  "--user-data-dir=$ProfileDir",
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=0',
  '--no-first-run',
  '--no-default-browser-check',
  'https://chatgpt.com/'
)
$proc = Start-Process -FilePath $Edge -ArgumentList $args -PassThru

$deadline = (Get-Date).AddSeconds(20)
$port = $null
while ((Get-Date) -lt $deadline) {
  if ($proc.HasExited) { throw "EDGE_EXITED_EARLY:$($proc.ExitCode)" }
  try {
    if (Test-Path $DevToolsFile) {
      $lines = Get-Content $DevToolsFile -ErrorAction Stop
      if ($lines.Count -ge 1 -and [int]::TryParse($lines[0], [ref]$port) -and $port -gt 0) { break }
    }
  } catch {
    Start-Sleep -Milliseconds 100
    continue
  }
  Start-Sleep -Milliseconds 100
}
if (-not $port) { throw 'DEVTOOLS_PORT_TIMEOUT' }

$record = [ordered]@{
  schema = 'die.muxia.mx032.edge-session-verify.v1'
  task_id = 'MX-032-R1'
  profile_id = $ProfileId
  profile_dir = $ProfileDir
  browser = 'Microsoft Edge Stable'
  browser_pid = $proc.Id
  session_id = $proc.SessionId
  debug_host = '127.0.0.1'
  debug_port = $port
  opened_at = (Get-Date).ToUniversalTime().ToString('o')
  credential_values_read_by_muxia = $false
  prompt_submitted = $false
  output_extracted = $false
  status = 'READY_FOR_SANITIZED_STATE_CHECK'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $SessionFile -Encoding UTF8
$record | ConvertTo-Json -Depth 5
