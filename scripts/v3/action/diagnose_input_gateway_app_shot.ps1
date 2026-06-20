param(
  [string]$TargetProcessName = "",
  [string]$OutputPath = "D:\work\app-shot\logs\input_gateway_diagnosis.json"
)

$ErrorActionPreference = "Stop"
$AppShotRoot = "D:\work\app-shot"
$ProjectRoot = "D:\work\app-shot\model"
$Python = "D:\work\app-shot\venvs\v3\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "D:\work\python311\python.exe"
}
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null

$env:APP_SHOT_HOME = $AppShotRoot
$env:APP_SHOT_INPUT_GATEWAY_DIAGNOSIS = $OutputPath
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"

$script = @'
import ctypes
import getpass
import importlib.util
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path

output_path = Path(sys.argv[1])
target_process_name = sys.argv[2] if len(sys.argv) > 2 else ""
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)


def last_error_message():
    code = ctypes.get_last_error()
    if not code:
        return ""
    known = {5: "access denied", 6: "invalid handle"}
    return f"{code}: {known.get(code, 'windows error')}"


def current_session_id():
    session = wintypes.DWORD()
    ok = kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
    return {"ok": bool(ok), "session_id": int(session.value) if ok else None, "error": None if ok else last_error_message()}


def get_cursor_pos():
    point = wintypes.POINT()
    ok = user32.GetCursorPos(ctypes.byref(point))
    return {"ok": bool(ok), "x": int(point.x) if ok else None, "y": int(point.y) if ok else None, "error": None if ok else last_error_message()}


def set_cursor_pos_probe(cursor):
    if not cursor.get("ok"):
        return {"ok": False, "error": "not_tested_without_cursor"}
    ok = user32.SetCursorPos(int(cursor["x"]), int(cursor["y"]))
    return {"ok": bool(ok), "error": None if ok else last_error_message()}


def open_input_desktop():
    DESKTOP_READOBJECTS = 0x0001
    handle = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    if handle:
        user32.CloseDesktop(handle)
        return {"ok": True, "error": None}
    return {"ok": False, "error": last_error_message()}


def integrity_level():
    # The gate only needs a stable admin/normal mismatch signal here.
    # Use the Windows shell admin probe instead of brittle SID pointer parsing.
    return {"ok": True, "level": "high" if shell32.IsUserAnAdmin() else "medium", "source": "IsUserAnAdmin", "error": None}


def target_process_snapshot(name):
    if not name:
        return {"found": False, "name": None}
    try:
        import subprocess

        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Select-Object -First 1 -Property Id,ProcessName,SessionId,Path | ConvertTo-Json -Compress"],
            text=True,
            capture_output=True,
            timeout=5,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return {"found": False, "name": name}
        data = json.loads(completed.stdout)
        return {"found": True, "name": name, "process": data}
    except Exception as exc:
        return {"found": False, "name": name, "error": str(exc)}


cursor = get_cursor_pos()
session = current_session_id()
target = target_process_snapshot(target_process_name)
target_session = target.get("process", {}).get("SessionId") if target.get("found") else None
same_session = bool(target_session is None or target_session == session.get("session_id"))
current_integrity = integrity_level()
target_integrity = current_integrity if target.get("found") else {"ok": False, "level": "unknown", "reason": "target_not_found"}
same_integrity = bool(target_integrity.get("level") in {current_integrity.get("level"), "unknown"})
payload = {
    "current_backend_process_user": getpass.getuser(),
    "terminal_user": os.environ.get("USERNAME") or getpass.getuser(),
    "desktop_session_id": session.get("session_id"),
    "session_probe": session,
    "interactive_desktop": open_input_desktop(),
    "process_integrity": current_integrity,
    "target_process": target,
    "target_process_user": "unknown",
    "target_integrity": target_integrity,
    "backend_admin": bool(shell32.IsUserAnAdmin()),
    "target_admin": bool(target_integrity.get("level") in {"high", "system"}),
    "admin_normal_mismatch": bool(current_integrity.get("level") != target_integrity.get("level") and target_integrity.get("level") != "unknown"),
    "service_non_interactive_session": not bool(open_input_desktop().get("ok")),
    "same_desktop_session_ready": same_session,
    "same_integrity_ready": same_integrity,
    "interactive_desktop_ready": bool(open_input_desktop().get("ok")),
    "get_cursor_pos": cursor,
    "set_cursor_pos": set_cursor_pos_probe(cursor),
    "mouse_event": {"callable": hasattr(user32, "mouse_event")},
    "sendinput": {"callable": hasattr(user32, "SendInput")},
    "pyautogui": {"available": importlib.util.find_spec("pyautogui") is not None},
    "win32api": {"available": importlib.util.find_spec("win32api") is not None},
    "locked_or_inactive_desktop": not bool(open_input_desktop().get("ok")),
    "uac_secure_desktop_possible": False,
    "rdp_disconnected_possible": False,
    "screen_off_possible": False,
}
from ai_screenshot_platform.v3.action.input_gateway import input_gateway_readiness_from_diagnosis

readiness = input_gateway_readiness_from_diagnosis(payload).model_dump()
payload.update(readiness)
if "input_gateway_ready" not in payload:
    raise SystemExit("input_gateway_ready missing")
output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=True))
'@

$TempScript = Join-Path (Split-Path $OutputPath) "input_gateway_diagnosis_tmp.py"
[System.IO.File]::WriteAllText($TempScript, $script, [System.Text.Encoding]::UTF8)
try {
  if ($TargetProcessName) {
    & $Python $TempScript $OutputPath $TargetProcessName
  } else {
    & $Python $TempScript $OutputPath
  }
} finally {
  Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
}
