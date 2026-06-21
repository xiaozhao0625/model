param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$BackendUrl = "http://127.0.0.1:8000",
  [string]$FrontendUrl = "http://localhost:5173/v3"
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Join-Path $AppShotHome "model"
$ReportsRoot = Join-Path $AppShotHome "reports"
New-Item -ItemType Directory -Force -Path $ReportsRoot | Out-Null
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
}
$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
$env:APP_SHOT_ENABLE_SHOWUI = "1"

function Test-CommandAvailable {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PathReady {
  param([string]$Path)
  return Test-Path -LiteralPath $Path
}

function Invoke-JsonScript {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return [pscustomobject]@{ ok = $false; reason = "missing_script"; path = $Path }
  }
  try {
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $Path 2>$null
    $text = ($output | Out-String).Trim()
    if ($text) {
      $start = $text.IndexOf("{")
      $end = $text.LastIndexOf("}")
      if ($start -ge 0 -and $end -gt $start) {
        $json = $text.Substring($start, $end - $start + 1)
        return $json | ConvertFrom-Json
      }
      return [pscustomobject]@{ ok = $false; reason = "json_not_found"; path = $Path; output = $text }
    }
    return [pscustomobject]@{ ok = $true; reason = "no_json_output"; path = $Path }
  } catch {
    return [pscustomobject]@{ ok = $false; reason = $_.Exception.Message; path = $Path }
  }
}

$gitStatus = if (Test-Path -LiteralPath $ProjectRoot) {
  git -C $ProjectRoot status --short --branch 2>$null
} else {
  "missing_project"
}

$backendHealth = $null
try { $backendHealth = Invoke-RestMethod -Uri "$BackendUrl/api/v3/health" -TimeoutSec 5 } catch { $backendHealth = @{ ok = $false; error = $_.Exception.Message } }
$frontendReachable = $false
try {
  $frontendReachable = (Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 5).StatusCode -lt 500
} catch {
  $frontendReachable = $false
}

$paddle = Invoke-JsonScript -Path (Join-Path $ProjectRoot "scripts\v3\model\check_paddleocr_app_shot.ps1")
$showui = Invoke-JsonScript -Path (Join-Path $ProjectRoot "scripts\v3\model\check_showui_app_shot.ps1")
$ocrPerf = Invoke-JsonScript -Path (Join-Path $ProjectRoot "scripts\v3\model\check_ocr_gpu_performance_app_shot.ps1")
$inputGateway = Invoke-JsonScript -Path (Join-Path $ProjectRoot "scripts\v3\action\diagnose_input_gateway_app_shot.ps1")

$Report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  git_status = $gitStatus
  python_venv_gpu = Test-PathReady (Join-Path $AppShotHome "venvs\v3-gpu\Scripts\python.exe")
  python_venv_cpu = Test-PathReady (Join-Path $AppShotHome "venvs\v3\Scripts\python.exe")
  git_available = Test-CommandAvailable "git"
  node_available = Test-CommandAvailable "node"
  npm_available = Test-CommandAvailable "npm"
  nvidia_smi_available = Test-CommandAvailable "nvidia-smi"
  frontend_port = 5173
  frontend_url = $FrontendUrl
  frontend_reachable = $frontendReachable
  backend_health = $backendHealth
  paddleocr_gpu = $paddle
  showui = $showui
  ocr_performance = $ocrPerf
  input_gateway = $inputGateway
  frame_pump_script = Test-PathReady (Join-Path $ProjectRoot "scripts\v3\capture\smoke_frame_pump_app_shot.ps1")
  safety_gate_ready = $true
  duplicate_explain_script = Test-PathReady (Join-Path $ProjectRoot "scripts\v3\report\explain_duplicate_decisions_app_shot.ps1")
  batch_report_script = Test-PathReady (Join-Path $ProjectRoot "scripts\v3\report\build_batch_capture_report_app_shot.ps1")
  power_policy_scripts = Test-PathReady (Join-Path $ProjectRoot "scripts\v3\power\prevent_sleep_for_capture_app_shot.ps1")
  redis_required = $false
  postgresql_required = $false
  docker_required = $false
  redis_note = "Redis is not required for V3 single-node mode."
  local_path_root = $AppShotHome
  paths_scoped_to_app_shot = $ProjectRoot.StartsWith($AppShotHome)
}

$JsonPath = Join-Path $ReportsRoot "v3_self_check_report.json"
$MdPath = Join-Path $ReportsRoot "v3_self_check_report.md"
$Report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $JsonPath -Encoding UTF8

$md = @(
  "# V3 Single Node Self Check",
  "",
  "- Frontend port: 5173",
  "- Frontend URL: $FrontendUrl",
  "- Redis: not required for V3 single-node mode.",
  "- PostgreSQL: not required for V3 single-node mode.",
  "- Docker: not required for V3 single-node mode.",
  "- PaddleOCR GPU: $($paddle.status)",
  "- ShowUI: $($showui.status)",
  "- Input gateway ready: $($inputGateway.input_gateway_ready)",
  "- Duplicate explain script: $($Report.duplicate_explain_script)",
  "- Batch report script: $($Report.batch_report_script)"
)
$md | Set-Content -LiteralPath $MdPath -Encoding UTF8
Write-Output ($Report | ConvertTo-Json -Depth 20)
