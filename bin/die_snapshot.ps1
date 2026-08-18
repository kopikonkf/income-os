# C:\DIE\bin\die_snapshot.ps1 -- snapshot filesystem untuk penegak fx-04 (CB7b)
param([string]$Out)
Get-ChildItem C:\DIE -Recurse -File -ErrorAction SilentlyContinue |
  ForEach-Object { "$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
  Set-Content $Out
Write-Output "Snapshot written: $Out"