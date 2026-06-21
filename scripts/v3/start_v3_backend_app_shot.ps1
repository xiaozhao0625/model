param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
} else {
  $env:APP_SHOT_HOME = $AppShotHome
  $env:APP_SHOT_PROJECT = $ProjectRoot
  $env:APP_SHOT_TOOLS = Join-Path $AppShotHome "tools"
  $env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
  $env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
  $env:APP_SHOT_DOWNLOADS = Join-Path $AppShotHome "downloads"
  $env:APP_SHOT_OBS_OUTPUT = Join-Path $AppShotHome "obs-output"
  $env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
  $env:npm_config_cache = Join-Path $AppShotHome "cache\npm"
  $env:HF_HOME = Join-Path $AppShotHome "cache\huggingface"
  $env:HUGGINGFACE_HUB_CACHE = Join-Path $AppShotHome "cache\huggingface"
  $env:TRANSFORMERS_CACHE = Join-Path $AppShotHome "cache\huggingface"
  $env:TORCH_HOME = Join-Path $AppShotHome "cache\torch"
  $env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
  $env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
}

$env:DATA_ROOT = Join-Path $env:APP_SHOT_RUNS "master"
$env:DATABASE_URL = "sqlite:///$($env:DATA_ROOT)\master.db"
$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
$env:APP_SHOT_ENABLE_SHOWUI = "1"
$env:APP_SHOT_OCR_PERFORMANCE_REPORT = Join-Path $AppShotHome "cache\ocr_gpu_performance.json"
New-Item -ItemType Directory -Force -Path $env:DATA_ROOT | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:APP_SHOT_RUNS "v3") | Out-Null

$GpuPython = Join-Path $AppShotHome "venvs\v3-gpu\Scripts\python.exe"
$CpuPython = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
$PythonCandidates = @($GpuPython, $CpuPython) | Where-Object { Test-Path -LiteralPath $_ }
$Python = $null
foreach ($candidate in $PythonCandidates) {
  & $candidate -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('uvicorn') else 1)" *> $null
  if ($LASTEXITCODE -eq 0) {
    $Python = $candidate
    break
  }
}
if ([string]::IsNullOrWhiteSpace($Python) -or !(Test-Path -LiteralPath $Python)) {
  throw "Python venv with uvicorn not found. Checked: $($PythonCandidates -join ', ')"
}

Set-Location $ProjectRoot
Write-Host "V3 backend Python: $Python"
Write-Host "Redis/PostgreSQL/Docker are not required for V3 single-node mode."
& $Python -m uvicorn ai_screenshot_platform.master.api.app:create_app --factory --host $HostName --port $Port
