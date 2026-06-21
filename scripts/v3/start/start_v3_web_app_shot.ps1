param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$LegacyScript = Join-Path $ProjectRoot "scripts\v3\start_v3_web_app_shot.ps1"
if (-not (Test-Path -LiteralPath $LegacyScript)) {
  throw "web start script not found: $LegacyScript"
}

$PortInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($PortInUse) {
  throw "port_in_use: frontend port $Port is occupied. V3 web console uses fixed port 5173 and will not auto-switch."
}

Write-Host "Redis is not required for V3 single-node mode."
Write-Host "V3 frontend port: 5173"
Write-Host "V3 frontend URL: http://localhost:5173/v3"
& powershell -NoProfile -ExecutionPolicy Bypass -File $LegacyScript -AppShotHome $AppShotHome -HostName $HostName -Port $Port
