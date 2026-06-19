param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$payload = @{
  screenshot_path = "mock_start.png"
  task_context = @{ app_type = "software"; target_language = "en" }
  ocr_boxes = @(@{ text = "Start"; bbox = @(20, 20, 140, 64); confidence = 0.91; language_hint = "en" })
} | ConvertTo-Json -Depth 8
$ranked = Invoke-RestMethod -Uri "$BaseUrl/api/v3/model/rank-click-candidates" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 10
[pscustomobject]@{
  ok = $ranked.ok
  provider = $ranked.data.provider
  candidate_count = @($ranked.data.candidates).Count
  action_control = $false
} | ConvertTo-Json -Depth 5
