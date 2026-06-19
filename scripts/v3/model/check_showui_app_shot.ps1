param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$ModelDir = Join-Path $AppShotHome "models\showui\ShowUI-2B"
$Exists = Test-Path -LiteralPath $ModelDir
[pscustomobject]@{
  provider = "showui"
  status = if ($Exists) { "degraded" } else { "unavailable" }
  enabled = $false
  model_dir = $ModelDir
  reason = if ($Exists) { "weights_present_but_disabled" } else { "showui_weights_missing" }
  complete_auto_mode_ready = $false
} | ConvertTo-Json -Depth 4
