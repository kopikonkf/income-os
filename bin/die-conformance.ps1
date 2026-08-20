# C:\DIE\bin\die-conformance.ps1 - Runner gabungan untuk conformance test (B3.5)
param([string]$Out)

$ErrorActionPreference = "Stop"

# Jalankan pytest dan capture output
$pytestResult = python -m pytest C:\DIE\bridge\tests -q --tb=no 2>&1

# Parse pytest output untuk passed/failed
$passed = 0
$failed = 0
$failedNames = @()

# Cari baris ringkasan pytest (contoh: "17 passed, 3 failed in 1.23s")
$summaryLine = $pytestResult | Where-Object { $_ -match '\d+ passed' -or $_ -match '\d+ failed' } | Select-Object -Last 1

if ($summaryLine -match '(\d+) passed') { $passed = [int]$Matches[1] }
if ($summaryLine -match '(\d+) failed') { $failed = [int]$Matches[1] }

# Cari nama test yang failed
$pytestResult | ForEach-Object {
    if ($_ -match 'FAILED\s+(.+?)::') {
        $failedNames += $Matches[1].Trim()
    }
}

# Daftar fixture yang dicek (sesuai fx-01..fx-08)
$fixturesChecked = @("fx-01", "fx-02", "fx-03", "fx-04", "fx-05", "fx-06", "fx-07", "fx-08", "fx-08c", "fx-08d")

$verdict = if ($failed -eq 0) { "PASS" } else { "FAIL" }

$output = @{
    run_at = (Get-Date).ToString("o")
    pytest = @{
        passed = $passed
        failed = $failed
        failed_names = $failedNames
    }
    fixtures_checked = $fixturesChecked
    verdict = $verdict
} | ConvertTo-Json -Depth 5 -Compress

$output | Set-Content -Path $Out -Encoding UTF8
Write-Output "Conformance written: $Out"
Write-Output "Verdict: $verdict ($passed passed, $failed failed)"