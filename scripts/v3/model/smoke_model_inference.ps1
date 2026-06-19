param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod -Uri "$BaseUrl/api/v3/model/health" -TimeoutSec 10
$classify = Invoke-RestMethod -Uri "$BaseUrl/api/v3/model/classify-scene" -Method Post -ContentType "application/json" -Body (@{ screenshot_path = "mock.png"; task_context = @{ app_type = "software" } } | ConvertTo-Json -Depth 5) -TimeoutSec 10
[pscustomobject]@{
  health_ok = $health.ok
  classify_ok = $classify.ok
  online_inference = $false
  model_action_control = $false
} | ConvertTo-Json -Depth 5
