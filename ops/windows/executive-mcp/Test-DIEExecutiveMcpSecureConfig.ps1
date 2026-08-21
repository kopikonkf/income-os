[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secure-config.preflight.v1"
$RepoRoot = "C:\DIE"
$OpsPath = Join-Path $RepoRoot "ops\windows\executive-mcp"
$PlanScript = Join-Path $OpsPath "New-DIEExecutiveMcpSecureConfigPlan.ps1"
$Line1Wrapper = Join-Path $OpsPath "Invoke-DIEExecutiveLine1Tunnel.ps1"
$Line2Wrapper = Join-Path $OpsPath "Invoke-DIEExecutiveLine2Tunnel.ps1"
$FixedRoot = "C:\ProgramData\DIE\ExecutiveMCP"

function Invoke-PlanJson {
    param([Parameter(Mandatory = $true)][string]$ScriptPath)

    $rawLines = & $ScriptPath -Mode Plan
    $planSucceeded = $?
    $raw = ($rawLines | Out-String).Trim()
    if (-not $planSucceeded) {
        throw "Plan execution failed for $ScriptPath"
    }
    return $raw | ConvertFrom-Json
}

foreach ($script in @($PlanScript, $Line1Wrapper, $Line2Wrapper)) {
    if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
        throw "Required B1 script is missing: $script"
    }
}

$plan = Invoke-PlanJson -ScriptPath $PlanScript
$line1 = Invoke-PlanJson -ScriptPath $Line1Wrapper
$line2 = Invoke-PlanJson -ScriptPath $Line2Wrapper
$line1Contract = @($plan.lanes | Where-Object { $_.lane -eq "line1" })
$line2Contract = @($plan.lanes | Where-Object { $_.lane -eq "line2" })
$line1Source = Get-Content -LiteralPath $Line1Wrapper -Raw
$line2Source = Get-Content -LiteralPath $Line2Wrapper -Raw
$combinedSource = $line1Source + [Environment]::NewLine + $line2Source

$forbiddenOrchestration = "(?im)\b(New-Service|Start-Service|Register-ScheduledTask|New-ScheduledTask|schtasks(?:\.exe)?|Start-Process)\b"
$environmentEnumeration = "(?im)(Get-ChildItem\s+Env:|GetEnvironmentVariables|GetEnvironmentVariable\s*\()"
$tunnelIdentityPattern = "(?i)\\btunnel_[0-9a-f]{16,}\\b"

$checks = [ordered]@{
    secure_config_schema_matches = $plan.schema_version -eq "die.executive.mcp.secure-config.v1"
    plan_mode_is_plan = $plan.mode -eq "Plan"
    fixed_install_root = $plan.install_root -eq $FixedRoot
    exactly_two_lanes = @($plan.lanes).Count -eq 2
    line1_contract_unique = $line1Contract.Count -eq 1
    line2_contract_unique = $line2Contract.Count -eq 1
    line1_file_reference_fixed = (
        $line1Contract.Count -eq 1 -and
        $line1Contract[0].control_plane_api_key_ref -eq
            "file:C:\ProgramData\DIE\ExecutiveMCP\secrets\line1\control-plane-api-key"
    )
    line2_file_reference_fixed = (
        $line2Contract.Count -eq 1 -and
        $line2Contract[0].control_plane_api_key_ref -eq
            "file:C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\control-plane-api-key"
    )
    line1_hmac_prohibited = (
        $line1Contract.Count -eq 1 -and
        $line1Contract[0].hmac.required -eq $false -and
        $line1Contract[0].hmac.injection -eq "prohibited"
    )
    line2_hmac_process_scoped = (
        $line2Contract.Count -eq 1 -and
        $line2Contract[0].hmac.required -eq $true -and
        $line2Contract[0].hmac.injection -eq "process-scoped" -and
        $line2Contract[0].hmac.cleared_on_exit -eq $true
    )
    acl_inheritance_disabled = $plan.acl_contract.inheritance_disabled -eq $true
    broad_acl_principals_forbidden = @($plan.acl_contract.broad_principals_forbidden).Count -eq 3
    secure_config_write_free = $plan.safety.writes_performed -eq $false
    secure_config_secret_free = $plan.safety.credentials_requested_or_read -eq $false
    secure_config_identity_free = $plan.safety.tunnel_identity_requested_or_read -eq $false
    profiles_not_initialized = $plan.safety.tunnel_profiles_initialized -eq $false
    tunnel_doctor_not_invoked = $plan.safety.tunnel_client_doctor_invoked -eq $false
    tunnel_run_not_invoked = $plan.safety.tunnel_client_run_invoked -eq $false
    line1_wrapper_plan_only_executed = (
        $line1.mode -eq "Plan" -and
        $line1.files_read -eq $false -and
        $line1.tunnel_client_run_invoked -eq $false
    )
    line2_wrapper_plan_only_executed = (
        $line2.mode -eq "Plan" -and
        $line2.files_read -eq $false -and
        $line2.tunnel_client_run_invoked -eq $false
    )
    line1_never_reads_hmac_files = $line1Source -notmatch "ReadAllText|snapshot-hmac-key"
    line1_clears_inherited_hmac = (
        $line1Source -match 'SetEnvironmentVariable\("DIE_SNAPSHOT_HMAC_KEY", \$null, "Process"\)' -and
        $line1Source -match 'SetEnvironmentVariable\("DIE_SNAPSHOT_HMAC_KEY_ID", \$null, "Process"\)'
    )
    line2_reads_only_fixed_protected_files = (
        $line2Source -match "\[System\.IO\.File\]::ReadAllText" -and
        $line2Source -match '\$SnapshotHmacKeyFile = Join-Path \$SecretsPath "snapshot-hmac-key"' -and
        $line2Source -match '\$SnapshotHmacKeyIdFile = Join-Path \$SecretsPath "snapshot-hmac-key-id"'
    )
    line2_clears_hmac_in_finally = (
        $line2Source -match '(?s)finally\s*\{.*DIE_SNAPSHOT_HMAC_KEY.*\$null.*DIE_SNAPSHOT_HMAC_KEY_ID.*\$null'
    )
    no_environment_enumeration = $combinedSource -notmatch $environmentEnumeration
    no_service_or_task_or_detached_process = $combinedSource -notmatch $forbiddenOrchestration
    no_embedded_tunnel_identity = $combinedSource -notmatch $tunnelIdentityPattern
    no_remote_admin_ui = $combinedSource -notmatch "--allow-remote-ui|--open-web-ui"
    no_raw_http_logging = $combinedSource -notmatch "--log.http-raw-unsafe"
}

$failedChecks = @(
    $checks.GetEnumerator() |
        Where-Object { -not [bool]$_.Value } |
        ForEach-Object { $_.Key }
)
$ready = $failedChecks.Count -eq 0

[ordered]@{
    schema_version = $SchemaVersion
    mode = "DryRun"
    ready = $ready
    checks = $checks
    failed_checks = $failedChecks
    evidence = [ordered]@{
        plan_schema = $plan.schema_version
        line1_schema = $line1.schema_version
        line2_schema = $line2.schema_version
        fixed_root = $FixedRoot
        programdata_accessed = $false
        secret_values_returned = $false
    }
    safety = [ordered]@{
        writes_performed = $false
        credentials_requested_or_read = $false
        tunnel_identity_requested_or_read = $false
        tunnel_profiles_initialized = $false
        tunnel_created_or_modified = $false
        tunnel_client_doctor_invoked = $false
        tunnel_client_run_invoked = $false
        mcp_services_started = $false
        windows_service_or_task_created = $false
        external_registration_performed = $false
    }
} | ConvertTo-Json -Depth 8

if (-not $ready) {
    exit 1
}
