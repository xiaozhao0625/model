param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$Folder = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs\v3"
$env:APP_SHOT_OBS_OUTPUT = if ($Folder) { $Folder } else { Join-Path $AppShotHome "obs-output" }
New-Item -ItemType Directory -Force -Path $env:APP_SHOT_OBS_OUTPUT | Out-Null

$sample = Join-Path $env:APP_SHOT_OBS_OUTPUT "worker_smoke_start.png"
if (!(Test-Path -LiteralPath $sample)) {
  [IO.File]::WriteAllBytes($sample, [byte[]](137,80,78,71,13,10,26,10,1,2,3,4))
}

Set-Location $ProjectRoot
& $Python -c @"
import json
import os
from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_once
from ai_screenshot_platform.v3.ocr.mock_provider import MockOcrProvider
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

runtime = V3Runtime(store=V3RunStore(os.environ['APP_SHOT_RUNS']), ocr_provider=MockOcrProvider())
run = runtime.create_run(
    V3TaskConfig(
        app_name='folder_watch_worker_smoke',
        target_language='en',
        capture_source='folder_watch',
        save_root=os.environ['APP_SHOT_RUNS'],
        must_have_text=True,
    )
)
stats = run_folder_watch_once(runtime, run.run_id, os.environ['APP_SHOT_OBS_OUTPUT'])
summary_path = Path(os.environ['APP_SHOT_RUNS']) / run.run_id / 'meta' / 'folder_watch_summary.json'
print(json.dumps({'run_id': run.run_id, 'stats': stats, 'folder_watch_summary.json': str(summary_path)}, ensure_ascii=False))
"@
if ($LASTEXITCODE -ne 0) {
  throw "folder_watch_worker smoke failed"
}
