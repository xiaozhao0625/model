param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
$env:PADDLE_PDX_MODEL_SOURCE = "modelscope"
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"
$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
New-Item -ItemType Directory -Force -Path (Join-Path $AppShotHome "test-images") | Out-Null
New-Item -ItemType Directory -Force -Path $env:PADDLE_PDX_CACHE_HOME | Out-Null

$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

& $Python -c "import paddle; import paddleocr; print('paddle', paddle.__version__); print('paddleocr ok')"
& $Python -c "from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider; h=PaddleOcrProvider().health(); print(h.model_dump_json())"
