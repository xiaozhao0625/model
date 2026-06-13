param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..\..").Path,
  [string]$TopologyFile = "configs/deploy/p13_software_requirements.example.json",
  [string]$OutputDir = "runs/p13_overall",
  [string]$MasterUrl = "http://192.168.1.18:8000",
  [switch]$SkipNetwork,
  [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$argsList = @(
  "scripts/deploy/p13/p13_m0_overall_check.py",
  "--project-root", $ProjectRoot,
  "--topology-file", $TopologyFile,
  "--output-dir", $OutputDir,
  "--master-url", $MasterUrl
)

if ($SkipNetwork) {
  $argsList += "--skip-network"
}
if ($SkipSmoke) {
  $argsList += "--skip-smoke"
}

python @argsList
Write-Host "P13 overall report directory: $OutputDir"
