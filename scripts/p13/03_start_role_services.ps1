param(
    [Parameter(Mandatory = $true)][ValidateSet('M0','W1','W2','W3')][string]$Role
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
. "$PSScriptRoot\lib\Write-DeployLog.ps1"

$outDir = Join-Path $RepoRoot "logs/p13/$Role"
$logPath = Join-Path $outDir 'service_start.log'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Write-DeployLog -LogPath $logPath -Role $Role -Action 'start_services' -Message 'Starting role services.'

$steps = @()
function Add-StepResult($Name, $Status, $Message, $NextAction) {
    $script:steps += [pscustomobject]@{ name = $Name; status = $Status; message = $Message; next_action = $NextAction }
}

if ($Role -eq 'M0') {
    Add-StepResult 'postgresql' 'check_only' 'PostgreSQL is verified by inventory/health checks; credentials are not read or logged.' 'Start the PostgreSQL Windows service manually if unavailable.'
    Add-StepResult 'redis' 'check_only' 'Redis is preferred; fallback is documented when unavailable.' 'Install/start Redis or document fallback.'
    $masterBat = Join-Path $RepoRoot 'scripts/deploy/p13/start_m0_master_api.bat'
    $webBat = Join-Path $RepoRoot 'scripts/deploy/p13/start_m0_web_console.bat'
    Add-StepResult 'master_api' $(if (Test-Path $masterBat) { 'start_script_available' } else { 'missing_start_script' }) $masterBat 'Run the start script from an operator shell when ready.'
    Add-StepResult 'web_console' $(if (Test-Path $webBat) { 'start_script_available' } else { 'missing_start_script' }) $webBat 'Run the start script from an operator shell when ready.'
    Add-StepResult 'model_gateway' 'boundary_only' 'P13.3 does not download models or prove model runtime production readiness.' 'Use later model-runtime acceptance steps.'
} else {
    $map = @{ W1='start_w1_pc_game_worker.bat'; W2='start_w2_pc_app_web_worker.bat'; W3='start_w3_android_worker.bat' }
    $workerBat = Join-Path $RepoRoot "scripts/deploy/p13/$($map[$Role])"
    Add-StepResult 'worker_runtime' $(if (Test-Path $workerBat) { 'start_script_available' } else { 'missing_start_script' }) $workerBat 'Run the worker start script after env bootstrap.'
    Add-StepResult 'master_api_target' 'configured' 'Workers must point to M0 Master API and must not connect to PostgreSQL.' 'Set MASTER_API_URL only; do not set DATABASE_URL on workers.'
}

$payload = [ordered]@{ role = $Role; status = 'completed_with_operator_actions'; steps = $steps }
Save-SafeJson -InputObject $payload -Path (Join-Path $outDir 'service_start_result.json')
Set-Content -LiteralPath (Join-Path $outDir 'service_start_summary.md') -Encoding UTF8 -Value @(
    "# P13.3 service start summary - $Role",
    '',
    "- Result: $($payload.status)",
    "- Steps: $($steps.Count)",
    "- Sensitive env values were not logged."
)
Write-DeployLog -LogPath $logPath -Role $Role -Action 'start_services' -Message 'Service start orchestration completed.' -Data $payload
$payload | ConvertTo-SafeJson
