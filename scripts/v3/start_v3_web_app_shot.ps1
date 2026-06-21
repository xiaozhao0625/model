param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
} else {
  $env:APP_SHOT_HOME = $AppShotHome
  $env:npm_config_cache = Join-Path $AppShotHome "cache\npm"
}

$WebRoot = Join-Path $ProjectRoot "apps\web-console"
if (!(Test-Path -LiteralPath (Join-Path $WebRoot "package.json"))) {
  throw "web console package.json not found: $WebRoot"
}

$PortInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($PortInUse) {
  throw "port_in_use: frontend port $Port is occupied. V3 web console uses fixed port 5173 and will not auto-switch."
}
Write-Host "Redis is not required for V3 single-node web console."
Write-Host "V3 web console: http://localhost:$Port/v3"

New-Item -ItemType Directory -Force -Path $env:npm_config_cache | Out-Null
Set-Location $WebRoot
npm config set cache $env:npm_config_cache
npm run dev -- --host $HostName --port $Port --strictPort
