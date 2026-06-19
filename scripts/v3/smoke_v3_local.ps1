param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod -Uri "$BaseUrl/api/v3/health" -TimeoutSec 10
$defaults = Invoke-RestMethod -Uri "$BaseUrl/api/v3/config/defaults" -TimeoutSec 10
$run = Invoke-RestMethod -Uri "$BaseUrl/api/v3/runs" -Method Post -ContentType "application/json" -Body (@{ config = $defaults.data } | ConvertTo-Json -Depth 8) -TimeoutSec 10
$started = Invoke-RestMethod -Uri "$BaseUrl/api/v3/runs/$($run.data.run_id)/start" -Method Post -TimeoutSec 10
$summary = Invoke-RestMethod -Uri "$BaseUrl/api/v3/runs/$($run.data.run_id)/summary" -TimeoutSec 10
[pscustomobject]@{
  health = $health.ok
  run_id = $run.data.run_id
  started_status = $started.data.status
  summary_status = $summary.data.status
  observe_only = $summary.data.observe_only
} | ConvertTo-Json -Depth 6
