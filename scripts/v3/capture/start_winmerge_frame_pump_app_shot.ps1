param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$OutputDir = "",
  [string]$WindowTitlePattern = "WinMerge|winmerge|left\.txt|right\.txt",
  [string]$MetadataFile = "",
  [double]$IntervalSeconds = 0.5,
  [int]$DurationSeconds = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Join-Path $AppShotHome "model"
$EnvScript = Join-Path $ProjectRoot "scripts\v3\env\app_shot_env.ps1"
if (Test-Path -LiteralPath $EnvScript) {
  . $EnvScript
} else {
  $env:APP_SHOT_HOME = $AppShotHome
  $env:APP_SHOT_PROJECT = $ProjectRoot
  $env:APP_SHOT_RUNS = Join-Path $AppShotHome "runs"
  $env:APP_SHOT_OBS_OUTPUT = Join-Path $AppShotHome "obs-output"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = $env:APP_SHOT_OBS_OUTPUT
}

$PythonCandidates = @(
  (Join-Path $AppShotHome "venvs\v3-gpu\Scripts\python.exe"),
  (Join-Path $AppShotHome "venvs\v3\Scripts\python.exe")
)
$Python = $PythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $Python) {
  throw "Python venv not found under D:\work\app-shot\venvs"
}

$PumpRoot = Join-Path $AppShotHome "cache\frame-pump"
$PidFile = Join-Path $PumpRoot "winmerge_frame_pump.pid"
$LogFile = Join-Path $PumpRoot "winmerge_frame_pump.log"
$RunnerPath = Join-Path $PumpRoot "winmerge_frame_pump.py"
$HeartbeatFile = Join-Path $AppShotHome "logs\frame_pump_heartbeat.json"
if ([string]::IsNullOrWhiteSpace($MetadataFile)) {
  $MetadataFile = Join-Path $PumpRoot "winmerge_frame_pump_capture.json"
}
New-Item -ItemType Directory -Force -Path $PumpRoot | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $HeartbeatFile) | Out-Null

if (Test-Path -LiteralPath $PidFile) {
  $existingPid = (Get-Content -LiteralPath $PidFile -Raw).Trim()
  if ($existingPid -and (Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue)) {
    throw "WinMerge frame pump is already running: pid $existingPid"
  }
  Remove-Item -LiteralPath $PidFile -Force
}

$runner = @'
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import ImageGrab

user32 = ctypes.windll.user32


def _window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _find_window(pattern: str) -> tuple[int, str] | None:
    regex = re.compile(pattern, re.IGNORECASE)
    found: list[tuple[int, str]] = []

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_text(hwnd)
        if title and regex.search(title):
            found.append((hwnd, title))
            return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(callback)
    user32.EnumWindows(enum_proc, 0)
    return found[0] if found else None


def _window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect failed")
    return rect.left, rect.top, rect.right, rect.bottom


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _write_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _capture_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "capture_reason": "periodic",
        "action_id": None,
        "ui_state_hint": "main_view",
    }
    if not path.is_file():
        return metadata
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return metadata
    if not isinstance(payload, dict):
        return metadata
    metadata["capture_reason"] = str(payload.get("capture_reason") or "periodic")
    action_id = payload.get("action_id")
    metadata["action_id"] = str(action_id) if action_id is not None else None
    metadata["ui_state_hint"] = str(payload.get("ui_state_hint") or "unknown")
    remaining = int(payload.get("remaining_frames") or payload.get("frames") or 1)
    if remaining <= 1:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    else:
        payload["remaining_frames"] = remaining - 1
        _atomic_write_json(path, payload)
    return metadata


def _heartbeat(path: Path, payload: dict[str, object]) -> None:
    _atomic_write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--window-title-pattern", required=True)
    parser.add_argument("--interval-seconds", type=float, default=0.5)
    parser.add_argument("--duration-seconds", type=int, default=0)
    parser.add_argument("--metadata-file", required=True)
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--heartbeat-file", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = Path(args.metadata_file)
    pid_file = Path(args.pid_file)
    log_file = Path(args.log_file)
    heartbeat_file = Path(args.heartbeat_file)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    frame_index = 0
    started = time.monotonic()
    try:
        while True:
            if args.duration_seconds > 0 and time.monotonic() - started >= args.duration_seconds:
                return 0
            match = _find_window(args.window_title_pattern)
            if not match:
                warning = {
                    "status": "warning",
                    "warning": "window_missing",
                    "timestamp": _utc_now(),
                    "frame_index": frame_index,
                }
                _heartbeat(heartbeat_file, warning)
                _write_jsonl(log_file, {"event": "window_missing", "pattern": args.window_title_pattern, **warning})
                time.sleep(args.interval_seconds)
                continue
            hwnd, window_title = match
            if user32.IsIconic(hwnd):
                warning = {
                    "status": "warning",
                    "warning": "window_occluded_or_minimized",
                    "timestamp": _utc_now(),
                    "hwnd": hwnd,
                    "window_title": window_title,
                    "frame_index": frame_index,
                }
                user32.ShowWindow(hwnd, 9)
                _heartbeat(heartbeat_file, warning)
                _write_jsonl(log_file, {"event": "window_occluded_or_minimized", **warning})
                time.sleep(args.interval_seconds)
                continue
            bbox = _window_rect(hwnd)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= 20 or height <= 20:
                warning = {
                    "status": "warning",
                    "warning": "window_invalid_size",
                    "timestamp": _utc_now(),
                    "hwnd": hwnd,
                    "window_title": window_title,
                    "bbox": list(bbox),
                    "frame_index": frame_index,
                }
                _heartbeat(heartbeat_file, warning)
                _write_jsonl(log_file, {"event": "window_invalid_size", **warning})
                time.sleep(args.interval_seconds)
                continue
            frame_index += 1
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            frame_path = output_dir / f"winmerge_frame_{stamp}_{frame_index:06d}.png"
            try:
                ImageGrab.grab(window=hwnd).save(frame_path)
                capture_mode = "window_hwnd"
            except TypeError:
                ImageGrab.grab(bbox=bbox).save(frame_path)
                capture_mode = "screen_bbox_fallback"
            sidecar = _capture_metadata(metadata_file)
            timestamp = _utc_now()
            sidecar.update(
                {
                    "frame_path": str(frame_path),
                    "timestamp": timestamp,
                    "hwnd": hwnd,
                    "window_title": window_title,
                    "bbox": list(bbox),
                    "capture_mode": capture_mode,
                    "frame_index": frame_index,
                }
            )
            _atomic_write_json(frame_path.with_suffix(".json"), sidecar)
            heartbeat = {
                "status": "running",
                "timestamp": timestamp,
                "frame_path": str(frame_path),
                "hwnd": hwnd,
                "window_title": window_title,
                "capture_reason": sidecar["capture_reason"],
                "action_id": sidecar["action_id"],
                "ui_state_hint": sidecar["ui_state_hint"],
                "frame_index": frame_index,
            }
            _heartbeat(heartbeat_file, heartbeat)
            _write_jsonl(log_file, {"event": "frame_saved", **heartbeat})
            time.sleep(args.interval_seconds)
    finally:
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
'@

Set-Content -LiteralPath $RunnerPath -Value $runner -Encoding UTF8

$arguments = @(
  $RunnerPath,
  "--output-dir", $OutputDir,
  "--window-title-pattern", $WindowTitlePattern,
  "--interval-seconds", ([string]$IntervalSeconds),
  "--duration-seconds", ([string]$DurationSeconds),
  "--metadata-file", $MetadataFile,
  "--pid-file", $PidFile,
  "--log-file", $LogFile,
  "--heartbeat-file", $HeartbeatFile
)

$process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
Start-Sleep -Milliseconds 500
if (!(Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
  throw "WinMerge frame pump failed to start. See $LogFile"
}

[pscustomobject]@{
  pid = $process.Id
  output_dir = $OutputDir
  pid_file = $PidFile
  log_file = $LogFile
  runner = $RunnerPath
  metadata_file = $MetadataFile
  heartbeat_file = $HeartbeatFile
} | ConvertTo-Json

