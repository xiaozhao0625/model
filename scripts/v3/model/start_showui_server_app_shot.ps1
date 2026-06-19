param(
  [string]$AppShotHome = "D:\work\app-shot",
  [int]$Port = 8010
)

$ErrorActionPreference = "Stop"
$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
$env:APP_SHOT_SHOWUI_MODEL_DIR = Join-Path $AppShotHome "models\showui\ShowUI-2B"
$env:APP_SHOT_ENABLE_SHOWUI = "1"
$env:HF_HOME = Join-Path $AppShotHome "cache\huggingface"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $AppShotHome "cache\huggingface"
$env:TRANSFORMERS_CACHE = Join-Path $AppShotHome "cache\huggingface"
$env:TORCH_HOME = Join-Path $AppShotHome "cache\torch"

$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

Set-Location (Join-Path $AppShotHome "model")
& $Python -m uvicorn ai_screenshot_platform.v3.model.inference_server:create_v3_model_server --factory --host 127.0.0.1 --port $Port
