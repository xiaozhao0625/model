param(
  [string]$WebUrl = "http://127.0.0.1:5173",
  [string]$ApiUrl = "http://127.0.0.1:8000",
  [string]$RunId = "p14_4_batch3C_w3_safe_ui_03_20260615_190322_run",
  [string]$OutputJson = ""
)

$ErrorActionPreference = "Stop"

function Test-Endpoint {
  param([string]$Name, [string]$Url)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 12
    $sw.Stop()
    [ordered]@{ name = $Name; url = $Url; ok = $true; status = [int]$response.StatusCode; latency_ms = [int]$sw.ElapsedMilliseconds; bytes = $response.Content.Length }
  } catch {
    $sw.Stop()
    [ordered]@{ name = $Name; url = $Url; ok = $false; status = 0; latency_ms = [int]$sw.ElapsedMilliseconds; error = $_.Exception.Message }
  }
}

$checks = @(
  (Test-Endpoint "web_console_root" $WebUrl),
  (Test-Endpoint "runs_page" "$WebUrl/runs?sort=created_at_desc&limit=50"),
  (Test-Endpoint "run_detail_page" "$WebUrl/runs/$RunId"),
  (Test-Endpoint "ocr_status_page" "$WebUrl/ocr-status"),
  (Test-Endpoint "model_gateway_page" "$WebUrl/model-gateway"),
  (Test-Endpoint "workers_page" "$WebUrl/workers"),
  (Test-Endpoint "artifact_api" "$ApiUrl/api/runs/$RunId/artifacts")
)

$result = [ordered]@{
  status = if (($checks | Where-Object { -not $_.ok }).Count -eq 0) { "passed" } else { "failed" }
  web_url = $WebUrl
  api_url = $ApiUrl
  run_id = $RunId
  checks = $checks
}

$json = $result | ConvertTo-Json -Depth 8
if ($OutputJson) {
  New-Item -ItemType Directory -Force -Path (Split-Path $OutputJson) | Out-Null
  $json | Set-Content -Encoding UTF8 $OutputJson
}
$json
if ($result.status -ne "passed") { exit 1 }
