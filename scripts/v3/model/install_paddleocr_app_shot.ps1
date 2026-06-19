param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$IndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple"
)

$ErrorActionPreference = "Stop"
$env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
$env:PADDLE_PDX_MODEL_SOURCE = "modelscope"
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"
$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:PADDLE_HOME | Out-Null
New-Item -ItemType Directory -Force -Path $env:PADDLE_PDX_CACHE_HOME | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppShotHome "models\paddleocr") | Out-Null

$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

& $Python -m pip install --upgrade pip -i $IndexUrl
& $Python -m pip install paddlepaddle paddleocr -i $IndexUrl
& $Python -c "import paddle; import paddleocr; print('paddle', paddle.__version__); print('paddleocr ok')"
