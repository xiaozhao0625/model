from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request


WORKER_METHODS = {
    "worker_pc_game_w1": "windows_safe_window",
    "worker_pc_app_web_w2": "playwright_edge_local_html",
    "worker_android_w3": "adb_emulator_screencap",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def main() -> None:
    args = parse_args()
    client = MasterClient(args.master_url)
    client.post(f"/api/workers/{args.worker_id}/heartbeat", {})
    claim = client.post(f"/api/workers/{args.worker_id}/claim", {})
    if claim.get("status") != "claimed" or not claim.get("task"):
        print(json.dumps({"worker_id": args.worker_id, "claim_status": claim.get("status"), "task": None}, indent=2))
        return

    task = claim["task"]
    method = WORKER_METHODS.get(args.worker_id)
    if not method:
        raise ValueError(f"unsupported P14 worker_id: {args.worker_id}")

    try:
        result = execute_task(args, task, method)
    except Exception as exc:  # Always close the claimed run and leave inspectable artifacts.
        result = write_failure_result(args, task, method, exc)
    payload = {
        "app_id": str(task["app_id"]),
        "run_id": str(task["run_id"]),
        "status": result["status"],
        "valid_total": result["valid_total"],
        "fixed_count": result["fixed_count"],
        "low_count": result["low_count"],
        "high_count": result["high_count"],
        "rejected_count": result["rejected_count"],
        "run_dir": result["run_dir"],
        "summary_path": result["summary_path"],
        "error": result.get("error"),
    }
    report = client.post(f"/api/workers/{args.worker_id}/runs/{task['run_id']}/report", payload)
    result["claim_status"] = claim["status"]
    result["report_status"] = report["run"]["status"]
    result["master_run"] = report["run"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one P14 minimal real worker task.")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--master-url", default="http://192.168.1.18:8000")
    parser.add_argument("--output-root", default=r"D:\work\runs")
    parser.add_argument("--target-total", type=int, default=3)
    parser.add_argument("--ffmpeg-path", default=r"D:\work\tools\ffmpeg\bin\ffmpeg.exe")
    parser.add_argument("--edge-path", default=r"C:\Program Files (x86)\Microsoft\EdgeCore\149.0.4022.69\msedge.exe")
    parser.add_argument("--adb-path", default=r"D:\work\tools\platform-tools\adb.exe")
    return parser.parse_args()


def execute_task(args: argparse.Namespace, task: dict[str, Any], method: str) -> dict[str, Any]:
    run_id = str(task["run_id"])
    worker_id = args.worker_id
    if worker_id == "worker_android_w3" and ("safe_variation" in run_id or "safe_ui" in run_id):
        method = "adb_safe_ui_variation"
    run_dir = Path(args.output_root) / run_id
    low_dir = run_dir / "low"
    for folder in [run_dir / "fixed", low_dir, run_dir / "high", run_dir / "rejected"]:
        folder.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    extra_metadata: dict[str, dict[str, Any]] = {}
    if method == "ffmpeg_testsrc":
        files = capture_ffmpeg_testsrc(Path(args.ffmpeg_path), low_dir, args.target_total)
        platform = "pc_obs"
        capture_method = "ffmpeg_testsrc"
    elif method == "windows_safe_window":
        files, extra_metadata = capture_windows_safe_window(run_dir, low_dir, args.target_total)
        platform = "pc_app"
        capture_method = "windows_safe_window_capture"
    elif method == "playwright_edge_local_html":
        files = capture_playwright_local_html(Path(args.edge_path), low_dir, run_dir, args.target_total)
        platform = "web"
        capture_method = "playwright_edge_content_only"
    elif method == "adb_emulator_screencap":
        files = capture_adb_emulator(Path(args.adb_path), low_dir, args.target_total)
        platform = "android"
        capture_method = "adb_screencap"
    elif method == "adb_safe_ui_variation":
        files, extra_metadata = capture_adb_safe_variation(Path(args.adb_path), low_dir, args.target_total)
        platform = "android"
        capture_method = "adb_safe_ui_variation"
    else:
        raise ValueError(f"unsupported method: {method}")

    records, counts = build_records(
        files=files,
        run_id=run_id,
        worker_id=worker_id,
        task_id=run_id,
        platform=platform,
        capture_method=capture_method,
        source_method=method,
        extra_metadata=extra_metadata,
    )
    finished_at = now_iso()
    meta_path = run_dir / "meta.jsonl"
    with meta_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    status = "capture_completed"
    error: str | None = None
    if method == "adb_safe_ui_variation" and counts["valid_total"] < min(args.target_total, 15):
        status = "failed_low_yield"
        error = "w3_low_variation_blocked"

    summary = {
        "run_id": run_id,
        "task_id": run_id,
        "worker_id": worker_id,
        "status": status,
        "valid_total": counts["valid_total"],
        "fixed_count": 0,
        "low_count": counts["low_count"],
        "high_count": 0,
        "rejected_count": counts["rejected_count"],
        "duplicate_count": counts["duplicate_count"],
        "target_total": args.target_total,
        "started_at": started_at,
        "finished_at": finished_at,
        "artifacts_root": str(run_dir),
        "meta_path": str(meta_path),
        "capture_method": capture_method,
        "source_method": method,
    }
    if method == "ffmpeg_testsrc":
        summary.update(
            {
                "test_source": True,
                "production_capture": False,
                "source_type": "test_source",
                "source_resolution": "1280x720",
                "output_width": 1280,
                "output_height": 720,
            }
        )
    if method == "playwright_edge_local_html":
        summary.update(
            {
                "content_only": True,
                "browser_chrome_included": False,
                "taskbar_included": False,
                "viewport_width": 900,
                "viewport_height": 520,
                "source_resolution": "900x520 content area",
                "downloaded_browser": False,
                "ran_playwright_install": False,
                "real_web_capture": False,
                "test_source": False,
                "production_capture": True,
            }
        )
    if method == "windows_safe_window":
        summary.update(
            {
                "capture_method": "windows_safe_window_capture",
                "source_type": "safe_windows_test_app",
                "allowed_windows": ["notepad.exe"],
                "test_source": False,
                "production_capture": True,
                "taskbar_included": False,
                "browser_chrome_included": False,
                "real_safe_window_capture": True,
                "ffmpeg_testsrc_used": False,
            }
        )
    if method == "adb_emulator_screencap":
        summary.update({"apk_installed": False, "game_started": False, "real_app_capture": False, "test_source": False, "production_capture": True})
    if method == "adb_safe_ui_variation":
        summary.update(
            {
                "apk_installed": False,
                "game_started": False,
                "account_login": False,
                "system_settings_modified": False,
                "test_source": False,
                "production_capture": True,
                "safe_actions": [
                    "settings_home",
                    "settings_wifi",
                    "settings_bluetooth",
                    "settings_display",
                    "settings_sound",
                    "settings_apps",
                    "settings_storage",
                    "settings_accessibility",
                    "settings_date",
                    "settings_locale",
                    "settings_device_info",
                    "settings_home_scrolled",
                ],
                "variation_actions": sorted(
                    {
                        str(item.get("action_name"))
                        for item in extra_metadata.values()
                        if item.get("action_name")
                    }
                ),
                "low_variation": counts["valid_total"] < min(args.target_total, 15),
            }
        )

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run.log").write_text(
        json.dumps({"event": status, "run_id": run_id, "worker_id": worker_id, "count": len(files), "error": error}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "worker_id": worker_id,
        "run_id": run_id,
        "status": status,
        "valid_total": counts["valid_total"],
        "fixed_count": 0,
        "low_count": counts["low_count"],
        "high_count": 0,
        "rejected_count": counts["rejected_count"],
        "duplicate_count": counts["duplicate_count"],
        "screenshot_count": len(files),
        "run_dir": str(run_dir),
        "meta_path": str(meta_path),
        "summary_path": str(summary_path),
        "capture_method": capture_method,
        "source_method": method,
        "error": error,
    }


def write_failure_result(args: argparse.Namespace, task: dict[str, Any], method: str, exc: Exception) -> dict[str, Any]:
    run_id = str(task["run_id"])
    worker_id = args.worker_id
    run_dir = Path(args.output_root) / run_id
    for folder in [run_dir / "fixed", run_dir / "low", run_dir / "high", run_dir / "rejected"]:
        folder.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    message = f"{type(exc).__name__}: {exc}"
    lower_message = message.lower()
    desktop_session_required = "desktop" in lower_message or "window handle" in lower_message or "session" in lower_message
    status = "failed_low_yield"
    capture_method = {
        "windows_safe_window": "windows_safe_window_capture",
        "playwright_edge_local_html": "playwright_edge_content_only",
        "adb_emulator_screencap": "adb_screencap",
        "adb_safe_ui_variation": "adb_safe_ui_variation",
        "ffmpeg_testsrc": "ffmpeg_testsrc",
    }.get(method, method)
    meta_path = run_dir / "meta.jsonl"
    meta_path.write_text("", encoding="utf-8")
    summary = {
        "run_id": run_id,
        "task_id": run_id,
        "worker_id": worker_id,
        "status": status,
        "valid_total": 0,
        "fixed_count": 0,
        "low_count": 0,
        "high_count": 0,
        "rejected_count": 0,
        "duplicate_count": 0,
        "target_total": args.target_total,
        "started_at": started_at,
        "finished_at": now_iso(),
        "artifacts_root": str(run_dir),
        "meta_path": str(meta_path),
        "capture_method": capture_method,
        "source_method": method,
        "error": message,
        "desktop_session_required": desktop_session_required,
        "failure_reason": "desktop_session_required" if desktop_session_required else "capture_failed",
        "test_source": False,
        "production_capture": True,
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run.log").write_text(
        json.dumps(
            {"event": status, "run_id": run_id, "worker_id": worker_id, "error": message},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "worker_id": worker_id,
        "run_id": run_id,
        "status": status,
        "valid_total": 0,
        "fixed_count": 0,
        "low_count": 0,
        "high_count": 0,
        "rejected_count": 0,
        "duplicate_count": 0,
        "screenshot_count": 0,
        "run_dir": str(run_dir),
        "meta_path": str(meta_path),
        "summary_path": str(summary_path),
        "capture_method": capture_method,
        "source_method": method,
        "error": message,
    }


def capture_ffmpeg_testsrc(ffmpeg: Path, low_dir: Path, total: int) -> list[Path]:
    if not ffmpeg.exists():
        raise FileNotFoundError(str(ffmpeg))
    output_pattern = low_dir / "ffmpeg_testsrc_%03d.png"
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=duration={total}:size=1280x720:rate=1",
        "-frames:v",
        str(total),
        str(output_pattern),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "ffmpeg_testsrc failed").strip()
        raise RuntimeError(details)
    return sorted(low_dir.glob("ffmpeg_testsrc_*.png"))


def capture_playwright_local_html(edge: Path, low_dir: Path, run_dir: Path, total: int) -> list[Path]:
    if not edge.exists():
        raise FileNotFoundError(str(edge))
    from playwright.sync_api import sync_playwright

    html_path = run_dir / "p14_local_content.html"
    html_path.write_text(
        """<!doctype html><html><head><meta charset='utf-8'><style>
body{margin:0;background:#101827;color:#e5e7eb;font-family:Arial,sans-serif}
#capture{width:900px;height:520px;display:flex;align-items:center;justify-content:center;flex-direction:column}
.frame{font-size:44px;font-weight:700}.sub{margin-top:16px;color:#93c5fd}
</style></head><body><main id='capture'><div class='frame' id='frame'></div><div class='sub'>local HTML only, no web login, no external network</div></main></body></html>""",
        encoding="utf-8",
    )
    files: list[Path] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(edge),
            headless=True,
            args=["--disable-gpu", "--no-first-run"],
        )
        page = browser.new_page(viewport={"width": 900, "height": 520}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="domcontentloaded")
        capture = page.locator("#capture")
        for index in range(1, total + 1):
            page.locator("#frame").evaluate("(node, value) => { node.textContent = value; }", f"P14-1 Frame {index}")
            output = low_dir / f"playwright_local_{index:03d}.png"
            capture.screenshot(path=str(output))
            files.append(output)
        browser.close()
    return files


def capture_windows_safe_window(run_dir: Path, low_dir: Path, total: int) -> tuple[list[Path], dict[str, dict[str, Any]]]:
    workspace = run_dir / "safe_window_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    capture_script = run_dir / "capture_safe_windows.ps1"
    manifest_path = run_dir / "windows_safe_window_manifest.json"
    safe_files_manifest_path = run_dir / "windows_safe_files.json"
    safe_files = []
    for index in range(1, total + 1):
        safe_file = workspace / f"p14_safe_notepad_{index:03d}.txt"
        safe_file.write_text(
            "\n".join(
                [
                    f"P14.3.1 W1 safe Notepad target #{index:03d}",
                    "This is a synthetic local safety window.",
                    "No account, no game, no real user page, no secrets.",
                    f"Variation token: SAFE-WINDOW-{index:03d}-{index * 7919}",
                ]
            ),
            encoding="utf-8",
        )
        safe_files.append(safe_file)
    safe_files_manifest_path.write_text(json.dumps([str(item) for item in safe_files], ensure_ascii=False), encoding="utf-8")

    capture_script.write_text(
        r"""
param(
  [string]$OutputDir,
  [string]$ManifestPath,
  [string]$SafeFilesManifestPath
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Capture {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
function Wait-WindowHandle([System.Diagnostics.Process]$Process, [string]$TitleHint) {
  for ($i = 0; $i -lt 80; $i++) {
    $Process.Refresh()
    if ($Process.MainWindowHandle -ne [IntPtr]::Zero) { return $Process.MainWindowHandle }
    $candidate = Get-Process -Name "notepad" -ErrorAction SilentlyContinue |
      Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and ($_.MainWindowTitle -like "*$TitleHint*" -or $_.MainWindowTitle -like "*P14*") } |
      Select-Object -First 1
    if ($candidate) { return $candidate.MainWindowHandle }
    $fallback = Get-Process -Name "notepad" -ErrorAction SilentlyContinue |
      Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
      Sort-Object StartTime -Descending |
      Select-Object -First 1
    if ($fallback) { return $fallback.MainWindowHandle }
    Start-Sleep -Milliseconds 250
  }
  throw "window handle not available for process $($Process.Id)"
}
function Capture-Window([IntPtr]$Handle, [string]$Path) {
  $rect = New-Object Win32Capture+RECT
  [void][Win32Capture]::GetWindowRect($Handle, [ref]$rect)
  $client = New-Object Win32Capture+RECT
  [void][Win32Capture]::GetClientRect($Handle, [ref]$client)
  $width = [Math]::Max(1, $rect.Right - $rect.Left)
  $height = [Math]::Max(1, $rect.Bottom - $rect.Top)
  $bitmap = New-Object System.Drawing.Bitmap $width, $height
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size $width, $height))
  $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose()
  $bitmap.Dispose()
  return @{
    window_rect = @{ left = $rect.Left; top = $rect.Top; right = $rect.Right; bottom = $rect.Bottom }
    client_rect = @{ left = 0; top = 0; right = $client.Right; bottom = $client.Bottom }
    crop_rect = @{ left = 0; top = 0; right = $width; bottom = $height }
    output_width = $width
    output_height = $height
  }
}
$SafeFiles = Get-Content -Raw $SafeFilesManifestPath | ConvertFrom-Json
$records = @()
$index = 0
foreach ($safeFile in $SafeFiles) {
  $index += 1
  $process = Start-Process -FilePath "notepad.exe" -ArgumentList @($safeFile) -PassThru
  try {
    $handle = Wait-WindowHandle $process ([System.IO.Path]::GetFileName($safeFile))
    [void][Win32Capture]::MoveWindow($handle, 80, 80, 960, 640, $true)
    [void][Win32Capture]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 700
    $output = Join-Path $OutputDir ("windows_safe_notepad_{0:D3}.png" -f $index)
    $metadata = Capture-Window $handle $output
    $metadata.file = $output
    $metadata.app_name = "notepad.exe"
    $metadata.window_title = "P14.3.1 safe Notepad target"
    $metadata.source_type = "pc_app_safe_window"
    $metadata.taskbar_included = $false
    $metadata.browser_chrome_included = $false
    $records += [pscustomobject]$metadata
  } finally {
    if (!$process.HasExited) {
      $process.CloseMainWindow() | Out-Null
      Start-Sleep -Milliseconds 300
      if (!$process.HasExited) { $process.Kill() }
    }
  }
}
$records | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $ManifestPath
""",
        encoding="utf-8",
    )
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(capture_script),
        "-OutputDir",
        str(low_dir),
        "-ManifestPath",
        str(manifest_path),
        "-SafeFilesManifestPath",
        str(safe_files_manifest_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "windows_safe_window_capture failed").strip()
        raise RuntimeError(details)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    extra_metadata = {str(Path(item["file"]).resolve()): item for item in manifest}
    files = sorted(low_dir.glob("windows_safe_notepad_*.png"))
    return files, extra_metadata


def capture_adb_emulator(adb: Path, low_dir: Path, total: int) -> list[Path]:
    if not adb.exists():
        raise FileNotFoundError(str(adb))
    devices = subprocess.check_output([str(adb), "devices"], text=True, encoding="utf-8", errors="ignore")
    if "emulator-" not in devices:
        raise RuntimeError("no emulator device visible in adb devices")
    boot_completed = subprocess.check_output([str(adb), "shell", "getprop", "sys.boot_completed"], text=True, encoding="utf-8", errors="ignore").strip()
    if boot_completed != "1":
        raise RuntimeError(f"emulator boot not completed: {boot_completed}")
    files: list[Path] = []
    for index in range(1, total + 1):
        output = low_dir / f"adb_emulator_{index:03d}.png"
        with output.open("wb") as handle:
            subprocess.run([str(adb), "exec-out", "screencap", "-p"], check=True, stdout=handle)
        files.append(output)
        time.sleep(1)
    return files


def capture_adb_safe_variation(adb: Path, low_dir: Path, total: int) -> tuple[list[Path], dict[str, dict[str, Any]]]:
    if not adb.exists():
        raise FileNotFoundError(str(adb))
    ensure_adb_ready(adb)
    safe_actions = [
        ("home", [[str(adb), "shell", "input", "keyevent", "KEYCODE_HOME"]]),
        ("notifications", [[str(adb), "shell", "cmd", "statusbar", "expand-notifications"]]),
        ("quick_settings", [[str(adb), "shell", "cmd", "statusbar", "expand-settings"]]),
        ("settings_home", [[str(adb), "shell", "am", "start", "-a", "android.settings.SETTINGS"]]),
        ("settings_display", [[str(adb), "shell", "am", "start", "-a", "android.settings.DISPLAY_SETTINGS"]]),
        ("settings_sound", [[str(adb), "shell", "am", "start", "-a", "android.settings.SOUND_SETTINGS"]]),
        ("settings_apps", [[str(adb), "shell", "am", "start", "-a", "android.settings.APPLICATION_SETTINGS"]]),
        ("settings_storage", [[str(adb), "shell", "am", "start", "-a", "android.settings.INTERNAL_STORAGE_SETTINGS"]]),
        ("settings_date", [[str(adb), "shell", "am", "start", "-a", "android.settings.DATE_SETTINGS"]]),
        ("settings_locale", [[str(adb), "shell", "am", "start", "-a", "android.settings.LOCALE_SETTINGS"]]),
        ("settings_device_info", [[str(adb), "shell", "am", "start", "-a", "android.settings.DEVICE_INFO_SETTINGS"]]),
        (
            "settings_home_scroll_down",
            [
                [str(adb), "shell", "am", "start", "-a", "android.settings.SETTINGS"],
                [str(adb), "shell", "input", "swipe", "540", "2050", "540", "700", "450"],
            ],
        ),
        (
            "settings_home_scroll_up",
            [
                [str(adb), "shell", "am", "start", "-a", "android.settings.SETTINGS"],
                [str(adb), "shell", "input", "swipe", "540", "700", "540", "2050", "450"],
            ],
        ),
        ("recent_apps", [[str(adb), "shell", "input", "keyevent", "KEYCODE_APP_SWITCH"]]),
        ("back_to_home", [[str(adb), "shell", "input", "keyevent", "KEYCODE_HOME"]]),
    ]
    files: list[Path] = []
    metadata: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    selected_actions = [safe_actions[(index - 1) % len(safe_actions)] for index in range(1, max(1, total) + 1)]
    for index, (name, commands) in enumerate(selected_actions, start=1):
        subprocess.run([str(adb), "shell", "cmd", "statusbar", "collapse"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.25)
        for command in commands:
            subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
        output = low_dir / f"adb_settings_safe_{index:03d}_{name}.png"
        with output.open("wb") as handle:
            subprocess.run([str(adb), "exec-out", "screencap", "-p"], check=True, stdout=handle)
        digest = sha256(output)
        is_duplicate = digest in seen
        seen.add(digest)
        metadata[str(output.resolve())] = {
            "action_name": name,
            "screen_state": name,
            "dedup_status": "duplicate" if is_duplicate else "new",
            "capture_method": "adb_safe_ui_variation",
            "source_method": "adb_safe_ui_variation",
        }
        files.append(output)
        time.sleep(0.6)
    return files, metadata


def ensure_adb_ready(adb: Path) -> None:
    devices = subprocess.check_output([str(adb), "devices"], text=True, encoding="utf-8", errors="ignore")
    if "emulator-" not in devices:
        raise RuntimeError("no emulator device visible in adb devices")
    boot_completed = subprocess.check_output([str(adb), "shell", "getprop", "sys.boot_completed"], text=True, encoding="utf-8", errors="ignore").strip()
    if boot_completed != "1":
        raise RuntimeError(f"emulator boot not completed: {boot_completed}")


def build_records(
    files: list[Path],
    run_id: str,
    worker_id: str,
    task_id: str,
    platform: str,
    capture_method: str,
    source_method: str,
    extra_metadata: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    duplicate_count = 0
    rejected_count = 0
    valid_total = 0
    for file_path in files:
        digest = sha256(file_path)
        is_duplicate = digest in seen
        seen.add(digest)
        if is_duplicate:
            duplicate_count += 1
        else:
            valid_total += 1
        width, height = png_dimensions(file_path)
        metadata = capture_metadata(
            capture_method=capture_method,
            source_method=source_method,
            width=width,
            height=height,
        )
        extra = (extra_metadata or {}).get(str(file_path.resolve()), {})
        metadata.update(extra)
        records.append(
            {
                "run_id": run_id,
                "worker_id": worker_id,
                "task_id": task_id,
                "platform": platform,
                "bucket": "low",
                "file_path": str(file_path),
                "content_hash": digest,
                "created_at": now_iso(),
                "capture_method": capture_method,
                "source_method": source_method,
                "width": width,
                "height": height,
                **metadata,
                "is_duplicate": is_duplicate,
                "rejected_reason": "duplicate" if is_duplicate else None,
            }
        )
    return records, {
        "valid_total": valid_total,
        "low_count": valid_total,
        "rejected_count": rejected_count,
        "duplicate_count": duplicate_count,
    }


def capture_metadata(capture_method: str, source_method: str, width: int, height: int) -> dict[str, Any]:
    if source_method == "ffmpeg_testsrc":
        return {
            "test_source": True,
            "production_capture": False,
            "source_type": "test_source",
            "source_resolution": f"{width}x{height} test source",
            "obs_canvas_width": width,
            "obs_canvas_height": height,
            "source_width": width,
            "source_height": height,
            "output_width": width,
            "output_height": height,
        }
    if capture_method == "playwright_edge_content_only":
        return {
            "content_only": True,
            "browser_chrome_included": False,
            "taskbar_included": False,
            "viewport_width": width,
            "viewport_height": height,
            "source_resolution": f"{width}x{height} page content area",
            "output_width": width,
            "output_height": height,
            "test_source": False,
            "production_capture": True,
        }
    if capture_method in {"adb_screencap", "adb_safe_ui_variation"}:
        return {
            "device_resolution": f"{width}x{height}",
            "source_resolution": f"{width}x{height} device screen",
            "output_width": width,
            "output_height": height,
            "test_source": False,
            "production_capture": True,
        }
    if capture_method == "windows_safe_window_capture":
        return {
            "source_type": "pc_app_safe_window",
            "window_rect": {"left": 0, "top": 0, "right": width, "bottom": height},
            "client_rect": {"left": 0, "top": 0, "right": width, "bottom": height},
            "crop_rect": {"left": 0, "top": 0, "right": width, "bottom": height},
            "source_resolution": f"{width}x{height} safe window",
            "output_width": width,
            "output_height": height,
            "test_source": False,
            "production_capture": True,
            "taskbar_included": False,
            "browser_chrome_included": False,
        }
    return {
        "output_width": width,
        "output_height": height,
        "test_source": False,
        "production_capture": True,
    }


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 0, 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MasterClient:
    def __init__(self, master_url: str) -> None:
        self.master_url = master_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.master_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("code") != 0:
            raise ValueError(data)
        return data["data"]


if __name__ == "__main__":
    main()
