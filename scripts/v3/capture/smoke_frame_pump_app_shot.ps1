param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$OutputDir = "",
  [int]$DurationSeconds = 120,
  [int]$MinFrames = 60,
  [double]$IntervalSeconds = 1.0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = Join-Path $AppShotHome "obs-output"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$before = @{}
Get-ChildItem -LiteralPath $OutputDir -Filter "frame_*.png" -ErrorAction SilentlyContinue | ForEach-Object {
  $before[$_.FullName] = $true
}

$startScript = Join-Path $ProjectRoot "scripts\v3\capture\start_notepadplusplus_frame_pump_app_shot.ps1"
$stopScript = Join-Path $ProjectRoot "scripts\v3\capture\stop_notepadplusplus_frame_pump_app_shot.ps1"
$startResult = & $startScript -AppShotHome $AppShotHome -OutputDir $OutputDir -DurationSeconds $DurationSeconds -IntervalSeconds $IntervalSeconds | ConvertFrom-Json

try {
  Start-Sleep -Seconds ([Math]::Max(1, $DurationSeconds + 2))
} finally {
  & $stopScript -AppShotHome $AppShotHome | Out-Null
}

$after = Get-ChildItem -LiteralPath $OutputDir -Filter "frame_*.png" -ErrorAction SilentlyContinue |
  Where-Object { -not $before.ContainsKey($_.FullName) } |
  Sort-Object LastWriteTime

$payload = [pscustomobject]@{
  output_dir = $OutputDir
  duration_seconds = $DurationSeconds
  min_frames = $MinFrames
  frames = $after.Count
  first_frame = if ($after.Count) { $after[0].FullName } else { $null }
  last_frame = if ($after.Count) { $after[-1].FullName } else { $null }
  start = $startResult
}
$payload | ConvertTo-Json -Depth 6

if ($after.Count -lt $MinFrames) {
  throw "frame pump produced $($after.Count) frames, expected at least $MinFrames"
}
