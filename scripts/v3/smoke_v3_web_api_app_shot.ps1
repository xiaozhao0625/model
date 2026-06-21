param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$ReportsRoot = Join-Path $AppShotHome "reports"
New-Item -ItemType Directory -Force -Path $ReportsRoot | Out-Null

$Endpoints = @(
  "/api/v3/health",
  "/api/v3/action/health",
  "/api/v3/model/health",
  "/api/v3/runs",
  "/api/v3/config/defaults"
)

$Results = @()
foreach ($endpoint in $Endpoints) {
  $url = "$BaseUrl$endpoint"
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    $Results += [pscustomobject]@{
      endpoint = $endpoint
      ok = $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
      status_code = $response.StatusCode
      optional = $false
      error = $null
    }
  } catch {
    $Results += [pscustomobject]@{
      endpoint = $endpoint
      ok = $false
      status_code = $null
      optional = $false
      error = $_.Exception.Message
    }
  }
}

$RunDetailEndpoints = @()
try {
  $runsEnvelope = Invoke-RestMethod -Uri "$BaseUrl/api/v3/runs" -TimeoutSec 10
  $runs = @($runsEnvelope.data)
  if ($runs.Count -gt 0 -and $runs[0].run_id) {
    $runId = $runs[0].run_id
    $RunDetailEndpoints = @(
      "/api/v3/runs/$runId/summary",
      "/api/v3/runs/$runId/actions"
    )
  }
} catch {
  $Results += [pscustomobject]@{
    endpoint = "/api/v3/runs:<parse_run_detail_targets>"
    ok = $false
    status_code = $null
    optional = $false
    error = $_.Exception.Message
  }
}

foreach ($endpoint in $RunDetailEndpoints) {
  $url = "$BaseUrl$endpoint"
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    $Results += [pscustomobject]@{
      endpoint = $endpoint
      ok = $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
      status_code = $response.StatusCode
      optional = $false
      error = $null
    }
  } catch {
    $Results += [pscustomobject]@{
      endpoint = $endpoint
      ok = $false
      status_code = $null
      optional = $false
      error = $_.Exception.Message
    }
  }
}

$Report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  base_url = $BaseUrl
  endpoints = $Results
  ok = -not (@($Results | Where-Object { -not $_.ok }).Count)
  api_client_scanned = "apps/web-console/src/lib/api-client.ts"
}

$JsonPath = Join-Path $ReportsRoot "v3_web_api_smoke_report.json"
$MdPath = Join-Path $ReportsRoot "v3_web_api_smoke_report.md"
$Report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $JsonPath -Encoding UTF8

$md = @(
  "# V3 Web API Smoke",
  "",
  "- Base URL: $BaseUrl",
  "- Overall: $($Report.ok)",
  "",
  "| Endpoint | OK | Status | Error |",
  "| --- | --- | ---: | --- |"
)
foreach ($item in $Results) {
  $md += "| $($item.endpoint) | $($item.ok) | $($item.status_code) | $($item.error) |"
}
$md | Set-Content -LiteralPath $MdPath -Encoding UTF8

Write-Output ($Report | ConvertTo-Json -Depth 8)
if (-not $Report.ok) {
  exit 1
}
