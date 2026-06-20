param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$PidFile = Join-Path $AppShotHome "cache\frame-pump\sumatrapdf_frame_pump.pid"
if (!(Test-Path -LiteralPath $PidFile)) {
  [pscustomobject]@{ stopped = $false; reason = "pid_file_missing"; pid_file = $PidFile } | ConvertTo-Json
  exit 0
}

$PidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($PidText)) {
  Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
  [pscustomobject]@{ stopped = $false; reason = "pid_file_empty"; pid_file = $PidFile } | ConvertTo-Json
  exit 0
}

$Process = Get-Process -Id ([int]$PidText) -ErrorAction SilentlyContinue
if ($Process) {
  Stop-Process -Id $Process.Id -Force
  Start-Sleep -Milliseconds 300
}
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue

[pscustomobject]@{
  stopped = [bool]$Process
  pid = [int]$PidText
  pid_file = $PidFile
} | ConvertTo-Json
