[CmdletBinding()]
param(
    [ValidateSet("Plan")]
    [string]$Mode = "Plan"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = "die.executive.mcp.secure-config.v1"
$InstallRoot = "C:\ProgramData\DIE\ExecutiveMCP"
$BinPath = Join-Path $InstallRoot "bin"
$ConfigPath = Join-Path $InstallRoot "config"
$SecretsPath = Join-Path $InstallRoot "secrets"
$LogsPath = Join-Path $InstallRoot "logs"
$RuntimePath = Join-Path $InstallRoot "runtime"
$ClientPath = Join-Path $BinPath "tunnel-client.exe"
$RepoRoot = "C:\DIE"
$OpsPath = Join-Path $RepoRoot "ops\windows\executive-mcp"

function New-LanePlan {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("line1", "line2")][string]$Lane,
        [Parameter(Mandatory = $true)][string]$ProfileName,
        [Parameter(Mandatory = $true)][string]$HealthListenAddress,
        [Parameter(Mandatory = $true)][string]$BootstrapPath,
        [Parameter(Mandatory = $true)][string]$WrapperPath
    )

    $laneConfigPath = Join-Path $ConfigPath $Lane
    $laneSecretsPath = Join-Path $SecretsPath $Lane
    $laneLogsPath = Join-Path $LogsPath $Lane
    $laneRuntimePath = Join-Path $RuntimePath $Lane
    $profileFile = Join-Path $laneConfigPath "$ProfileName.yaml"
    $controlPlaneKeyFile = Join-Path $laneSecretsPath "control-plane-api-key"
    $controlPlaneKeyRef = "file:$controlPlaneKeyFile"

    $requiredSecretFiles = @(
        [ordered]@{
            purpose = "tunnel control-plane authentication"
            path = $controlPlaneKeyFile
            reference = $controlPlaneKeyRef
            consumed_by = "tunnel-client"
        }
    )
    $hmacContract = [ordered]@{
        required = $false
        injection = "prohibited"
        scope = "none"
    }

    if ($Lane -eq "line2") {
        $hmacKeyFile = Join-Path $laneSecretsPath "snapshot-hmac-key"
        $hmacKeyIdFile = Join-Path $laneSecretsPath "snapshot-hmac-key-id"
        $requiredSecretFiles += @(
            [ordered]@{
                purpose = "snapshot HMAC signing"
                path = $hmacKeyFile
                reference = "wrapper-process-only"
                consumed_by = "Line 2 wrapper"
            },
            [ordered]@{
                purpose = "snapshot HMAC key identifier"
                path = $hmacKeyIdFile
                reference = "wrapper-process-only"
                consumed_by = "Line 2 wrapper"
            }
        )
        $hmacContract = [ordered]@{
            required = $true
            injection = "process-scoped"
            scope = "Line 2 tunnel-client and its MCP child only"
            cleared_on_exit = $true
        }
    }

    return [ordered]@{
        lane = $Lane
        profile_name = $ProfileName
        tunnel_identity = "not-collected-in-b1"
        profile_directory = $laneConfigPath
        profile_file = $profileFile
        secrets_directory = $laneSecretsPath
        logs_directory = $laneLogsPath
        runtime_directory = $laneRuntimePath
        tunnel_client = $ClientPath
        bootstrap = $BootstrapPath
        wrapper = $WrapperPath
        control_plane_api_key_ref = $controlPlaneKeyRef
        required_secret_files = $requiredSecretFiles
        hmac = $hmacContract
        health_listen_address = $HealthListenAddress
        log_file = Join-Path $laneLogsPath "tunnel-client.jsonl"
        pid_file = Join-Path $laneRuntimePath "tunnel-client.pid"
        remote_admin_ui_allowed = $false
        raw_http_logging_allowed = $false
    }
}

$line1 = New-LanePlan -Lane "line1" -ProfileName "executive-line1" -HealthListenAddress "127.0.0.1:18101" -BootstrapPath (Join-Path $RepoRoot "bin\die_executive_line1_mcp.py") -WrapperPath (Join-Path $OpsPath "Invoke-DIEExecutiveLine1Tunnel.ps1")
$line2 = New-LanePlan -Lane "line2" -ProfileName "executive-line2" -HealthListenAddress "127.0.0.1:18102" -BootstrapPath (Join-Path $RepoRoot "bin\die_executive_mcp.py") -WrapperPath (Join-Path $OpsPath "Invoke-DIEExecutiveLine2Tunnel.ps1")

$requiredDirectories = @(
    $BinPath,
    $ConfigPath,
    $SecretsPath,
    $LogsPath,
    $RuntimePath,
    $line1.profile_directory,
    $line1.secrets_directory,
    $line1.logs_directory,
    $line1.runtime_directory,
    $line2.profile_directory,
    $line2.secrets_directory,
    $line2.logs_directory,
    $line2.runtime_directory
)

[ordered]@{
    schema_version = $SchemaVersion
    mode = $Mode
    install_root = $InstallRoot
    repository_root = $RepoRoot
    required_directories = $requiredDirectories
    acl_contract = [ordered]@{
        inheritance_disabled = $true
        inherited_rules_allowed = $false
        access_type = "Allow"
        principals = @(
            [ordered]@{ sid = "S-1-5-18"; role = "Local System"; rights = "FullControl" },
            [ordered]@{ sid = "S-1-5-32-544"; role = "Built-in Administrators"; rights = "FullControl" },
            [ordered]@{ sid = "current-operator-at-b2"; role = "Activation operator"; rights = "FullControl" }
        )
        broad_principals_forbidden = @("Everyone", "BUILTIN\Users", "Authenticated Users")
        applies_to = @("directories", "profile files", "secret files", "log files", "PID files")
    }
    lanes = @($line1, $line2)
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
} | ConvertTo-Json -Depth 10
