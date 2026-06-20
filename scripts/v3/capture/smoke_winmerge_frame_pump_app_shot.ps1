param(
  [string]$AppShotHome = "D:\work\app-shot",
  [int]$DurationSeconds = 300,
  [int]$MinFrames = 150
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$StartPump = Join-Path $ProjectRoot "scripts\v3\capture\start_winmerge_frame_pump_app_shot.ps1"
$StopPump = Join-Path $ProjectRoot "scripts\v3\capture\stop_winmerge_frame_pump_app_shot.ps1"
$OutputDir = Join-Path $AppShotHome "obs-output"
$Heartbeat = Join-Path $AppShotHome "logs\frame_pump_heartbeat.json"
$TestFileDir = Join-Path $AppShotHome "test-files\winmerge"
$LeftPath = Join-Path $TestFileDir "left.txt"
$RightPath = Join-Path $TestFileDir "right.txt"
$WinMergeCandidates = @(
  (Join-Path $AppShotHome "tools\winmerge\WinMergeU.exe"),
  (Join-Path $AppShotHome "tools\winmerge\WinMerge.exe")
)
$WinMergeExe = $WinMergeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $WinMergeExe) {
  throw "WinMerge executable not found under D:\work\app-shot\tools\winmerge"
}

$WinMergeProcess = $null
try {
  New-Item -ItemType Directory -Force -Path $TestFileDir | Out-Null
  @(
    "V3 WinMerge English comparison sample",
    "The left frame pump smoke file is safe.",
    "Line 3 is identical.",
    "Line 4 is left only."
  ) | Set-Content -LiteralPath $LeftPath -Encoding UTF8
  @(
    "V3 WinMerge English comparison sample",
    "The right frame pump smoke file is safe.",
    "Line 3 is identical.",
    "Line 4 is right only."
  ) | Set-Content -LiteralPath $RightPath -Encoding UTF8
  New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
  $before = @(Get-ChildItem -LiteralPath $OutputDir -Filter "winmerge_frame_*.png" -ErrorAction SilentlyContinue).Count
  $WinMergeProcess = Start-Process -FilePath $WinMergeExe -ArgumentList @($LeftPath, $RightPath) -PassThru
  Start-Sleep -Seconds 2
  & powershell -NoProfile -ExecutionPolicy Bypass -File $StartPump -DurationSeconds $DurationSeconds -IntervalSeconds 0.5 | Out-Null
  Start-Sleep -Seconds ([Math]::Max(2, $DurationSeconds + 1))
  & powershell -NoProfile -ExecutionPolicy Bypass -File $StopPump | Out-Null
  $afterFiles = @(Get-ChildItem -LiteralPath $OutputDir -Filter "winmerge_frame_*.png" -ErrorAction SilentlyContinue)
  $after = $afterFiles.Count
  $newFrames = [Math]::Max(0, $after - $before)
  if ($newFrames -lt $MinFrames) {
    throw "WinMerge frame pump smoke expected at least $MinFrames frames, got $newFrames"
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
  if ($WinMergeProcess -and -not $WinMergeProcess.HasExited) {
    Stop-Process -Id $WinMergeProcess.Id -Force -ErrorAction SilentlyContinue
  }
}

