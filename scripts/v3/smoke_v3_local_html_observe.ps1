param(
  [string]$AppShotHome = $env:APP_SHOT_HOME,
  [string]$BrowserPath = "",
  [switch]$UseMockOcr = $false,
  [switch]$AllowFallbackImage = $true
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($AppShotHome)) {
  $AppShotHome = "D:\work\app-shot"
}

$ProjectRoot = Join-Path $AppShotHome "model"
$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_PROJECT = $ProjectRoot
$env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
$env:APP_SHOT_OBS_OUTPUT = Join-Path $AppShotHome "obs-output\local-html-observe"
New-Item -ItemType Directory -Force -Path $env:APP_SHOT_OBS_OUTPUT | Out-Null

$htmlPath = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_observe.html"
$screenshotPath = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_observe_start.png"
$html = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>V3 Local HTML Observe</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f7f9fc; color: #172033; }
    main { width: 900px; margin: 56px auto; }
    h1 { font-size: 34px; margin: 0 0 18px; }
    p { font-size: 20px; margin: 0 0 28px; }
    button { font-size: 24px; padding: 16px 42px; border: 2px solid #174ea6; background: #ffffff; color: #174ea6; }
    .secondary { margin-left: 18px; color: #35506d; border-color: #8aa0b8; }
  </style>
</head>
<body>
  <main>
    <h1>Local HTML Observe Target</h1>
    <p>Safe English UI smoke page for V3 OCR and candidate observation.</p>
    <button>Start</button>
    <button class="secondary">View Report</button>
  </main>
</body>
</html>
'@
Set-Content -LiteralPath $htmlPath -Value $html -Encoding UTF8

function Resolve-LocalBrowser {
  param([string]$Preferred)
  $candidates = @(
    $Preferred,
    "msedge.exe",
    "chrome.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
  ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

  foreach ($candidate in $candidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }
  return $null
}

$browser = Resolve-LocalBrowser -Preferred $BrowserPath
$capturedWithBrowser = $false
if ($browser) {
  $htmlUri = (New-Object System.Uri($htmlPath)).AbsoluteUri
  $userDataDir = Join-Path $env:APP_SHOT_OBS_OUTPUT "browser-profile"
  New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null
  & $browser --headless --disable-gpu --window-size=1000,700 "--user-data-dir=$userDataDir" "--screenshot=$screenshotPath" $htmlUri *> $null
  $capturedWithBrowser = Test-Path -LiteralPath $screenshotPath
}

if (!$capturedWithBrowser) {
  if (!$AllowFallbackImage) {
    throw "No headless browser screenshot available"
  }
  $env:V3_LOCAL_HTML_FALLBACK_IMAGE = $screenshotPath
  @'
import os
from PIL import Image, ImageDraw

path = os.environ['V3_LOCAL_HTML_FALLBACK_IMAGE']
image = Image.new('RGB', (1000, 700), '#f7f9fc')
draw = ImageDraw.Draw(image)
draw.text((90, 80), 'Local HTML Observe Target', fill='#172033')
draw.text((90, 145), 'Safe English UI smoke page for V3 OCR and candidate observation.', fill='#172033')
draw.rectangle((90, 220, 230, 290), outline='#174ea6', width=3, fill='#ffffff')
draw.text((128, 242), 'Start', fill='#174ea6')
draw.rectangle((260, 220, 450, 290), outline='#8aa0b8', width=3, fill='#ffffff')
draw.text((296, 242), 'View Report', fill='#35506d')
image.save(path)
'@ | & $Python -
}

$env:V3_LOCAL_HTML_USE_MOCK_OCR = if ($UseMockOcr) { "1" } else { "0" }
Set-Location $ProjectRoot
$pythonLog = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_observe_python.stderr.log"
$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
$result = @'
import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_once
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

store = V3RunStore()
ocr_provider = MockOcrProvider() if os.environ.get('V3_LOCAL_HTML_USE_MOCK_OCR') == '1' else None
runtime = V3Runtime(store=store, ocr_provider=ocr_provider)
run = runtime.create_run(
    V3TaskConfig(
        app_name='local_html_observe',
        app_type='web',
        target_language='en',
        capture_source='folder_watch',
        save_root=os.environ['APP_SHOT_RUNS'],
        enable_ocr=True,
        enable_ui_model=True,
        enable_auto_click=False,
        observe_only=True,
        must_have_text=True,
        max_images=10,
        max_actions=1,
    )
)
runtime.start_run(run.run_id)
stats = run_folder_watch_once(runtime, run.run_id, os.environ['APP_SHOT_OBS_OUTPUT'])
images = runtime.images(run.run_id)
candidates = runtime.candidates(run.run_id) if images and images[-1].bucket == 'accepted' else []
summary = runtime.summary(run.run_id)
actions = runtime.list_actions(run.run_id)
payload = {
    'run_id': run.run_id,
    'observe_only': summary.observe_only,
    'auto_click_ready': summary.auto_click_ready,
    'stats': stats,
    'counts': summary.counts,
    'latest_bucket': images[-1].bucket if images else None,
    'latest_reject_reason': images[-1].reject_reason if images else None,
    'candidate_count': len(candidates),
    'actions_count': len(actions),
    'summary_path': str(Path(os.environ['APP_SHOT_RUNS']) / 'v3' / run.run_id / 'summary.json'),
}
print(json.dumps(payload, ensure_ascii=False))
if not images:
    raise SystemExit('local HTML observe smoke did not ingest an image')
if summary.auto_click_ready:
    raise SystemExit('local HTML observe smoke unexpectedly enabled auto click')
if actions:
    raise SystemExit('local HTML observe smoke unexpectedly wrote actions')
'@ | & $Python - 2> $pythonLog
  $pythonExitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $oldErrorActionPreference
}

if ($pythonExitCode -ne 0) {
  $logTail = if (Test-Path -LiteralPath $pythonLog) { (Get-Content -LiteralPath $pythonLog -Tail 20) -join "`n" } else { "" }
  throw "local HTML observe smoke failed`n$logTail"
}

$payload = $result | ConvertFrom-Json
$payload | Add-Member -NotePropertyName html_path -NotePropertyValue $htmlPath
$payload | Add-Member -NotePropertyName screenshot_path -NotePropertyValue $screenshotPath
$payload | Add-Member -NotePropertyName browser_capture -NotePropertyValue $capturedWithBrowser
$payload | ConvertTo-Json -Depth 8
