param(
  [string]$AppShotHome = $env:APP_SHOT_HOME,
  [string]$BrowserPath = "",
  [switch]$ExecuteRealClick = $false,
  [switch]$UseMockOcr = $false
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
$env:APP_SHOT_OBS_OUTPUT = Join-Path $AppShotHome "obs-output\local-html-controlled-click"
$env:APP_SHOT_ALLOW_REAL_CLICK = if ($ExecuteRealClick) { "1" } else { "0" }
$env:APP_SHOT_CAPTURE_AFTER_CLICK = if ($ExecuteRealClick) { "1" } else { "0" }
$env:V3_CONTROLLED_CLICK_CROP_LEFT = "90"
$env:V3_CONTROLLED_CLICK_CROP_TOP = "165"
$env:V3_CONTROLLED_CLICK_CROP_RIGHT = "1060"
$env:V3_CONTROLLED_CLICK_CROP_BOTTOM = "760"
New-Item -ItemType Directory -Force -Path $env:APP_SHOT_OBS_OUTPUT | Out-Null

$htmlPath = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_controlled_click.html"
$screenshotPath = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_controlled_click_screen.png"
$html = @'
<!doctype html>
<html lang="en" class="notranslate" translate="no">
<head>
  <meta charset="utf-8">
  <meta name="google" content="notranslate">
  <meta http-equiv="Content-Language" content="en">
  <title>V3 Controlled Click</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f8fb; color: #172033; }
    main { width: 860px; margin: 90px auto; }
    h1 { font-size: 34px; margin: 0 0 18px; }
    p { font-size: 20px; margin: 0 0 28px; }
    button { font-size: 28px; padding: 18px 52px; border: 2px solid #174ea6; background: #ffffff; color: #174ea6; }
    #status { margin-top: 28px; font-size: 24px; color: #1f6f43; }
  </style>
</head>
<body>
  <main>
    <h1>Local HTML Controlled Click Target</h1>
    <p>Safe English UI smoke page. One click on Start changes this page.</p>
    <button id="start" onclick="this.textContent='Started'; document.getElementById('status').textContent='Navigation Success'; document.body.dataset.clicked='1';">Start</button>
    <div id="status">Waiting</div>
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
if (!$browser) {
  throw "No supported local browser found for controlled click smoke"
}

$browserProcess = $null
try {
  $htmlUri = (New-Object System.Uri($htmlPath)).AbsoluteUri
  $userDataDir = Join-Path $env:APP_SHOT_OBS_OUTPUT "browser-profile"
  if (Test-Path -LiteralPath $userDataDir) {
    Remove-Item -LiteralPath $userDataDir -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null
  $args = @(
    "--new-window",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-translate",
    "--disable-features=Translate,TranslateUI",
    "--lang=en-US",
    "--window-size=1000,700",
    "--window-position=80,80",
    "--user-data-dir=$userDataDir",
    $htmlUri
  )
  $browserProcess = Start-Process -FilePath $browser -ArgumentList $args -PassThru
  Start-Sleep -Seconds 3

  $env:V3_CONTROLLED_CLICK_SCREENSHOT = $screenshotPath
  @'
import os
from PIL import ImageGrab

box = (
    int(os.environ['V3_CONTROLLED_CLICK_CROP_LEFT']),
    int(os.environ['V3_CONTROLLED_CLICK_CROP_TOP']),
    int(os.environ['V3_CONTROLLED_CLICK_CROP_RIGHT']),
    int(os.environ['V3_CONTROLLED_CLICK_CROP_BOTTOM']),
)
ImageGrab.grab(bbox=box).save(os.environ['V3_CONTROLLED_CLICK_SCREENSHOT'])
'@ | & $Python -

  $env:V3_LOCAL_HTML_USE_MOCK_OCR = if ($UseMockOcr) { "1" } else { "0" }
  $env:V3_LOCAL_HTML_EXECUTE_CLICK = if ($ExecuteRealClick) { "1" } else { "0" }
  Set-Location $ProjectRoot
  $pythonLog = Join-Path $env:APP_SHOT_OBS_OUTPUT "local_html_controlled_click_python.stderr.log"
  $oldErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
  $result = @'
import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.click_executor import ClickExecutor, _windows_left_click
from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_once
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

store = V3RunStore()
ocr_provider = MockOcrProvider() if os.environ.get('V3_LOCAL_HTML_USE_MOCK_OCR') == '1' else None
offset_x = int(os.environ['V3_CONTROLLED_CLICK_CROP_LEFT'])
offset_y = int(os.environ['V3_CONTROLLED_CLICK_CROP_TOP'])

def offset_click(x, y):
    _windows_left_click(int(x) + offset_x, int(y) + offset_y)

runtime = V3Runtime(
    store=store,
    ocr_provider=ocr_provider,
    action_loop=ActionLoop(
        executor=ClickExecutor(
            allow_real_click=os.environ.get('APP_SHOT_ALLOW_REAL_CLICK') == '1',
            click_backend=offset_click,
        )
    ),
)

def capture_after(run_id, action_index, before_image):
    if os.environ.get('APP_SHOT_CAPTURE_AFTER_CLICK') != '1':
        return before_image
    from PIL import ImageGrab
    import time

    time.sleep(0.75)
    path = store.write_artifact(run_id, f'meta/after_{action_index}.png', '')
    path.unlink(missing_ok=True)
    box = (
        int(os.environ['V3_CONTROLLED_CLICK_CROP_LEFT']),
        int(os.environ['V3_CONTROLLED_CLICK_CROP_TOP']),
        int(os.environ['V3_CONTROLLED_CLICK_CROP_RIGHT']),
        int(os.environ['V3_CONTROLLED_CLICK_CROP_BOTTOM']),
    )
    ImageGrab.grab(bbox=box).save(path)
    return str(path)

runtime._capture_after_image = capture_after
run = runtime.create_run(
    V3TaskConfig(
        app_name='local_html_controlled_click',
        app_type='web',
        target_language='en',
        capture_source='folder_watch',
        save_root=os.environ['APP_SHOT_RUNS'],
        enable_ocr=True,
        enable_ui_model=True,
        enable_auto_click=True,
        observe_only=False,
        must_have_text=True,
        max_images=10,
        max_actions=1,
    )
)
runtime.start_run(run.run_id)
stats = run_folder_watch_once(runtime, run.run_id, os.environ['APP_SHOT_OBS_OUTPUT'])
images = runtime.images(run.run_id)
if os.environ.get('V3_LOCAL_HTML_EXECUTE_CLICK') == '1':
    actions = runtime.execute_action(run.run_id)
else:
    actions = runtime.evaluate_action(run.run_id)
summary = runtime.summary(run.run_id)
action = actions[0] if actions else {}
result = action.get('result', {}) if isinstance(action, dict) else {}
payload = {
    'run_id': run.run_id,
    'mode': 'execute' if os.environ.get('V3_LOCAL_HTML_EXECUTE_CLICK') == '1' else 'evaluate',
    'observe_only': summary.observe_only,
    'auto_click_ready': summary.auto_click_ready,
    'stats': stats,
    'counts': summary.counts,
    'latest_bucket': images[-1].bucket if images else None,
    'latest_reject_reason': images[-1].reject_reason if images else None,
    'action_result': result,
    'action_label': action.get('label') if isinstance(action, dict) else None,
    'before_image': action.get('before_image') if isinstance(action, dict) else None,
    'after_image': action.get('after_image') if isinstance(action, dict) else None,
    'summary_path': str(Path(os.environ['APP_SHOT_RUNS']) / 'v3' / run.run_id / 'summary.json'),
}
print(json.dumps(payload, ensure_ascii=False))
if not images:
    raise SystemExit('controlled click smoke did not ingest an image')
if images[-1].bucket != 'accepted':
    raise SystemExit(f"controlled click smoke image was not accepted: {images[-1].bucket}:{images[-1].reject_reason}")
if not actions:
    raise SystemExit('controlled click smoke did not produce an action audit')
if os.environ.get('V3_LOCAL_HTML_EXECUTE_CLICK') == '1':
    if result.get('executed') is not True:
        raise SystemExit(f"controlled click smoke did not execute: {result}")
    if result.get('status') not in {'ui_changed', 'navigation_success'}:
        raise SystemExit(f"controlled click smoke did not detect a UI change: {result}")
else:
    if result.get('status') != 'evaluated':
        raise SystemExit(f"controlled click smoke evaluate mode did not stay evaluation-only: {result}")
'@ | & $Python - 2> $pythonLog
    $pythonExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $oldErrorActionPreference
  }

  if ($pythonExitCode -ne 0) {
    $logTail = if (Test-Path -LiteralPath $pythonLog) { (Get-Content -LiteralPath $pythonLog -Tail 20) -join "`n" } else { "" }
    throw "controlled click smoke failed`n$logTail"
  }

  $payload = $result | ConvertFrom-Json
  $payload | Add-Member -NotePropertyName html_path -NotePropertyValue $htmlPath
  $payload | Add-Member -NotePropertyName screenshot_path -NotePropertyValue $screenshotPath
  $payload | Add-Member -NotePropertyName real_click_armed -NotePropertyValue ([bool]$ExecuteRealClick)
  $payload | ConvertTo-Json -Depth 8
} finally {
  if ($browserProcess -and !$browserProcess.HasExited) {
    Stop-Process -Id $browserProcess.Id -Force -ErrorAction SilentlyContinue
  }
}
