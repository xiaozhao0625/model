param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$VenvName = "v3-gpu"
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
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"

@'
import json
import tempfile
import time
from pathlib import Path

import paddle
from PIL import Image, ImageDraw, ImageFont

from ai_screenshot_platform.v3.ocr.paddle_provider import PaddleOcrProvider

def font_for(name: str):
    from PIL import ImageFont
    candidates = {
        "english": [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"],
        "japanese": [r"C:\Windows\Fonts\meiryo.ttc", r"C:\Windows\Fonts\YuGothM.ttc"],
        "korean": [r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunsl.ttf"],
    }
    for font_path in candidates.get(name, []):
        if Path(font_path).is_file():
            return ImageFont.truetype(font_path, 30)
    return ImageFont.load_default()

def make_image(path: Path, text: str, name: str):
    image = Image.new("RGB", (960, 420), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    font = font_for(name)
    draw.text((40, 50), text, fill=(15, 20, 30), font=font)
    image.save(path)

def run_case(provider, tmp: Path, name: str, text: str, lang: str):
    path = tmp / f"{name}.png"
    make_image(path, text, name)
    start = time.perf_counter()
    result = provider.recognize_for_language(str(path), lang)
    return {
        "case": name,
        "status": result.status,
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
        "texts": [box.text for box in result.text_boxes],
    }

provider = PaddleOcrProvider(enabled=True)
tmp = Path(tempfile.mkdtemp(prefix="app_shot_gpu_ocr_smoke_"))
cases = [
    run_case(provider, tmp, "english", "File View Zoom Settings Help", "en"),
    run_case(provider, tmp, "japanese", "\u30d5\u30a1\u30a4\u30eb \u8868\u793a \u8a2d\u5b9a", "ja"),
    run_case(provider, tmp, "korean", "\ud30c\uc77c \ubcf4\uae30 \uc124\uc815", "ko"),
]
notepadplusplus = {
    "target": "notepadplusplus",
    "window_capture": "not_executed_by_smoke_script",
    "reason": "real window capture is performed by the capture smoke; this smoke validates the OCR runtime",
}
payload = {
    "paddle_version": paddle.__version__,
    "is_compiled_with_cuda": bool(paddle.is_compiled_with_cuda()),
    "device": paddle.get_device(),
    "english": cases[0],
    "japanese": cases[1],
    "korean": cases[2],
    "notepadplusplus": notepadplusplus,
    "ready": bool(paddle.is_compiled_with_cuda()) and str(paddle.get_device()).startswith(("gpu", "cuda")),
}
print(json.dumps(payload, ensure_ascii=True, indent=2))
if not payload["ready"]:
    raise SystemExit(2)
'@ | & $Python -
