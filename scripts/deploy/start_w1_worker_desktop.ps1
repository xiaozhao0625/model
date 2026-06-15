param(
  [string]$MasterUrl = "http://192.168.1.18:8000",
  [string]$WorkerId = "worker_pc_game_w1",
  [string]$RepoRoot = "D:\work\model",
  [string]$PythonPath = "D:\work\venvs\ai-screenshot-worker\Scripts\python.exe",
  [int]$TargetTotal = 20,
  [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"

function Write-JsonAndExit {
  param(
    [hashtable]$Payload,
    [int]$Code = 0
  )
  $Payload | ConvertTo-Json -Depth 8
  exit $Code
}

function Get-SessionInfo {
  $quserOutput = $null
  try { $quserOutput = (& quser 2>$null) -join "`n" } catch { $quserOutput = $null }
  [ordered]@{
    computer_name = $env:COMPUTERNAME
    user_name = $env:USERNAME
    user_interactive = [Environment]::UserInteractive
    session = $quserOutput
  }
}

function Invoke-W1DesktopPreflight {
  Add-Type -AssemblyName System.Drawing
  Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class P14W1Desktop {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

  $logDir = "D:\work\logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $safeText = Join-Path $logDir "p14_w1_desktop_preflight.txt"
  $capturePath = Join-Path $logDir "p14_w1_desktop_preflight.png"
  Set-Content -LiteralPath $safeText -Encoding UTF8 -Value @(
    "P14.4 W1 safe desktop preflight",
    "No account, no game, no real user page, no secrets."
  )

  $process = Start-Process -FilePath "notepad.exe" -ArgumentList @($safeText) -PassThru
  try {
    $handle = [IntPtr]::Zero
    for ($i = 0; $i -lt 60; $i++) {
      $process.Refresh()
      if ($process.MainWindowHandle -ne [IntPtr]::Zero) {
        $handle = $process.MainWindowHandle
        break
      }
      Start-Sleep -Milliseconds 250
    }
    if ($handle -eq [IntPtr]::Zero) {
      return [ordered]@{
        status = "desktop_session_required"
        can_enumerate_windows = $false
        can_get_window_handle = $false
        reason = "notepad_window_handle_not_available"
      }
    }

    [void][P14W1Desktop]::MoveWindow($handle, 80, 80, 960, 640, $true)
    [void][P14W1Desktop]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 500

    $rect = New-Object P14W1Desktop+RECT
    $client = New-Object P14W1Desktop+RECT
    [void][P14W1Desktop]::GetWindowRect($handle, [ref]$rect)
    [void][P14W1Desktop]::GetClientRect($handle, [ref]$client)
    $width = [Math]::Max(1, $rect.Right - $rect.Left)
    $height = [Math]::Max(1, $rect.Bottom - $rect.Top)
    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size $width, $height))
    $bitmap.Save($capturePath, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()

    return [ordered]@{
      status = "passed"
      can_enumerate_windows = $true
      can_get_window_handle = $true
      can_get_client_rect = $true
      can_capture_safe_window = (Test-Path -LiteralPath $capturePath)
      capture_path = $capturePath
      window_rect = @{ left = $rect.Left; top = $rect.Top; right = $rect.Right; bottom = $rect.Bottom }
      client_rect = @{ left = 0; top = 0; right = $client.Right; bottom = $client.Bottom }
    }
  } finally {
    if ($process -and !$process.HasExited) {
      $process.CloseMainWindow() | Out-Null
      Start-Sleep -Milliseconds 300
      if (!$process.HasExited) { $process.Kill() }
    }
  }
}

$session = Get-SessionInfo
if (!$session.user_interactive) {
  Write-JsonAndExit -Code 2 -Payload ([ordered]@{
    status = "desktop_session_required"
    session = $session
    started_worker = $false
    sensitive_information_printed = $false
  })
}

$preflight = Invoke-W1DesktopPreflight
if ($preflight.status -ne "passed") {
  Write-JsonAndExit -Code 2 -Payload ([ordered]@{
    status = "desktop_session_required"
    session = $session
    preflight = $preflight
    started_worker = $false
    sensitive_information_printed = $false
  })
}

if ($PreflightOnly) {
  Write-JsonAndExit -Payload ([ordered]@{
    status = "preflight_passed"
    session = $session
    preflight = $preflight
    started_worker = $false
    sensitive_information_printed = $false
  })
}

if (!(Test-Path -LiteralPath $PythonPath)) {
  throw "worker python not found: $PythonPath"
}
if (!(Test-Path -LiteralPath $RepoRoot)) {
  throw "repo root not found: $RepoRoot"
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONIOENCODING = "utf-8"
& $PythonPath "scripts\p14\p14_minimal_worker_task.py" `
  --worker-id $WorkerId `
  --master-url $MasterUrl `
  --output-root "D:\work\runs" `
  --target-total $TargetTotal

Write-JsonAndExit -Payload ([ordered]@{
  status = "worker_invocation_finished"
  session = $session
  preflight = $preflight
  started_worker = $true
  worker_exit_code = $LASTEXITCODE
  sensitive_information_printed = $false
})
