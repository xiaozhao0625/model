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
New-Item -ItemType Directory -Force -Path $env:DATA_ROOT | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:APP_SHOT_RUNS "v3") | Out-Null

$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

Set-Location $ProjectRoot
& $Python -m uvicorn ai_screenshot_platform.master.api.app:create_app --factory --host $HostName --port $Port
