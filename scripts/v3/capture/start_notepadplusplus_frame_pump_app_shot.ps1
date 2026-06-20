param(
  [string]$AppShotHome = "D:\work\app-shot",
  [string]$OutputDir = "",
  [string]$WindowTitlePattern = "Notepad\+\+",
  [double]$IntervalSeconds = 1.0,
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

$Python = Join-Path $AppShotHome "venvs\v3\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Python)) {
  throw "Python venv not found: $Python"
}

$PumpRoot = Join-Path $AppShotHome "cache\frame-pump"
$PidFile = Join-Path $PumpRoot "notepadplusplus_frame_pump.pid"
$LogFile = Join-Path $PumpRoot "notepadplusplus_frame_pump.log"
$RunnerPath = Join-Path $PumpRoot "notepadplusplus_frame_pump.py"
New-Item -ItemType Directory -Force -Path $PumpRoot | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (Test-Path -LiteralPath $PidFile) {
  $existingPid = (Get-Content -LiteralPath $PidFile -Raw).Trim()
  if ($existingPid -and (Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue)) {
    throw "Notepad++ frame pump is already running: pid $existingPid"
  }
  Remove-Item -LiteralPath $PidFile -Force
}

$runner = @'
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import re
import sys
import time
from datetime import datetime
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


def _write_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--window-title-pattern", required=True)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--duration-seconds", type=int, default=0)
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pid_file = Path(args.pid_file)
    log_file = Path(args.log_file)
    pid_file.write_text(str(ctypes.windll.kernel32.GetCurrentProcessId()), encoding="utf-8")
    frame_index = 0
    started = time.monotonic()
    try:
        while True:
            if args.duration_seconds > 0 and time.monotonic() - started >= args.duration_seconds:
                return 0
            match = _find_window(args.window_title_pattern)
            if not match:
                _write_jsonl(log_file, {"event": "window_missing", "pattern": args.window_title_pattern})
                time.sleep(args.interval_seconds)
                continue
            hwnd, title = match
            if user32.IsIconic(hwnd):
                _write_jsonl(log_file, {"event": "window_minimized", "title": title})
                time.sleep(args.interval_seconds)
                continue
            bbox = _window_rect(hwnd)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= 20 or height <= 20:
                _write_jsonl(log_file, {"event": "window_too_small", "title": title, "bbox": bbox})
                time.sleep(args.interval_seconds)
                continue
            frame_index += 1
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = output_dir / f"frame_{stamp}_{frame_index:06d}.png"
            ImageGrab.grab(bbox=bbox).save(path)
            _write_jsonl(log_file, {"event": "frame_saved", "path": str(path), "title": title, "bbox": bbox})
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
  "--pid-file", $PidFile,
  "--log-file", $LogFile
)

$process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
Start-Sleep -Milliseconds 500
if (!(Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
  throw "Notepad++ frame pump failed to start. See $LogFile"
}

[pscustomobject]@{
  pid = $process.Id
  output_dir = $OutputDir
  pid_file = $PidFile
  log_file = $LogFile
  runner = $RunnerPath
} | ConvertTo-Json
