param(
  [string]$AppShotHome = "D:\work\app-shot"
)

$ErrorActionPreference = "Stop"
$ModelDir = Join-Path $AppShotHome "models\showui\ShowUI-2B"
$Exists = Test-Path -LiteralPath $ModelDir
$Enabled = "$env:APP_SHOT_ENABLE_SHOWUI".ToLowerInvariant() -in @("1", "true", "yes", "on")
[pscustomobject]@{
  provider = "showui"
  status = if (!$Exists) { "unavailable" } elseif ($Enabled) { "ready" } else { "degraded" }
  enabled = $Enabled
  model_dir = $ModelDir
  reason = if (!$Exists) { "showui_weights_missing" } elseif ($Enabled) { "enabled" } else { "weights_present_but_disabled" }
  complete_auto_mode_ready = $false
} | ConvertTo-Json -Depth 4
