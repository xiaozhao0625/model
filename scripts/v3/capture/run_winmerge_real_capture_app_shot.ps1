param(
  [string]$AppShotHome = "D:\work\app-shot",
  [int]$MaxSeconds = 900,
  [int]$MinProcessed = 150,
  [int]$TargetAcceptedMin = 50,
  [int]$TargetAcceptedMax = 100,
  [int]$MaxActions = 20,
  [switch]$RestorePowerOnExit = $false
)

$ErrorActionPreference = "Stop"
# capture contract: max_actions=20 target_accepted_min=50 target_accepted_max=100
$ProjectRoot = Join-Path $AppShotHome "model"
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
}

$SavePower = Join-Path $ProjectRoot "scripts\v3\power\save_power_policy_app_shot.ps1"
$PreventPower = Join-Path $ProjectRoot "scripts\v3\power\prevent_sleep_for_capture_app_shot.ps1"
$RestorePower = Join-Path $ProjectRoot "scripts\v3\power\restore_power_policy_app_shot.ps1"
$DiagnoseInput = Join-Path $ProjectRoot "scripts\v3\action\diagnose_input_gateway_app_shot.ps1"
$StartPump = Join-Path $ProjectRoot "scripts\v3\capture\start_winmerge_frame_pump_app_shot.ps1"
$StopPump = Join-Path $ProjectRoot "scripts\v3\capture\stop_winmerge_frame_pump_app_shot.ps1"

$WinMergeCandidates = @(
  (Join-Path $AppShotHome "tools\winmerge\WinMergeU.exe"),
  (Join-Path $AppShotHome "tools\winmerge\WinMerge.exe")
)
$WinMergeExe = $WinMergeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $WinMergeExe) {
  throw "WinMerge executable not found under D:\work\app-shot\tools\winmerge"
}
# Fixture contract:
# D:\work\app-shot\test-files\winmerge\left.txt
# D:\work\app-shot\test-files\winmerge\right.txt
$TestFileDir = Join-Path $AppShotHome "test-files\winmerge"
$LeftPath = Join-Path $TestFileDir "left.txt"
$RightPath = Join-Path $TestFileDir "right.txt"

$GpuPython = Join-Path $AppShotHome "venvs\v3-gpu\Scripts\python.exe"
$CpuPython = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
$Python = if (Test-Path -LiteralPath $GpuPython) { $GpuPython } else { $CpuPython }
if (-not (Test-Path -LiteralPath $Python)) {
  throw "Python venv not found"
}

$env:APP_SHOT_HOME = $AppShotHome
$env:APP_SHOT_PROJECT = $ProjectRoot
$env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
$env:APP_SHOT_OBS_OUTPUT = Join-Path $AppShotHome "obs-output"
$env:APP_SHOT_ENABLE_PADDLEOCR = "1"
$env:APP_SHOT_ENABLE_SHOWUI = "1"
$env:APP_SHOT_ALLOW_REAL_CLICK = "1"
$env:APP_SHOT_CAPTURE_AFTER_CLICK = "1"
$env:APP_SHOT_OCR_PERFORMANCE_REPORT = Join-Path $AppShotHome "cache\ocr_gpu_performance.json"
$env:APP_SHOT_INPUT_GATEWAY_DIAGNOSIS = Join-Path $AppShotHome "logs\input_gateway_diagnosis.json"
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
$env:PADDLE_HOME = Join-Path $AppShotHome "cache\paddle"
$env:PADDLE_PDX_CACHE_HOME = Join-Path $AppShotHome "models\paddleocr\paddlex"
$env:PADDLE_PDX_MODEL_SOURCE = "modelscope"
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"
$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
New-Item -ItemType Directory -Force -Path $env:APP_SHOT_OBS_OUTPUT | Out-Null

$PowerRestored = $false
$PumpStarted = $false
$WinMergeProcess = $null
$MetadataFile = Join-Path $AppShotHome "cache\frame-pump\winmerge_frame_pump_capture.json"
$BeforePowerPolicy = Join-Path $AppShotHome "logs\power_policy_before_capture.json"

try {
  if (-not (Test-Path -LiteralPath $BeforePowerPolicy)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $SavePower | Out-Null
  }
  & powershell -NoProfile -ExecutionPolicy Bypass -File $PreventPower | Out-Null
  & powershell -NoProfile -ExecutionPolicy Bypass -File $DiagnoseInput -TargetProcessName "WinMerge" | Out-Null
  $diagnosis = Get-Content -Raw -LiteralPath $env:APP_SHOT_INPUT_GATEWAY_DIAGNOSIS | ConvertFrom-Json
  if (-not ($diagnosis.input_gateway_ready -and $diagnosis.cursor_read_ready -and $diagnosis.mouse_click_ready -and $diagnosis.interactive_desktop_ready)) {
    throw "input_gateway_not_ready_after_prevent_sleep: $($diagnosis.blockers -join ',')"
  }

  New-Item -ItemType Directory -Force -Path $TestFileDir | Out-Null
  @(
    "V3 WinMerge English comparison sample",
    "The left file keeps this shared introduction.",
    "Line 3 is identical on both sides.",
    "Line 4 exists only in the left comparison file.",
    "Line 5 uses a stable English sentence for OCR.",
    "Line 6 highlights a safe difference for capture.",
    "Line 7 remains unchanged.",
    "Line 8 ends the left sample."
  ) | Set-Content -LiteralPath $LeftPath -Encoding UTF8
  @(
    "V3 WinMerge English comparison sample",
    "The right file keeps this shared introduction.",
    "Line 3 is identical on both sides.",
    "Line 4 exists only in the right comparison file.",
    "Line 5 uses a stable English sentence for OCR.",
    "Line 6 highlights a safe difference for capture.",
    "Line 7 remains unchanged.",
    "Line 8 ends the right sample."
  ) | Set-Content -LiteralPath $RightPath -Encoding UTF8
  # Destructive WinMerge actions remain blocked: Save, Save As, Save Left, Save Right, Save Merged, Delete, Print, external command.
  $WinMergeProcess = Start-Process -FilePath $WinMergeExe -ArgumentList @($LeftPath, $RightPath) -PassThru
  Start-Sleep -Seconds 2

  $positionScript = @'
import ctypes
import re
import sys
import time

pattern = re.compile(r"winmerge|left\.txt|right\.txt", re.I)
user32 = ctypes.windll.user32
SWP_SHOWWINDOW = 0x0040

def title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

found = []
def cb(hwnd, _):
    if user32.IsWindowVisible(hwnd):
        text = title(hwnd)
        if text and pattern.search(text):
            found.append(hwnd)
            return False
    return True

enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb)
deadline = time.time() + 10
while time.time() < deadline and not found:
    user32.EnumWindows(enum_proc, 0)
    if found:
        break
    time.sleep(0.5)
if not found:
    raise SystemExit("winmerge_window_not_found")
hwnd = found[0]
user32.SetWindowPos(hwnd, 0, 0, 0, 1200, 900, SWP_SHOWWINDOW)
user32.SetForegroundWindow(hwnd)
print(hwnd)
'@
  $PositionScriptPath = Join-Path $AppShotHome "logs\winmerge_position_window.py"
  [System.IO.File]::WriteAllText($PositionScriptPath, $positionScript, [System.Text.Encoding]::UTF8)
  & $Python $PositionScriptPath | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to position WinMerge window"
  }

  & powershell -NoProfile -ExecutionPolicy Bypass -File $StartPump -WindowTitlePattern "WinMerge|winmerge|left\.txt|right\.txt" -MetadataFile $MetadataFile -IntervalSeconds 0.5 | Out-Null
  $PumpStarted = $true
  Start-Sleep -Seconds 2

  $driver = @'
import json
import os
import time
from pathlib import Path

from ai_screenshot_platform.v3.action.action_loop import ActionLoop
from ai_screenshot_platform.v3.action.click_executor import ClickExecutor
from ai_screenshot_platform.v3.capture.folder_watch_worker import run_folder_watch_once
from ai_screenshot_platform.v3.runtime import V3Runtime
from ai_screenshot_platform.v3.schemas import V3TaskConfig
from ai_screenshot_platform.v3.storage.run_store import V3RunStore

watch_dir = Path(os.environ["APP_SHOT_OBS_OUTPUT"])
metadata_file = Path(os.environ["WINMERGE_METADATA_FILE"])
start_pump_script = Path(os.environ["WINMERGE_START_PUMP_SCRIPT"])
stop_pump_script = Path(os.environ["WINMERGE_STOP_PUMP_SCRIPT"])
heartbeat_file = Path(os.environ["WINMERGE_HEARTBEAT_FILE"])
max_seconds = int(os.environ["WINMERGE_MAX_SECONDS"])
min_processed = int(os.environ["WINMERGE_MIN_PROCESSED"])
target_accepted_min = int(os.environ["WINMERGE_TARGET_ACCEPTED_MIN"])
target_accepted_max = int(os.environ["WINMERGE_TARGET_ACCEPTED_MAX"])
max_actions = int(os.environ["WINMERGE_MAX_ACTIONS"])

runtime = V3Runtime(
    store=V3RunStore(Path(os.environ["APP_SHOT_RUNS"]) / "v3"),
    action_loop=ActionLoop(
        executor=ClickExecutor(
            allow_real_click=True,
            target_client_rect=(0, 28, 1200, 900),
        )
    ),
)
run = runtime.create_run(
    V3TaskConfig(
        app_name="winmerge_real_auto_explore_sample",
        app_type="pc_app",
        target_language="en",
        capture_source="folder_watch",
        save_root=str(Path(os.environ["APP_SHOT_RUNS"]) / "v3"),
        enable_ocr=True,
        enable_ui_model=True,
        enable_auto_click=True,
        observe_only=False,
        enable_game_explorer=False,
        must_have_text=True,
        safety_mode="strict",
        max_actions=max_actions,
        max_images=500,
    )
)
runtime.start_run(run.run_id)
seen = {str(path.resolve()) for path in watch_dir.glob("*.png")}
started = time.monotonic()
last_action_at = 0.0
last_accept_count = 0
frame_pump_restart_count = 0
action_attempts = 0

def write_capture_hint(capture_reason, action_id=None, ui_state_hint="unknown", frames=1):
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_text(
        json.dumps(
            {
                "capture_reason": capture_reason,
                "action_id": action_id,
                "ui_state_hint": ui_state_hint,
                "remaining_frames": frames,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

def read_heartbeat():
    if not heartbeat_file.is_file():
        return {}
    try:
        return json.loads(heartbeat_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

def frame_pump_is_stale(max_age_seconds=5.0):
    heartbeat = read_heartbeat()
    frame_path = heartbeat.get("frame_path")
    if not frame_path:
        return True
    path = Path(str(frame_path))
    if not path.is_file():
        return True
    return time.time() - path.stat().st_mtime > max_age_seconds

def restart_frame_pump_if_stale():
    global frame_pump_restart_count
    if not frame_pump_is_stale():
        return
    frame_pump_restart_count += 1
    os.system(f'powershell -NoProfile -ExecutionPolicy Bypass -File "{stop_pump_script}" >NUL')
    os.system(
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{start_pump_script}" '
        f'-WindowTitlePattern "WinMerge|winmerge|left\\.txt|right\\.txt" -MetadataFile "{metadata_file}" -IntervalSeconds 0.5 >NUL'
    )
    runtime.store.append_event(
        run.run_id,
        "frame_pump_restarted",
        {"reason": "stale", "frame_pump_restart_count": frame_pump_restart_count},
    )

def ui_state_for_label(label):
    lowered = (label or "").casefold()
    escaped = (label or "").encode("unicode_escape").decode("ascii")
    # winmerge_mojibake_menu_map: Chinese UI labels OCR may arrive through Paddle as escaped unicode.
    localized_states = {
        "\\u6587\\u4ef6": "menu_file",
        "\\u7f16\\u8f91": "menu_edit",
        "\\u89c6\\u56fe": "menu_view",
        "\\u5de5\\u5177": "menu_tools",
        "\\u63d2\\u4ef6": "menu_plugins",
        "\\u7a97\\u53e3": "menu_window",
        "\\u5e2e\\u52a9": "menu_help",
    }
    if escaped in localized_states:
        return localized_states[escaped]
    if "file" in lowered:
        return "menu_file"
    if "view" in lowered:
        return "menu_view"
    if "merge" in lowered:
        return "menu_merge"
    if "navigate" in lowered or "difference" in lowered:
        return "menu_navigate"
    if "tool" in lowered or "option" in lowered or "setting" in lowered:
        return "menu_tools"
    if "go" in lowered or "goto" in lowered:
        return "menu_goto"
    if "zoom" in lowered or "aa" == lowered or "fit" in lowered:
        return "menu_zoom"
    if "find" in lowered or "search" in lowered:
        return "dialog_find"
    if "page" in lowered or "previous" in lowered or "next" in lowered or "prev" in lowered:
        return "menu_goto"
    if "favorite" in lowered:
        return "menu_favorites"
    if "help" in lowered:
        return "menu_help"
    if "about" in lowered:
        return "dialog_about"
    return "main_view"

def distinct_states(summary):
    states = set(summary.accepted_by_ui_state_hint)
    return states - {"unknown"}

while True:
    restart_frame_pump_if_stale()
    stats = run_folder_watch_once(runtime, run.run_id, watch_dir, seen=seen)
    stats["frame_pump_restart_count"] = frame_pump_restart_count
    stats["frame_pump_heartbeat"] = read_heartbeat()
    runtime.store.write_artifact(run.run_id, "meta/folder_watch_summary.json", stats)
    summary = runtime.summary(run.run_id)
    states = distinct_states(summary)
    if (
        summary.processed >= min_processed
        and summary.accepted >= target_accepted_min
        and len(states) >= 4
    ):
        break
    if summary.accepted >= target_accepted_max and summary.processed >= min_processed:
        break
    elapsed = time.monotonic() - started
    if elapsed >= max_seconds:
        break

    action_count = summary.auto_click_count
    if (
        summary.accepted > 0
        and action_attempts < max_actions
        and elapsed - last_action_at >= 3.0
    ):
        action_attempts += 1
        action_id = f"action:{action_attempts}"
        write_capture_hint("before_action", action_id=action_id, ui_state_hint="main_view", frames=1)
        time.sleep(0.7)
        action = runtime.execute_action(run.run_id)[0]
        label = action.get("label") if isinstance(action, dict) else None
        state = ui_state_for_label(label)
        write_capture_hint("after_action", action_id=action_id, ui_state_hint=state, frames=5)
        time.sleep(2.8)
        last_action_at = time.monotonic() - started
    else:
        write_capture_hint("periodic", ui_state_hint="main_view", frames=1)
        time.sleep(0.5)
    last_accept_count = summary.accepted

final_summary = runtime.summary(run.run_id)
actions = runtime.list_actions(run.run_id)
folder_watch_summary = {}
folder_watch_summary_path = Path(os.environ["APP_SHOT_RUNS"]) / "v3" / run.run_id / "meta" / "folder_watch_summary.json"
if folder_watch_summary_path.is_file():
    folder_watch_summary = json.loads(folder_watch_summary_path.read_text(encoding="utf-8"))
folder_watch_summary["frame_pump_restart_count"] = frame_pump_restart_count
folder_watch_summary["frame_pump_heartbeat"] = read_heartbeat()
runtime.store.write_artifact(run.run_id, "meta/folder_watch_summary.json", folder_watch_summary)
final_summary = runtime.summary(run.run_id)
payload = {
    "run_id": run.run_id,
    "processed": final_summary.processed,
    "accepted": final_summary.accepted,
    "rejected": final_summary.rejected,
    "failed": final_summary.failed,
    "quarantined": final_summary.quarantined,
    "actions": final_summary.auto_click_count,
    "accepted_by_ui_state_hint": final_summary.accepted_by_ui_state_hint,
    "accepted_by_capture_reason": final_summary.accepted_by_capture_reason,
    "summary_path": str(Path(os.environ["APP_SHOT_RUNS"]) / "v3" / run.run_id / "summary.json"),
    "actions_path": str(Path(os.environ["APP_SHOT_RUNS"]) / "v3" / run.run_id / "meta" / "actions.jsonl"),
    "folder_watch_summary_path": str(Path(os.environ["APP_SHOT_RUNS"]) / "v3" / run.run_id / "meta" / "folder_watch_summary.json"),
    "frame_pump_restart_count": frame_pump_restart_count,
    "frame_pump_heartbeat": read_heartbeat(),
    "stopped_by": "target" if final_summary.processed >= min_processed and final_summary.accepted >= target_accepted_min and len(distinct_states(final_summary)) >= 4 else "timeout_or_partial",
    "last_actions": actions[-5:],
    "target_accepted_min": target_accepted_min,
    "target_accepted_max": target_accepted_max,
    "max_actions": max_actions,
}
print(json.dumps(payload, ensure_ascii=False))
'@
  $DriverPath = Join-Path $AppShotHome "logs\winmerge_real_capture_driver.py"
  [System.IO.File]::WriteAllText($DriverPath, $driver, [System.Text.Encoding]::UTF8)
  $env:WINMERGE_METADATA_FILE = $MetadataFile
  $env:WINMERGE_START_PUMP_SCRIPT = $StartPump
  $env:WINMERGE_STOP_PUMP_SCRIPT = $StopPump
  $env:WINMERGE_HEARTBEAT_FILE = Join-Path $AppShotHome "logs\frame_pump_heartbeat.json"
  $env:WINMERGE_MAX_SECONDS = [string]$MaxSeconds
  $env:WINMERGE_MIN_PROCESSED = [string]$MinProcessed
  $env:WINMERGE_TARGET_ACCEPTED_MIN = [string]$TargetAcceptedMin
  $env:WINMERGE_TARGET_ACCEPTED_MAX = [string]$TargetAcceptedMax
  $env:WINMERGE_MAX_ACTIONS = [string]$MaxActions
  Set-Location $ProjectRoot
  & $Python $DriverPath
  if ($LASTEXITCODE -ne 0) {
    throw "WinMerge capture driver failed"
  }
} finally {
  if ($PumpStarted) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $StopPump | Out-Null
  }
  if ($RestorePowerOnExit) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $RestorePower | Out-Null
    $PowerRestored = $true
  }
  if ($WinMergeProcess -and -not $WinMergeProcess.HasExited) {
    Stop-Process -Id $WinMergeProcess.Id -Force -ErrorAction SilentlyContinue
  }
  [pscustomobject]@{
    power_restored = $PowerRestored
    restored_policy = "D:\work\app-shot\logs\power_policy_restored.json"
  } | ConvertTo-Json
}

