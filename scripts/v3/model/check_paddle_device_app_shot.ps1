param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
$env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"

@'
import json
import shutil
import subprocess

info = {}
try:
    import torch
    info["torch_version"] = torch.__version__
    info["torch_cuda_available"] = torch.cuda.is_available()
    info["torch_cuda"] = torch.version.cuda
    info["torch_device_name"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
except Exception as exc:
    info["torch_error"] = repr(exc)

try:
    import paddle
    info["paddle_version"] = paddle.__version__
    info["paddle_cuda"] = paddle.is_compiled_with_cuda()
    info["paddle_device"] = paddle.get_device()
except Exception as exc:
    info["paddle_error"] = repr(exc)

if shutil.which("nvidia-smi"):
    try:
        info["nvidia_smi"] = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            text=True,
            timeout=10,
        ).strip()
    except Exception as exc:
        info["nvidia_smi_error"] = repr(exc)
else:
    info["nvidia_smi"] = None

print(json.dumps(info, ensure_ascii=False, indent=2))
'@ | & $Python -
