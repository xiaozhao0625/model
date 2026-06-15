param(
  [string]$Python = "E:\work\venvs\ai-screenshot-master\Scripts\python.exe",
  [string]$ApiUrl = "http://127.0.0.1:8000",
  [string]$WebUrl = "http://127.0.0.1:5173",
  [string]$RunId = "p14_4_batch3C_w3_safe_ui_03_20260615_190322_run",
  [string]$OutputDir = "deploy_output"
)

$ErrorActionPreference = "Continue"
$results = New-Object System.Collections.Generic.List[object]

function Invoke-GateStep {
  param(
    [string]$Name,
    [scriptblock]$Script
  )
  $sw = [Diagnostics.Stopwatch]::StartNew()
  try {
    $output = & $Script 2>&1
    $exit = if ($LASTEXITCODE -ne $null) { [int]$LASTEXITCODE } else { 0 }
    $sw.Stop()
    $script:results.Add([ordered]@{ name = $Name; status = if ($exit -eq 0) { "passed" } else { "failed" }; exit_code = $exit; latency_ms = [int]$sw.ElapsedMilliseconds; output = (($output | Select-Object -Last 40) -join "`n") })
  } catch {
    $sw.Stop()
    $script:results.Add([ordered]@{ name = $Name; status = "failed"; exit_code = 1; latency_ms = [int]$sw.ElapsedMilliseconds; output = $_.Exception.Message })
  }
  $global:LASTEXITCODE = 0
}

Invoke-GateStep "python_compile" { & $Python -m compileall src tests scripts }
Invoke-GateStep "backend_tests" { & $Python -m pytest tests\unit\test_master_backend_api.py tests\integration\test_postgres_production_readiness_api.py }
Invoke-GateStep "frontend_lint" { cmd /c npm run lint --prefix apps\web-console }
Invoke-GateStep "frontend_build" { cmd /c npm run build --prefix apps\web-console }
Invoke-GateStep "api_smoke" { & $Python scripts\qa\check_api_smoke.py --base-url $ApiUrl --run-id $RunId }
Invoke-GateStep "run_consistency" { & $Python scripts\qa\check_run_consistency.py --base-url $ApiUrl --run-id $RunId }
Invoke-GateStep "artifact_index" { & $Python scripts\qa\check_artifact_index.py --base-url $ApiUrl --run-id $RunId }
Invoke-GateStep "p14_5_flow" { & $Python scripts\qa\check_p14_5_flow.py --base-url $ApiUrl --run-id $RunId }
Invoke-GateStep "frontend_smoke" { powershell -ExecutionPolicy Bypass -File scripts\qa\check_frontend_smoke.ps1 -WebUrl $WebUrl -ApiUrl $ApiUrl -RunId $RunId }

$failed = @($results | Where-Object { $_.status -ne "passed" })
$report = [ordered]@{
  schema_version = "p14.4-ux-artifact-qa-quality-gate"
  generated_at = (Get-Date).ToString("o")
  status = if ($failed.Count -eq 0) { "passed" } else { "failed" }
  api_url = $ApiUrl
  web_url = $WebUrl
  run_id = $RunId
  steps = $results
  safety = [ordered]@{
    online_inference = $false
    model_action_control = $false
    production_scale_capture = $false
    downloaded_model_or_ocr = $false
    sensitive_information_disclosed = $false
    worker_direct_postgresql = $false
  }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$jsonPath = Join-Path $OutputDir "p14_4_ux_artifact_qa_quality_gate_report.json"
$mdPath = Join-Path $OutputDir "p14_4_ux_artifact_qa_quality_gate_report.md"
$report | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $jsonPath
@(
  "# P14.4 UX Artifact QA Quality Gate Report",
  "",
  "- status: $($report.status)",
  "- api_url: $ApiUrl",
  "- web_url: $WebUrl",
  "- run_id: $RunId",
  "",
  "## Steps",
  ($results | ForEach-Object { "- $($_.name): $($_.status) ($($_.latency_ms) ms)" }),
  "",
  "## Safety",
  "- online_inference: no",
  "- model_action_control: no",
  "- production_scale_capture: no",
  "- downloaded_model_or_ocr: no",
  "- sensitive_information_disclosed: no",
  "- worker_direct_postgresql: no"
) | Set-Content -Encoding UTF8 $mdPath

$report | ConvertTo-Json -Depth 10
if ($failed.Count -gt 0) { exit 1 }
