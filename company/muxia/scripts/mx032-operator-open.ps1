$ErrorActionPreference = 'Stop'

$MuxiaRoot = if ($env:MUXIA_ROOT) { $env:MUXIA_ROOT } else { 'C:\DIE\workspaces\MUXIA-B04\muxia-root' }
$ProfileId = if ($env:MUXIA_PROFILE_ID) { $env:MUXIA_PROFILE_ID } else { 'chatgpt-a' }
$ProfileDir = Join-Path $MuxiaRoot "profiles\$ProfileId\browser"
$StateDir = Join-Path $MuxiaRoot 'state'
$SessionFile = Join-Path $StateDir 'mx032-operator-session.json'
$DevToolsFile = Join-Path $ProfileDir 'DevToolsActivePort'

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
Remove-Item $DevToolsFile -Force -ErrorAction SilentlyContinue

$Chrome = node -e "const {chromium}=require('playwright'); process.stdout.write(chromium.executablePath())"
if (-not (Test-Path $Chrome)) { throw "PLAYWRIGHT_CHROME_NOT_FOUND: $Chrome" }

$args = @(
  "--user-data-dir=$ProfileDir",
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=0',
  '--no-first-run',
  '--no-default-browser-check',
  'https://chatgpt.com/'
)

$proc = Start-Process -FilePath $Chrome -ArgumentList $args -PassThru

$deadline = (Get-Date).AddSeconds(20)
$port = $null
while ((Get-Date) -lt $deadline) {
  if ($proc.HasExited) { throw "CHROME_EXITED_EARLY:$($proc.ExitCode)" }
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

$session = [ordered]@{
  schema = 'die.muxia.operator-session.v1'
  task_id = 'MX-032'
  mode = 'OPERATOR_CONTROLLED_HEADED'
  profile_id = $ProfileId
  profile_dir = $ProfileDir
  browser_pid = $proc.Id
  debug_host = '127.0.0.1'
  debug_port = $port
  provider_url = 'https://chatgpt.com/'
  opened_at = (Get-Date).ToUniversalTime().ToString('o')
  prompt_submitted_by_automation = $false
  output_extracted_by_automation = $false
  credential_values_read_by_muxia = $false
  bypass_attempted = $false
  operator_action_required = $true
  status = 'WAITING_OPERATOR_LOGIN'
}
$session | ConvertTo-Json -Depth 5 | Set-Content -Path $SessionFile -Encoding UTF8
$session | ConvertTo-Json -Depth 5
