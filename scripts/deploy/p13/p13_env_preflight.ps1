param(
  [ValidateSet("M0", "W1", "W2", "W3")]
  [string]$Role,
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..\..").Path,
  [string]$OutputDir = "runs/p13_preflight",
  [string]$TopologyFile = "configs/deploy/p13_software_requirements.example.json",
  [string]$MasterUrl = "http://192.168.1.18:8000",
  [switch]$UploadReport
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$argsList = @(
  "scripts/deploy/p13/p13_env_preflight.py",
  "--role", $Role,
  "--project-root", $ProjectRoot,
  "--output-dir", $OutputDir,
  "--topology-file", $TopologyFile,
  "--master-url", $MasterUrl
)

if ($UploadReport) {
  $argsList += "--upload-report"
}

python @argsList
Write-Host "P13 preflight report directory: $OutputDir\$Role"
