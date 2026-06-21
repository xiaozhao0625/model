param(
  [string]$AppShotHome = "",
  [switch]$NoFail
)

$ErrorActionPreference = "Stop"

function Resolve-AppShotHome {
  param([string]$ProvidedRoot = "")
  if (-not [string]::IsNullOrWhiteSpace($ProvidedRoot)) {
    return (Resolve-Path -LiteralPath $ProvidedRoot).Path
  }
  $projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
  return (Split-Path -Parent $projectRoot)
}

function Test-PythonModule {
  param([string]$Python, [string]$Module)
  if (-not (Test-Path -LiteralPath $Python)) { return $false }
  & $Python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$Module') else 1)" *> $null
  return ($LASTEXITCODE -eq 0)
}

function Add-Check {
  param(
    [System.Collections.ArrayList]$Checks,
    [string]$Name,
    [string]$Path,
    [bool]$Ok,
    [string]$Message = ""
  )
  [void]$Checks.Add([pscustomobject]@{
    name = $Name
    path = $Path
    ok = $Ok
    message = $Message
  })
}

$Root = Resolve-AppShotHome -ProvidedRoot $AppShotHome
$ProjectRoot = Join-Path $Root "model"
$ReportsRoot = Join-Path $Root "reports"
$EnvDir = Join-Path $ProjectRoot "scripts\v3\env"
$EnvScript = Join-Path $EnvDir "app_shot_env.ps1"

$requiredDirs = @(
  "tools",
  "downloads",
  "models",
  "cache",
  "cache\pip",
  "cache\npm",
  "cache\huggingface",
  "cache\torch",
  "cache\paddle",
  "runs",
  "runs\v3",
  "obs-output",
  "logs",
  "venvs",
  "reports"
)
foreach ($dir in $requiredDirs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Root $dir) | Out-Null
}
New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null

@"
`$env:APP_SHOT_HOME = "$Root"
`$env:APP_SHOT_PROJECT = "$ProjectRoot"
`$env:APP_SHOT_TOOLS = "$Root\tools"
`$env:APP_SHOT_MODELS = "$Root\models"
`$env:APP_SHOT_RUNS = "$Root\runs"
`$env:APP_SHOT_DOWNLOADS = "$Root\downloads"
`$env:APP_SHOT_OBS_OUTPUT = "$Root\obs-output"
`$env:PIP_CACHE_DIR = "$Root\cache\pip"
`$env:npm_config_cache = "$Root\cache\npm"
`$env:HF_HOME = "$Root\cache\huggingface"
`$env:HUGGINGFACE_HUB_CACHE = "$Root\cache\huggingface"
`$env:TRANSFORMERS_CACHE = "$Root\cache\huggingface"
`$env:TORCH_HOME = "$Root\cache\torch"
`$env:PADDLE_HOME = "$Root\cache\paddle"
`$env:PADDLE_PDX_CACHE_HOME = "$Root\models\paddleocr\paddlex"
`$env:PADDLE_PDX_MODEL_SOURCE = "modelscope"
`$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"
`$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
`$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
`$env:APP_SHOT_ENABLE_SHOWUI = "1"
`$env:APP_SHOT_OCR_PERFORMANCE_REPORT = "$Root\cache\ocr_gpu_performance.json"
`$env:APP_SHOT_FRAME_PUMP_HEARTBEAT = "$Root\logs\frame_pump_heartbeat.json"
`$env:APP_SHOT_POWER_POLICY_BEFORE = "$Root\logs\power_policy_before_capture.json"
`$env:APP_SHOT_POWER_POLICY_ACTIVE = "$Root\logs\power_policy_capture_active.json"
`$env:APP_SHOT_POWER_POLICY_RESTORED = "$Root\logs\power_policy_restored.json"
"@ | Set-Content -LiteralPath $EnvScript -Encoding UTF8

. $EnvScript

$checks = [System.Collections.ArrayList]::new()
$gpuPython = Join-Path $Root "venvs\v3-gpu\Scripts\python.exe"
$cpuPython = Join-Path $Root "venvs\v3\Scripts\python.exe"
$nodeModules = Join-Path $ProjectRoot "apps\web-console\node_modules"
$packageJson = Join-Path $ProjectRoot "apps\web-console\package.json"

Add-Check $checks "project_root" $ProjectRoot (Test-Path -LiteralPath $ProjectRoot)
Add-Check $checks "web_package" $packageJson (Test-Path -LiteralPath $packageJson)
Add-Check $checks "node_modules" $nodeModules (Test-Path -LiteralPath $nodeModules)
Add-Check $checks "venv_gpu_python" $gpuPython (Test-Path -LiteralPath $gpuPython)
Add-Check $checks "venv_cpu_python" $cpuPython (Test-Path -LiteralPath $cpuPython)
Add-Check $checks "backend_uvicorn_gpu" $gpuPython (Test-PythonModule -Python $gpuPython -Module "uvicorn")
Add-Check $checks "backend_fastapi_gpu" $gpuPython (Test-PythonModule -Python $gpuPython -Module "fastapi")
Add-Check $checks "backend_uvicorn_cpu" $cpuPython (Test-PythonModule -Python $cpuPython -Module "uvicorn")
Add-Check $checks "models" (Join-Path $Root "models") (Test-Path -LiteralPath (Join-Path $Root "models"))
Add-Check $checks "showui_model" (Join-Path $Root "models\showui\ShowUI-2B") (Test-Path -LiteralPath (Join-Path $Root "models\showui\ShowUI-2B"))
Add-Check $checks "paddleocr_models" (Join-Path $Root "models\paddleocr") (Test-Path -LiteralPath (Join-Path $Root "models\paddleocr"))
Add-Check $checks "tools" (Join-Path $Root "tools") (Test-Path -LiteralPath (Join-Path $Root "tools"))
Add-Check $checks "ffmpeg" (Join-Path $Root "tools\ffmpeg\bin\ffmpeg.exe") (Test-Path -LiteralPath (Join-Path $Root "tools\ffmpeg\bin\ffmpeg.exe"))
Add-Check $checks "obs_studio" (Join-Path $Root "tools\obs-studio") (Test-Path -LiteralPath (Join-Path $Root "tools\obs-studio"))
Add-Check $checks "env_script" $EnvScript (Test-Path -LiteralPath $EnvScript)

$failed = @($checks | Where-Object { -not $_.ok })
$report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  app_shot_home = $Root
  project_root = $ProjectRoot
  env_script = $EnvScript
  checks = $checks
  ok = ($failed.Count -eq 0)
  failed = $failed
  next_step = "Run scripts\v3\portable\start_app_shot_v3.ps1, then open http://127.0.0.1:5173/v3"
}

$reportPath = Join-Path $ReportsRoot "v3_portable_repair_report.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "V3 portable repair report: $reportPath"
Write-Host "APP_SHOT_HOME: $Root"
if ($failed.Count -gt 0) {
  Write-Warning "Some dependencies are 缺失或不可用. See report for details."
  $failed | Format-Table -AutoSize | Out-String | Write-Host
  if (-not $NoFail) {
    throw "portable_repair_failed: dependency checks failed"
  }
}

Write-Output ($report | ConvertTo-Json -Depth 8)
