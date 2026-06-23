param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$PythonHome = "D:\work\python311",
  [string]$NodeHome = "D:\work\nodejs",
  [string]$HostName = "127.0.0.1",
  [int]$BackendPort = 8000,
  [int]$WebPort = 5173,
  [switch]$NoBrowser,
  [switch]$KeepExistingPorts
)

$ErrorActionPreference = "Stop"

function Stop-PortListener {
  param([int]$Port)
  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $processId = [int]$listener.OwningProcess
    if ($processId -le 0) { continue }
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      Write-Host "Stopping existing listener on port ${Port}: PID $processId ($($process.ProcessName))"
      Stop-Process -Id $processId -Force
    } catch {
      Write-Warning "Could not stop PID $processId on port ${Port}: $($_.Exception.Message)"
    }
  }
}

function Wait-HttpReady {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 45
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 700
    }
  }
  return $false
}

$ProjectRoot = Join-Path $AppShotHome "model"
$WebRoot = Join-Path $ProjectRoot "apps\web-console"
$BackendScript = Join-Path $ProjectRoot "scripts\v3\start_v3_backend_app_shot.ps1"
$LogsRoot = Join-Path $AppShotHome "logs"
$ObsOutput = Join-Path $AppShotHome "obs-output"
$NpmCmd = Join-Path $NodeHome "npm.cmd"

if (!(Test-Path -LiteralPath $ProjectRoot)) { throw "Project root not found: $ProjectRoot" }
if (!(Test-Path -LiteralPath $BackendScript)) { throw "Backend start script not found: $BackendScript" }
if (!(Test-Path -LiteralPath (Join-Path $WebRoot "package.json"))) { throw "Frontend package.json not found: $WebRoot" }
if (!(Test-Path -LiteralPath $NpmCmd)) { throw "npm.cmd not found: $NpmCmd" }

New-Item -ItemType Directory -Force -Path $LogsRoot, $ObsOutput, (Join-Path $AppShotHome "cache\npm") | Out-Null

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_PROJECT = $ProjectRoot
$env:APP_SHOT_OBS_OUTPUT = $ObsOutput
$env:npm_config_cache = Join-Path $AppShotHome "cache\npm"
$env:Path = "$NodeHome;$PythonHome;$env:Path"

if (!$KeepExistingPorts) {
  Stop-PortListener -Port $BackendPort
  Stop-PortListener -Port $WebPort
  Start-Sleep -Seconds 1
}

$backendOut = Join-Path $LogsRoot "v3_backend_stdout.log"
$backendErr = Join-Path $LogsRoot "v3_backend_stderr.log"
$frontendOut = Join-Path $LogsRoot "v3_frontend_stdout.log"
$frontendErr = Join-Path $LogsRoot "v3_frontend_stderr.log"

Write-Host "Starting V3 backend on http://$HostName`:$BackendPort"
$backend = Start-Process -FilePath "powershell.exe" -PassThru -WindowStyle Hidden -WorkingDirectory $ProjectRoot -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", $BackendScript,
  "-AppShotHome", $AppShotHome,
  "-HostName", $HostName,
  "-Port", [string]$BackendPort
)

$backendReady = Wait-HttpReady -Url "http://$HostName`:$BackendPort/api/v3/health" -TimeoutSeconds 60
if (!$backendReady) {
  Write-Warning "Backend did not report ready within 60 seconds. Check logs:"
  Write-Warning "  $backendOut"
  Write-Warning "  $backendErr"
} else {
  Write-Host "Backend ready. PID: $($backend.Id)"
}

Write-Host "Starting V3 web console on http://$HostName`:$WebPort/v3"
if (!(Test-Path -LiteralPath (Join-Path $WebRoot "node_modules"))) {
  Write-Host "Frontend node_modules not found. Running npm install once..."
  Push-Location $WebRoot
  try {
    & $NpmCmd install
    if ($LASTEXITCODE -ne 0) {
      throw "npm install failed with exit code $LASTEXITCODE"
    }
  } finally {
    Pop-Location
  }
}

$frontend = Start-Process -FilePath $NpmCmd -PassThru -WindowStyle Hidden -WorkingDirectory $WebRoot -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -ArgumentList @(
  "run", "dev", "--",
  "--host", $HostName,
  "--port", [string]$WebPort,
  "--strictPort"
)

$frontendReady = Wait-HttpReady -Url "http://$HostName`:$WebPort/v3" -TimeoutSeconds 45
if (!$frontendReady) {
  Write-Warning "Frontend did not report ready within 45 seconds. Check logs:"
  Write-Warning "  $frontendOut"
  Write-Warning "  $frontendErr"
} else {
  Write-Host "Frontend ready. PID: $($frontend.Id)"
}

Write-Host ""
Write-Host "V3 OBS-OCR collector is starting/running:"
Write-Host "  Backend:  http://$HostName`:$BackendPort"
Write-Host "  Frontend: http://$HostName`:$WebPort/v3"
Write-Host "  Logs:     $LogsRoot"
Write-Host "  Output:   $ObsOutput"
Write-Host ""
Write-Host "Close services later by stopping listeners on ports $BackendPort and $WebPort, or run this script again to restart them."

if (!$NoBrowser -and $frontendReady) {
  Start-Process "http://$HostName`:$WebPort/v3"
}
