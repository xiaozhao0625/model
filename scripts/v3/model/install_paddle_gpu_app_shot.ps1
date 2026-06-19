param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$PaddleVersion = "3.3.1",
  [string]$IndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"

$command = @(
  $Python,
  "-m",
  "pip",
  "install",
  "--upgrade",
  "paddlepaddle-gpu==$PaddleVersion",
  "-i",
  $IndexUrl
)

if (!$Execute) {
  [pscustomobject]@{
    status = "planned"
    reason = "pass -Execute to install; Windows GPU Paddle wheels may be unavailable, CPU fallback is allowed"
    command = $command -join " "
    app_shot_home = $AppShotHome
  } | ConvertTo-Json -Depth 4
  exit 0
}

& $Python -m pip install --upgrade "paddlepaddle-gpu==$PaddleVersion" -i $IndexUrl
& (Join-Path $PSScriptRoot "check_paddle_device_app_shot.ps1") -AppShotHome $AppShotHome
