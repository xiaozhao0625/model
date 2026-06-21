param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$LegacyScript = Join-Path $ProjectRoot "scripts\v3\start_v3_backend_app_shot.ps1"
if (-not (Test-Path -LiteralPath $LegacyScript)) {
  throw "backend start script not found: $LegacyScript"
}

Write-Host "Redis is not required for V3 single-node mode."
Write-Host "PostgreSQL is not required for V3 single-node mode."
Write-Host "Docker is not required for V3 single-node mode."
& powershell -NoProfile -ExecutionPolicy Bypass -File $LegacyScript -AppShotHome $AppShotHome -HostName $HostName -Port $Port
