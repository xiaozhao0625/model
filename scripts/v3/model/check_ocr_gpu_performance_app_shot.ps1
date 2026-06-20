param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$VenvName = "v3-gpu",
  [double]$MaxFrameSeconds = 5.0,
  [double]$PreferredFrameSeconds = 3.0,
  [switch]$MeasureEvenIfCpu
)

$ErrorActionPreference = "Stop"
$RepoRoot = Join-Path $AppShotHome "model"
$Python = Join-Path $AppShotHome "venvs\$VenvName\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  $Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
}
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found under D:\work\app-shot\venvs"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
$env:PYTHONPATH = Join-Path $RepoRoot "src"
$env:PIP_CACHE_DIR = Join-Path $AppShotHome "cache\pip"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
$env:APP_SHOT_OCR_PERFORMANCE_REPORT = Join-Path $AppShotHome "cache\ocr_gpu_performance.json"
$env:APP_SHOT_MAX_FRAME_SECONDS = [string]$MaxFrameSeconds
$env:APP_SHOT_PREFERRED_FRAME_SECONDS = [string]$PreferredFrameSeconds
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $env:APP_SHOT_OCR_PERFORMANCE_REPORT) | Out-Null

$MeasureCpuValue = if ($MeasureEvenIfCpu) { "1" } else { "0" }
$env:APP_SHOT_MEASURE_CPU_OCR = $MeasureCpuValue

@'
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

def safe_call(fn, default=None):
    try:
        return fn()
    except Exception as exc:
        return {"error": repr(exc)}

def nvidia_info():
    if not shutil.which("nvidia-smi"):
        return {"available": False, "reason": "nvidia-smi_not_found"}
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        text=True,
        timeout=10,
    ).strip()
    return {"available": True, "query": output}

def torch_info():
    import torch
    return {
        "version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda": getattr(torch.version, "cuda", None),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }

def paddle_info():
    import paddle
    return {
        "version": paddle.__version__,
        "is_compiled_with_cuda": bool(paddle.is_compiled_with_cuda()),
        "device": paddle.get_device(),
    }

def make_image(path: Path, text: str, size=(1280, 720)):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", size, (245, 247, 250))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.rectangle([30, 30, size[0] - 30, 110], fill=(255, 255, 255), outline=(80, 90, 100))
    draw.text((48, 58), text, fill=(20, 30, 40), font=font)
    draw.text((48, 160), "File Edit View Go To Zoom Favorites Settings Help About", fill=(20, 30, 40), font=font)
    image.save(path)

def measure_ocr(image_path: Path, lang="en"):
    from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider
    provider = PaddleOcrProvider(enabled=True)
    start = time.perf_counter()
    result = provider.recognize_for_language(str(image_path), lang)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return elapsed_ms, result.model_dump()

payload = {
    "gpu": safe_call(nvidia_info, {}),
    "torch": safe_call(torch_info, {}),
    "paddle": safe_call(paddle_info, {}),
    "ocr_provider": "paddleocr",
    "device": None,
    "full_frame_ms": None,
    "roi_ms": None,
    "scaled_ms": None,
    "cache_hit_ms": None,
    "preferred_frame_seconds": float(os.environ.get("APP_SHOT_PREFERRED_FRAME_SECONDS", "3.0")),
}
payload["device"] = payload.get("paddle", {}).get("device") if isinstance(payload.get("paddle"), dict) else None
paddle_cuda = bool(isinstance(payload.get("paddle"), dict) and payload["paddle"].get("is_compiled_with_cuda") is True)
gpu_device = str(payload.get("device") or "").startswith(("gpu", "cuda"))
ocr_gpu_ready = paddle_cuda and gpu_device

can_measure = ocr_gpu_ready or os.environ.get("APP_SHOT_MEASURE_CPU_OCR") == "1"
errors = []
if can_measure:
    try:
        tmp = Path(tempfile.mkdtemp(prefix="app_shot_ocr_perf_"))
        full = tmp / "full.png"
        roi = tmp / "roi.png"
        scaled = tmp / "scaled.png"
        make_image(full, "English OCR performance readiness sample")
        from PIL import Image
        with Image.open(full) as image:
            image.crop((20, 20, 760, 220)).save(roi)
            image.resize((640, 360)).save(scaled)
        cache = {}
        for key, path in [("full_frame_ms", full), ("roi_ms", roi), ("scaled_ms", scaled)]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in cache:
                payload[key] = 0.0
                continue
            elapsed, result = measure_ocr(path)
            cache[digest] = result
            payload[key] = elapsed
        start = time.perf_counter()
        hashlib.sha256(full.read_bytes()).hexdigest() in cache
        payload["cache_hit_ms"] = round((time.perf_counter() - start) * 1000, 2)
    except Exception as exc:
        errors.append(repr(exc))
else:
    errors.append("ocr_measurement_skipped_until_gpu_ready")

timings = [payload[key] for key in ("full_frame_ms", "roi_ms", "scaled_ms") if isinstance(payload.get(key), (int, float))]
max_frame_seconds = float(os.environ.get("APP_SHOT_MAX_FRAME_SECONDS", "5.0"))
ocr_performance_ready = bool(timings) and max(timings) <= max_frame_seconds * 1000
payload["ocr_gpu_ready"] = bool(ocr_gpu_ready)
payload["ocr_performance_ready"] = bool(ocr_performance_ready)
payload["ocr_production_ready"] = bool(ocr_gpu_ready and ocr_performance_ready)
payload["full_auto_capture_ready"] = bool(payload["ocr_production_ready"])
payload["failure_reasons"] = []
if not payload["ocr_gpu_ready"]:
    payload["failure_reasons"].append("ocr_gpu_not_ready")
if not payload["ocr_performance_ready"]:
    payload["failure_reasons"].append("ocr_performance_not_ready")
payload["errors"] = errors

report = Path(os.environ["APP_SHOT_OCR_PERFORMANCE_REPORT"])
report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
'@ | & $Python -
