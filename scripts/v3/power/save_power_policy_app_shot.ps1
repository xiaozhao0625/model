param(
  [string]$OutputPath = "D:\work\app-shot\logs\power_policy_before_capture.json"
)

$ErrorActionPreference = "Stop"
$AppShotRoot = "D:\work\app-shot"
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null

function Get-ActiveScheme {
  $text = powercfg /getactivescheme
  $guid = if ($text -match "([0-9a-fA-F-]{36})") { $Matches[1] } else { "SCHEME_CURRENT" }
  [ordered]@{ guid = $guid; raw = $text }
}

function Get-PowerSetting {
  param(
    [string]$SubGroup,
    [string]$Setting
  )
  $warnings = @()
  $raw = ""
  try {
    $raw = (powercfg /query SCHEME_CURRENT $SubGroup $Setting) -join "`n"
    $indexes = Get-CurrentPowerIndexes -Raw $raw
    $ac = $indexes.ac_seconds
    $dc = $indexes.dc_seconds
    return [ordered]@{
      subgroup = $SubGroup
      setting = $Setting
      ac_seconds = $ac
      dc_seconds = $dc
      raw = $raw
      warnings = $warnings
    }
  } catch {
    $warnings += $_.Exception.Message
    return [ordered]@{
      subgroup = $SubGroup
      setting = $Setting
      ac_seconds = $null
      dc_seconds = $null
      raw = $raw
      warnings = $warnings
    }
  }
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

$policy = [ordered]@{
  app_shot_root = $AppShotRoot
  captured_at = (Get-Date).ToUniversalTime().ToString("o")
  active_scheme = Get-ActiveScheme
  settings = [ordered]@{
    monitor_timeout = Get-PowerSetting -SubGroup "SUB_VIDEO" -Setting "VIDEOIDLE"
    sleep_timeout = Get-PowerSetting -SubGroup "SUB_SLEEP" -Setting "STANDBYIDLE"
    hibernate_timeout = Get-PowerSetting -SubGroup "SUB_SLEEP" -Setting "HIBERNATEIDLE"
    lock_display_idle = Get-PowerSetting -SubGroup "SUB_VIDEO" -Setting "VIDEOCONLOCK"
  }
}

$policy | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output ($policy | ConvertTo-Json -Depth 8)
