param(
  [string]$InputPath = "D:\work\app-shot\logs\power_policy_before_capture.json",
  [string]$OutputPath = "D:\work\app-shot\logs\power_policy_restored.json"
)

$ErrorActionPreference = "Stop"
$AppShotRoot = "D:\work\app-shot"
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null

if (-not (Test-Path -LiteralPath $InputPath)) {
  throw "Original power policy file missing: $InputPath"
}

$before = Get-Content -Raw -LiteralPath $InputPath | ConvertFrom-Json
$warnings = New-Object System.Collections.Generic.List[string]

function Get-CurrentPowerIndexes {
  param([string]$Raw)
  $matches = [regex]::Matches($Raw, "0x([0-9a-fA-F]+)")
  if ($matches.Count -lt 2) {
    return [ordered]@{ ac_seconds = $null; dc_seconds = $null }
  }
  $acHex = $matches[$matches.Count - 2].Groups[1].Value
  $dcHex = $matches[$matches.Count - 1].Groups[1].Value
  return [ordered]@{
    ac_seconds = [Convert]::ToInt32($acHex, 16)
    dc_seconds = [Convert]::ToInt32($dcHex, 16)
  }
}

function Restore-Setting {
  param(
    [string]$Name,
    [string]$SubGroup,
    [string]$Setting,
    [object]$Saved
  )
  if ($null -eq $Saved) {
    $warnings.Add("$Name saved value missing")
    return
  }
  $acSeconds = Resolve-SavedSeconds -Saved $Saved -Mode "ac"
  $dcSeconds = Resolve-SavedSeconds -Saved $Saved -Mode "dc"
  if ($null -ne $acSeconds) {
    powercfg /setacvalueindex SCHEME_CURRENT $SubGroup $Setting ([int]$acSeconds) | Out-Null
    if ($LASTEXITCODE -ne 0) { $warnings.Add("$Name AC restore failed with exit $LASTEXITCODE") }
  }
  if ($null -ne $dcSeconds) {
    powercfg /setdcvalueindex SCHEME_CURRENT $SubGroup $Setting ([int]$dcSeconds) | Out-Null
    if ($LASTEXITCODE -ne 0) { $warnings.Add("$Name DC restore failed with exit $LASTEXITCODE") }
  }
}

function Resolve-SavedSeconds {
  param(
    [object]$Saved,
    [ValidateSet("ac", "dc")]
    [string]$Mode
  )
  $property = if ($Mode -eq "ac") { "ac_seconds" } else { "dc_seconds" }
  if ($null -ne $Saved.$property) {
    return [int]$Saved.$property
  }
  $raw = [string]$Saved.raw
  $indexes = Get-CurrentPowerIndexes -Raw $raw
  if ($Mode -eq "ac") {
    return $indexes.ac_seconds
  }
  return $indexes.dc_seconds
}

Restore-Setting -Name "monitor_timeout" -SubGroup "SUB_VIDEO" -Setting "VIDEOIDLE" -Saved $before.settings.monitor_timeout
Restore-Setting -Name "sleep_timeout" -SubGroup "SUB_SLEEP" -Setting "STANDBYIDLE" -Saved $before.settings.sleep_timeout
Restore-Setting -Name "hibernate_timeout" -SubGroup "SUB_SLEEP" -Setting "HIBERNATEIDLE" -Saved $before.settings.hibernate_timeout
if ($null -ne $before.settings.lock_display_idle -and $null -ne $before.settings.lock_display_idle.ac_seconds) {
  Restore-Setting -Name "lock_display_idle" -SubGroup "SUB_VIDEO" -Setting "VIDEOCONLOCK" -Saved $before.settings.lock_display_idle
}
powercfg /S $before.active_scheme.guid | Out-Null

function Get-SettingAfter {
  param([string]$SubGroup, [string]$Setting)
  $raw = (powercfg /query SCHEME_CURRENT $SubGroup $Setting) -join "`n"
  $indexes = Get-CurrentPowerIndexes -Raw $raw
  $ac = $indexes.ac_seconds
  $dc = $indexes.dc_seconds
  [ordered]@{ subgroup = $SubGroup; setting = $Setting; ac_seconds = $ac; dc_seconds = $dc; raw = $raw }
}


$restored = [ordered]@{
  app_shot_root = $AppShotRoot
  restored_at = (Get-Date).ToUniversalTime().ToString("o")
  source_policy = $InputPath
  active_scheme = $before.active_scheme
  settings = [ordered]@{
    monitor_timeout = Get-SettingAfter -SubGroup "SUB_VIDEO" -Setting "VIDEOIDLE"
    sleep_timeout = Get-SettingAfter -SubGroup "SUB_SLEEP" -Setting "STANDBYIDLE"
    hibernate_timeout = Get-SettingAfter -SubGroup "SUB_SLEEP" -Setting "HIBERNATEIDLE"
    lock_display_idle = Get-SettingAfter -SubGroup "SUB_VIDEO" -Setting "VIDEOCONLOCK"
  }
  warnings = @($warnings)
}

$restored | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output ($restored | ConvertTo-Json -Depth 8)
