param(
  [string]$AppShotHome = $env:APP_SHOT_HOME,
  [string]$Folder = "",
  [int]$DurationSeconds = 600,
  [double]$PollIntervalSeconds = 1,
  [int]$MaxIterations = 0,
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

if ([string]::IsNullOrWhiteSpace($Folder)) {
  $Folder = Join-Path $AppShotHome "obs-output\folder-watch-loop"
}
$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_PROJECT = $ProjectRoot
$env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
$env:APP_SHOT_OBS_OUTPUT = $Folder
$env:V3_LOOP_DURATION_SECONDS = [string]$DurationSeconds
$env:V3_LOOP_POLL_INTERVAL_SECONDS = [string]$PollIntervalSeconds
$env:V3_LOOP_MAX_ITERATIONS = [string]$MaxIterations
$env:V3_LOOP_USE_MOCK_OCR = if ($UseMockOcr) { "1" } else { "0" }
New-Item -ItemType Directory -Force -Path $env:APP_SHOT_OBS_OUTPUT | Out-Null

$samplePath = Join-Path $env:APP_SHOT_OBS_OUTPUT "loop_smoke_start.png"
if (!(Test-Path -LiteralPath $samplePath)) {
  $env:V3_LOOP_SAMPLE_IMAGE = $samplePath
  @'
import os
from PIL import Image, ImageDraw

image = Image.new('RGB', (420, 180), '#ffffff')
draw = ImageDraw.Draw(image)
draw.text((40, 45), 'Start', fill='#174ea6')
draw.text((40, 95), 'Folder Watch Loop Smoke', fill='#172033')
image.save(os.environ['V3_LOOP_SAMPLE_IMAGE'])
'@ | & $Python -
}

Set-Location $ProjectRoot
$pythonLog = Join-Path $env:APP_SHOT_OBS_OUTPUT "folder_watch_loop_python.stderr.log"
$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
$result = @'
import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_loop
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

store = V3RunStore()
ocr_provider = MockOcrProvider() if os.environ.get('V3_LOOP_USE_MOCK_OCR') == '1' else None
runtime = V3Runtime(store=store, ocr_provider=ocr_provider)
run = runtime.create_run(
    V3TaskConfig(
        app_name='folder_watch_loop_smoke',
        app_type='web',
        target_language='en',
        capture_source='folder_watch',
        save_root=os.environ['APP_SHOT_RUNS'],
        enable_ocr=True,
        enable_ui_model=True,
        enable_auto_click=False,
        observe_only=True,
        must_have_text=True,
        max_images=100,
        max_actions=1,
    )
)
runtime.start_run(run.run_id)
max_iterations = int(os.environ['V3_LOOP_MAX_ITERATIONS'])
stats = run_folder_watch_loop(
    runtime,
    run.run_id,
    os.environ['APP_SHOT_OBS_OUTPUT'],
    duration_seconds=float(os.environ['V3_LOOP_DURATION_SECONDS']),
    poll_interval_seconds=float(os.environ['V3_LOOP_POLL_INTERVAL_SECONDS']),
    max_iterations=max_iterations if max_iterations > 0 else None,
)
summary = runtime.summary(run.run_id)
summary_path = Path(os.environ['APP_SHOT_RUNS']) / 'v3' / run.run_id / 'summary.json'
folder_summary_path = Path(os.environ['APP_SHOT_RUNS']) / 'v3' / run.run_id / 'meta' / 'folder_watch_summary.json'
payload = {
    'run_id': run.run_id,
    'observe_only': summary.observe_only,
    'auto_click_ready': summary.auto_click_ready,
    'stats': stats,
    'counts': summary.counts,
    'summary_path': str(summary_path),
    'folder_watch_summary.json': str(folder_summary_path),
}
print(json.dumps(payload, ensure_ascii=False))
if summary.auto_click_ready:
    raise SystemExit('folder watch loop smoke unexpectedly enabled auto click')
if stats['iterations'] <= 0:
    raise SystemExit('folder watch loop smoke did not run any iterations')
'@ | & $Python - 2> $pythonLog
  $pythonExitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $oldErrorActionPreference
}

if ($pythonExitCode -ne 0) {
  $logTail = if (Test-Path -LiteralPath $pythonLog) { (Get-Content -LiteralPath $pythonLog -Tail 20) -join "`n" } else { "" }
  throw "folder watch loop smoke failed`n$logTail"
}

$result | ConvertFrom-Json | ConvertTo-Json -Depth 8
