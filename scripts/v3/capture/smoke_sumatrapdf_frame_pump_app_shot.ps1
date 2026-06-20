param(
  [string]$AppShotHome = "D:\work\app-shot",
  [int]$DurationSeconds = 300,
  [int]$MinFrames = 150
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$StartPump = Join-Path $ProjectRoot "scripts\v3\capture\start_sumatrapdf_frame_pump_app_shot.ps1"
$StopPump = Join-Path $ProjectRoot "scripts\v3\capture\stop_sumatrapdf_frame_pump_app_shot.ps1"
$OutputDir = Join-Path $AppShotHome "obs-output"
$Heartbeat = Join-Path $AppShotHome "logs\frame_pump_heartbeat.json"
$PdfPath = Join-Path $AppShotHome "test-docs\sumatra_v3_english_sample.pdf"
$SumatraCandidates = @(
  (Join-Path $AppShotHome "tools\sumatrapdf\SumatraPDF.exe"),
  (Join-Path $AppShotHome "tools\sumatrapdf\SumatraPDF-3.6.1-64.exe")
)
$SumatraExe = $SumatraCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $SumatraExe) {
  throw "SumatraPDF executable not found under D:\work\app-shot\tools\sumatrapdf"
}
if (-not (Test-Path -LiteralPath $PdfPath)) {
  throw "Local English PDF not found: $PdfPath"
}

$SumatraProcess = $null
try {
  New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
  $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "sumatra_frame_*.png" -ErrorAction SilentlyContinue).Count
  $SumatraProcess = Start-Process -FilePath $SumatraExe -ArgumentList @("-reuse-instance", $PdfPath) -PassThru
  Start-Sleep -Seconds 2
  & powershell -NoProfile -ExecutionPolicy Bypass -File $StartPump -DurationSeconds $DurationSeconds -IntervalSeconds 0.5 | Out-Null
  Start-Sleep -Seconds ([Math]::Max(2, $DurationSeconds + 1))
  & powershell -NoProfile -ExecutionPolicy Bypass -File $StopPump | Out-Null
  $afterFiles = @(Get-ChildItem -LiteralPath $OutputDir -Filter "sumatra_frame_*.png" -ErrorAction SilentlyContinue)
  $after = $afterFiles.Count
  $newFrames = [Math]::Max(0, $after - $before)
  if ($newFrames -lt $MinFrames) {
    throw "SumatraPDF frame pump smoke expected at least $MinFrames frames, got $newFrames"
  }
  if (-not (Test-Path -LiteralPath $Heartbeat)) {
    throw "Missing frame pump heartbeat: $Heartbeat"
  }
  $heartbeatPayload = Get-Content -LiteralPath $Heartbeat -Raw | ConvertFrom-Json
  [pscustomobject]@{
    ok = $true
    min_frames = $MinFrames
    frames = $newFrames
    heartbeat = $Heartbeat
    heartbeat_status = $heartbeatPayload.status
  } | ConvertTo-Json
} finally {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $StopPump | Out-Null
  if ($SumatraProcess -and -not $SumatraProcess.HasExited) {
    Stop-Process -Id $SumatraProcess.Id -Force -ErrorAction SilentlyContinue
  }
}
