param(
  [string]$LogDir = "D:\work\app-shot\logs"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\work\app-shot\model"
$Save = Join-Path $ProjectRoot "scripts\v3\power\save_power_policy_app_shot.ps1"
$Prevent = Join-Path $ProjectRoot "scripts\v3\power\prevent_sleep_for_capture_app_shot.ps1"
$Restore = Join-Path $ProjectRoot "scripts\v3\power\restore_power_policy_app_shot.ps1"
$Before = Join-Path $LogDir "power_policy_before_capture.json"
$Active = Join-Path $LogDir "power_policy_capture_active.json"
$Restored = Join-Path $LogDir "power_policy_restored.json"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$ok = $false
try {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $Save -OutputPath $Before | Out-Null
  & powershell -NoProfile -ExecutionPolicy Bypass -File $Prevent -OutputPath $Active | Out-Null
  $activePolicy = Get-Content -Raw -LiteralPath $Active | ConvertFrom-Json
  foreach ($name in @("monitor_timeout", "sleep_timeout", "hibernate_timeout")) {
    if ($activePolicy.settings.$name.ac_seconds -ne 0 -or $activePolicy.settings.$name.dc_seconds -ne 0) {
      throw "$name was not disabled for capture"
    }
  }
  $ok = $true
} finally {
  if (Test-Path -LiteralPath $Before) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Restore -InputPath $Before -OutputPath $Restored | Out-Null
  }
}

$summary = [ordered]@{
  ok = $ok
  before = $Before
  active = $Active
  restored = $Restored
  restored_exists = (Test-Path -LiteralPath $Restored)
}
Write-Output ($summary | ConvertTo-Json -Depth 4)
