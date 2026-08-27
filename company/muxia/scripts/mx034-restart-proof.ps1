$ErrorActionPreference = 'Stop'

$Edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$MuxiaRoot = if ($env:MUXIA_ROOT) { $env:MUXIA_ROOT } else { 'C:\DIE\workspaces\MUXIA-B04\muxia-root' }
$ProfileId = if ($env:MUXIA_PROFILE_ID) { $env:MUXIA_PROFILE_ID } else { 'chatgpt-a' }
$ProfileDir = Join-Path $MuxiaRoot "profiles\$ProfileId\edge-auth"
$StateDir = Join-Path $MuxiaRoot 'state'
$SessionFile = Join-Path $StateDir 'mx034-restart-session.json'
$DevToolsFile = Join-Path $ProfileDir 'DevToolsActivePort'

if (-not (Test-Path $Edge)) { throw 'EDGE_NOT_FOUND' }
if (-not (Test-Path $ProfileDir)) { throw 'PROFILE_NOT_FOUND' }

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'msedge.exe' -and $_.CommandLine -like "*$ProfileDir*"
}
$oldTop = $existing | Where-Object { $_.CommandLine -like '*--user-data-dir=*' } | Select-Object -First 1
if (-not $oldTop) { throw 'NO_ACTIVE_PROFILE_PROCESS' }
$oldPid = [int]$oldTop.ProcessId

$proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
if ($proc -and $proc.MainWindowHandle -ne 0) {
  $null = $proc.CloseMainWindow()
}
$deadline = (Get-Date).AddSeconds(8)
while ((Get-Date) -lt $deadline) {
  $left = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'msedge.exe' -and $_.CommandLine -like "*$ProfileDir*"
  }
  if (-not $left) { break }
  Start-Sleep -Milliseconds 250
}
$left = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'msedge.exe' -and $_.CommandLine -like "*$ProfileDir*"
}
if ($left) {
  $left | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Milliseconds 750
}
$left = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'msedge.exe' -and $_.CommandLine -like "*$ProfileDir*"
}
if ($left) { throw 'PROFILE_PROCESS_DID_NOT_STOP' }

Remove-Item $DevToolsFile -Force -ErrorAction SilentlyContinue
$args = @(
  "--user-data-dir=$ProfileDir",
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=0',
  '--no-first-run',
  '--no-default-browser-check',
  'https://chatgpt.com/'
)
$newProc = Start-Process -FilePath $Edge -ArgumentList $args -PassThru

$deadline = (Get-Date).AddSeconds(20)
$port = $null
while ((Get-Date) -lt $deadline) {
  if ($newProc.HasExited) { throw "EDGE_EXITED_EARLY:$($newProc.ExitCode)" }
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
  schema = 'die.muxia.mx034.restart-session.v1'
  task_id = 'MX-034'
  profile_id = $ProfileId
  profile_dir = $ProfileDir
  old_browser_pid = $oldPid
  new_browser_pid = $newProc.Id
  process_identity_changed = ($oldPid -ne $newProc.Id)
  browser = 'Microsoft Edge Stable'
  session_id = $newProc.SessionId
  debug_host = '127.0.0.1'
  debug_port = $port
  reopened_at = (Get-Date).ToUniversalTime().ToString('o')
  credential_values_read_by_muxia = $false
  prompt_submitted = $false
  output_extracted = $false
  status = 'READY_FOR_POST_RESTART_STATE_CHECK'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $SessionFile -Encoding UTF8
$record | ConvertTo-Json -Depth 5
