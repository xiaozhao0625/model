param(
  [string]$AppShotHome = "",
  [string]$HostName = "127.0.0.1",
  [int]$BackendPort = 8000,
  [int]$WebPort = 5173
)

$ErrorActionPreference = "Stop"

function Resolve-AppShotHome {
  param([string]$ProvidedRoot = "")
  if (-not [string]::IsNullOrWhiteSpace($ProvidedRoot)) {
    return (Resolve-Path -LiteralPath $ProvidedRoot).Path
  }
  $projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
  return (Split-Path -Parent $projectRoot)
}

function Stop-PortOwner {
  param([int]$Port)
  $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($connection in $connections) {
    $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
    if ($process -and ($process.ProcessName -match "node|npm|python|powershell")) {
      Stop-Process -Id $process.Id -Force
    }
  }
}

function Wait-Port {
  param([int]$Port, [int]$TimeoutSeconds = 30)
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($connection) { return $true }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  return $false
}

$Root = Resolve-AppShotHome -ProvidedRoot $AppShotHome
$ProjectRoot = Join-Path $Root "model"
$ReportsRoot = Join-Path $Root "reports"
$RepairScript = Join-Path $ProjectRoot "scripts\v3\portable\repair_after_move_app_shot.ps1"
$BackendScript = Join-Path $ProjectRoot "scripts\v3\start_v3_backend_app_shot.ps1"
$WebScript = Join-Path $ProjectRoot "scripts\v3\start_v3_web_app_shot.ps1"
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"

if (-not (Test-Path -LiteralPath $RepairScript)) { throw "missing repair script: $RepairScript" }
if (-not (Test-Path -LiteralPath $BackendScript)) { throw "missing backend script: $BackendScript" }
if (-not (Test-Path -LiteralPath $WebScript)) { throw "missing web script: $WebScript" }

if ($env:APP_SHOT_PORTABLE_SKIP_REPAIR -ne "1") {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RepairScript -AppShotHome $Root
}
. $EnvScript

Stop-PortOwner -Port $BackendPort
Stop-PortOwner -Port $WebPort
Start-Sleep -Seconds 1

Start-Process -FilePath powershell.exe -WindowStyle Hidden -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $BackendScript,
  "-AppShotHome", $Root,
  "-HostName", $HostName,
  "-Port", [string]$BackendPort
) | Out-Null

if (-not (Wait-Port -Port $BackendPort -TimeoutSeconds 45)) {
  throw "backend_start_failed: port $BackendPort did not open"
}

Start-Process -FilePath powershell.exe -WindowStyle Hidden -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $WebScript,
  "-AppShotHome", $Root,
  "-HostName", $HostName,
  "-Port", [string]$WebPort
) | Out-Null

if (-not (Wait-Port -Port $WebPort -TimeoutSeconds 45)) {
  throw "web_start_failed: port $WebPort did not open"
}

$url = "http://127.0.0.1:$WebPort/v3"
$report = [pscustomobject]@{
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
  app_shot_home = $Root
  backend_port = $BackendPort
  web_port = $WebPort
  backend_url = "http://127.0.0.1:$BackendPort"
  web_url = $url
  repair_script = $RepairScript
  backend_script = $BackendScript
  web_script = $WebScript
  ok = $true
}
$reportPath = Join-Path $ReportsRoot "v3_portable_start_report.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "V3 backend: http://127.0.0.1:$BackendPort"
Write-Host "V3 web console: $url"
Write-Host "Default V3 web console: http://127.0.0.1:5173/v3"
Write-Host "V3 portable start report: $reportPath"
Start-Process $url | Out-Null
Write-Output ($report | ConvertTo-Json -Depth 6)
