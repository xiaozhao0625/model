param(
  [string]$OutputPath = "D:\work\app-shot\logs\power_policy_capture_active.json"
)

$ErrorActionPreference = "Stop"
$AppShotRoot = "D:\work\app-shot"
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null

$warnings = New-Object System.Collections.Generic.List[string]

function Invoke-PowerChange {
  param(
    [string]$Name,
    [scriptblock]$Command
  )
  try {
    & $Command
    if ($LASTEXITCODE -ne 0) {
      $warnings.Add("$Name failed with exit $LASTEXITCODE")
    }
  } catch {
    $warnings.Add("$Name failed: $($_.Exception.Message)")
  }
}

Invoke-PowerChange "monitor-timeout-ac" { powercfg /change monitor-timeout-ac 0 | Out-Null }
Invoke-PowerChange "monitor-timeout-dc" { powercfg /change monitor-timeout-dc 0 | Out-Null }
Invoke-PowerChange "standby-timeout-ac" { powercfg /change standby-timeout-ac 0 | Out-Null }
Invoke-PowerChange "standby-timeout-dc" { powercfg /change standby-timeout-dc 0 | Out-Null }
Invoke-PowerChange "hibernate-timeout-ac" { powercfg /change hibernate-timeout-ac 0 | Out-Null }
Invoke-PowerChange "hibernate-timeout-dc" { powercfg /change hibernate-timeout-dc 0 | Out-Null }

function Get-SettingAfter {
  param([string]$SubGroup, [string]$Setting)
  $raw = (powercfg /query SCHEME_CURRENT $SubGroup $Setting) -join "`n"
  $indexes = Get-CurrentPowerIndexes -Raw $raw
  $ac = $indexes.ac_seconds
  $dc = $indexes.dc_seconds
  [ordered]@{ subgroup = $SubGroup; setting = $Setting; ac_seconds = $ac; dc_seconds = $dc; raw = $raw }
}

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

$active = [ordered]@{
  app_shot_root = $AppShotRoot
  captured_at = (Get-Date).ToUniversalTime().ToString("o")
  requested = [ordered]@{
    "monitor-timeout-ac" = 0
    "monitor-timeout-dc" = 0
    "standby-timeout-ac" = 0
    "standby-timeout-dc" = 0
    "hibernate-timeout-ac" = 0
    "hibernate-timeout-dc" = 0
  }
  settings = [ordered]@{
    monitor_timeout = Get-SettingAfter -SubGroup "SUB_VIDEO" -Setting "VIDEOIDLE"
    sleep_timeout = Get-SettingAfter -SubGroup "SUB_SLEEP" -Setting "STANDBYIDLE"
    hibernate_timeout = Get-SettingAfter -SubGroup "SUB_SLEEP" -Setting "HIBERNATEIDLE"
    lock_display_idle = Get-SettingAfter -SubGroup "SUB_VIDEO" -Setting "VIDEOCONLOCK"
  }
  warnings = @($warnings)
}

foreach ($name in @("monitor_timeout", "sleep_timeout", "hibernate_timeout")) {
  $setting = $active.settings[$name]
  if ($setting.ac_seconds -ne 0) { $warnings.Add("$name AC did not verify as zero") }
  if ($setting.dc_seconds -ne 0) { $warnings.Add("$name DC did not verify as zero") }
}
$active.warnings = @($warnings)

$active | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output ($active | ConvertTo-Json -Depth 8)
