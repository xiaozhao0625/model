param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$Target = Join-Path $AppShotHome "models\showui\ShowUI-2B"
$Cache = Join-Path $AppShotHome "cache\huggingface"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
New-Item -ItemType Directory -Force -Path $Cache | Out-Null

Write-Output "ShowUI download is manual-gated for this lightweight setup pass."
Write-Output "Source: https://huggingface.co/showlab/ShowUI-2B"
Write-Output "Expected directory: $Target"
Write-Output "Cache directory: $Cache"
Write-Output "This script does not download automatically. Review license, revision, file list, size, and sha256 before downloading."
exit 2
