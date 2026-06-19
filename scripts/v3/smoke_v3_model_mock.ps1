param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [switch]$FallbackToLocal = $true
)

$ErrorActionPreference = "Stop"
$payload = @{
  screenshot_path = "mock_start.png"
  task_context = @{ app_type = "software"; target_language = "en" }
  ocr_boxes = @(@{ text = "Start"; bbox = @(20, 20, 140, 64); confidence = 0.91; language_hint = "en" })
} | ConvertTo-Json -Depth 8
try {
  $ranked = Invoke-RestMethod -Uri "$BaseUrl/api/v3/model/rank-click-candidates" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 10
} catch {
  if (!$FallbackToLocal) {
    throw
  }
  $Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
  if (!(Test-Path -LiteralPath $Python)) {
    throw "Python venv not found: $Python"
  }
  Set-Location (Join-Path $AppShotHome "model")
  $local = @'
import json
from ai_screenshot_platform.v3.model.registry import UiModelRegistry
from ai_screenshot_platform.v3.schemas import ModelRequest, OcrTextBox
result = UiModelRegistry().rank_click_candidates(
    ModelRequest(
        screenshot_path="mock_start.png",
        task_context={"app_type": "software", "target_language": "en"},
        ocr_boxes=[OcrTextBox(text="Start", bbox=[20, 20, 140, 64], confidence=0.91, language_hint="en")],
    )
)
print(json.dumps({"ok": True, "data": result.model_dump()}, ensure_ascii=False))
'@ | & $Python -
  $ranked = $local | ConvertFrom-Json
}
[pscustomobject]@{
  ok = $ranked.ok
  provider = $ranked.data.provider
  candidate_count = @($ranked.data.candidates).Count
  action_control = $false
} | ConvertTo-Json -Depth 5
