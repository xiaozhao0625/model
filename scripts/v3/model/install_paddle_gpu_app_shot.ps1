param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$Python311 = "D:\work\python311\python.exe",
  [string]$PaddleVersion = "3.3.1",
  [string]$CudaWheel = "cu118",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$RepoRoot = Join-Path $AppShotHome "model"
$CpuPython = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
$GpuVenv = Join-Path $AppShotHome "venvs\v3-gpu"
$GpuPython = Join-Path $GpuVenv "Scripts\python.exe"
$FreezePath = Join-Path $AppShotHome "cache\pip\v3-freeze-before-gpu.txt"
$PaddleIndex = "https://www.paddlepaddle.org.cn/packages/stable/$CudaWheel/"
$MirrorIndex = "https://pypi.tuna.tsinghua.edu.cn/simple"

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
$env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
$env:HF_HOME = Join-Path $AppShotHome "cache\huggingface"
$env:TORCH_HOME = Join-Path $AppShotHome "cache\torch"

$plan = [ordered]@{
  status = "planned"
  app_shot_home = $AppShotHome
  repo_root = $RepoRoot
  cpu_venv_python = $CpuPython
  gpu_venv = $GpuVenv
  gpu_venv_python = $GpuPython
  freeze_path = $FreezePath
  package = "paddlepaddle-gpu==$PaddleVersion"
  paddle_index = $PaddleIndex
  mirror_index = $MirrorIndex
  command = "$Python311 -m venv `"$GpuVenv`"; `"$GpuPython`" -m pip install --upgrade pip setuptools wheel -i $MirrorIndex; `"$GpuPython`" -m pip install --upgrade paddlepaddle-gpu==$PaddleVersion -i $PaddleIndex --extra-index-url $MirrorIndex"
  note = "pass -Execute to create D:\work\app-shot\venvs\v3-gpu; D:\work\app-shot\venvs\v3 is only frozen, not modified"
}

if (!$Execute) {
  $plan | ConvertTo-Json -Depth 5
  exit 0
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $FreezePath) | Out-Null
if (Test-Path -LiteralPath $CpuPython) {
  & $CpuPython -m pip freeze | Set-Content -LiteralPath $FreezePath -Encoding UTF8
}

if (!(Test-Path -LiteralPath $GpuPython)) {
  if (!(Test-Path -LiteralPath $Python311)) {
    throw "Python 3.11 not found: $Python311"
  }
  & $Python311 -m venv $GpuVenv
}

& $GpuPython -m pip install --upgrade pip setuptools wheel -i $MirrorIndex
& $GpuPython -m pip install --upgrade "paddlepaddle-gpu==$PaddleVersion" -i $PaddleIndex --extra-index-url $MirrorIndex

$env:PYTHONPATH = Join-Path $RepoRoot "src"
@'
import json
import paddle

result = {
    "paddle_version": paddle.__version__,
    "is_compiled_with_cuda": bool(paddle.is_compiled_with_cuda()),
    "device": paddle.get_device(),
}
if result["is_compiled_with_cuda"]:
    paddle.utils.run_check()
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result["is_compiled_with_cuda"]:
    raise SystemExit(2)
'@ | & $GpuPython -
