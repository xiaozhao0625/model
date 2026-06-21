param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$HostName = "127.0.0.1",
  [int]$BackendPort = 8000,
  [int]$WebPort = 5173
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$BackendScript = Join-Path $ProjectRoot "scripts\v3\start\start_v3_backend_app_shot.ps1"
$WebScript = Join-Path $ProjectRoot "scripts\v3\start\start_v3_web_app_shot.ps1"
if (-not (Test-Path -LiteralPath $BackendScript)) { throw "missing backend script: $BackendScript" }
if (-not (Test-Path -LiteralPath $WebScript)) { throw "missing web script: $WebScript" }

Write-Host "Redis is not required for V3 single-node mode."
Write-Host "Starting V3 backend and web console."
Write-Host "Web URL: http://localhost:5173/v3"

Start-Process powershell -WindowStyle Hidden -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $BackendScript,
  "-AppShotHome", $AppShotHome,
  "-HostName", $HostName,
  "-Port", [string]$BackendPort
) | Out-Null

Start-Sleep -Seconds 3
& powershell -NoProfile -ExecutionPolicy Bypass -File $WebScript -AppShotHome $AppShotHome -HostName $HostName -Port $WebPort
