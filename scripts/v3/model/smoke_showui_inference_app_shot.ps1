param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$ImagePath = "",
  [string]$Goal = "Find the Start button"
)

$ErrorActionPreference = "Stop"
$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_MODELS = Join-Path $AppShotHome "models"
$env:APP_SHOT_SHOWUI_MODEL_DIR = Join-Path $AppShotHome "models\showui\ShowUI-2B"
$env:APP_SHOT_ENABLE_SHOWUI = "1"
$env:HF_HOME = Join-Path $AppShotHome "cache\huggingface"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $AppShotHome "cache\huggingface"
$env:TRANSFORMERS_CACHE = Join-Path $AppShotHome "cache\huggingface"
$env:TORCH_HOME = Join-Path $AppShotHome "cache\torch"

Set-Location (Join-Path $AppShotHome "model")

@"
import json
from pathlib import Path

from PIL import Image, ImageDraw

from ai_screenshot_platform.v3.model.showui_provider import ShowUiProvider
from ai_screenshot_platform.v3.schemas import ModelRequest

app_home = Path(r"$AppShotHome")
image_path = Path(r"$ImagePath") if r"$ImagePath" else app_home / "test-images" / "showui_smoke.png"
image_path.parent.mkdir(parents=True, exist_ok=True)
if not image_path.exists():
    image = Image.new("RGB", (360, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((120, 70, 240, 120), outline="black", width=2)
    draw.text((158, 88), "Start", fill="black")
    image.save(image_path)

provider = ShowUiProvider(enabled=True)
health = provider.health()
result = provider.rank_click_candidates(
    ModelRequest(
        screenshot_path=str(image_path),
        task_context={"goal": r"$Goal", "observe_only": True},
    )
)
print(json.dumps({
    "health": health.model_dump(),
    "result": result.model_dump(),
    "image_path": str(image_path),
}, ensure_ascii=False, indent=2))
"@ | & $Python -
