from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
from typing import Any

from ai_screenshot_platform.v3.schemas import InputGatewayHealth, V3TaskConfig


def default_diagnosis_path() -> Path:
    explicit = os.environ.get("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS")
    if explicit:
        return Path(explicit)
    home = Path(os.environ.get("APP_SHOT_HOME", "D:/work/app-shot"))
    return home / "logs" / "input_gateway_diagnosis.json"


def load_input_gateway_readiness(path: str | Path | None = None, target_config: V3TaskConfig | None = None) -> InputGatewayHealth:
    diagnosis_path = Path(path) if path is not None else default_diagnosis_path()
    if not diagnosis_path.is_file():
        readiness = InputGatewayHealth(
            real_input_allowed=_real_input_allowed(),
            diagnosis_path=str(diagnosis_path),
            blockers=["input_gateway_not_measured"],
            details={"diagnosis_present": False},
        )
        return enrich_target_window_readiness(readiness, target_config)
    try:
        payload = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        readiness = InputGatewayHealth(
            real_input_allowed=_real_input_allowed(),
            diagnosis_path=str(diagnosis_path),
            blockers=[f"input_gateway_diagnosis_invalid:{exc}"],
            details={"diagnosis_present": True},
        )
        return enrich_target_window_readiness(readiness, target_config)
    readiness = input_gateway_readiness_from_diagnosis(payload if isinstance(payload, dict) else {}, real_input_allowed=_real_input_allowed())
    readiness.diagnosis_path = str(diagnosis_path)
    return enrich_target_window_readiness(readiness, target_config)


def input_gateway_readiness_from_diagnosis(payload: dict[str, Any], *, real_input_allowed: bool = True) -> InputGatewayHealth:
    cursor = _probe_ok(payload.get("get_cursor_pos"))
    set_cursor = _probe_ok(payload.get("set_cursor_pos"))
    sendinput = _probe_callable(payload.get("sendinput"))
    mouse_event = _probe_callable(payload.get("mouse_event"))
    pyautogui = _available(payload.get("pyautogui"))
    same_session = bool(payload.get("same_desktop_session_ready") is True or payload.get("same_desktop_session") is True)
    same_integrity = bool(payload.get("same_integrity_ready") is True or payload.get("same_integrity") is True)
    interactive = bool(payload.get("interactive_desktop_ready") is True or _probe_ok(payload.get("interactive_desktop")))
    cursor_error = _probe_error(payload.get("get_cursor_pos"))
    cursor_access_denied = _is_access_denied(cursor_error)
    safe_context = same_session and same_integrity and interactive
    keyboard_input_ready = bool(real_input_allowed and safe_context and sendinput)
    mouse_move_ready = bool(real_input_allowed and safe_context and (sendinput or mouse_event))
    mouse_click_ready = bool(real_input_allowed and safe_context and cursor and ((set_cursor and (sendinput or mouse_event)) or pyautogui))
    target_window_found = _target_found(payload)
    target_window_foreground = _target_foreground(payload)
    current_foreground = _foreground_from_payload(payload) or current_foreground_window()
    blockers: list[str] = []

    if not real_input_allowed:
        blockers.append("real_input_disabled")
    if not cursor:
        blockers.append("cursor_read_access_denied" if cursor_access_denied else "cursor_read_not_ready")
    if not keyboard_input_ready:
        if real_input_allowed and safe_context and not sendinput:
            blockers.append("sendinput_not_callable")
        else:
            blockers.append("keyboard_input_not_ready")
    if not mouse_move_ready:
        blockers.append("mouse_move_not_ready")
    if not mouse_click_ready:
        blockers.append("cursor_read_access_denied" if cursor_access_denied else "mouse_click_not_ready")
    if not same_session:
        blockers.append("same_desktop_session_not_ready")
    if not same_integrity:
        blockers.append("same_integrity_not_ready")
    if not interactive:
        blockers.append("interactive_desktop_not_ready")
    if not target_window_found:
        blockers.append("target_window_not_found")
    elif not target_window_foreground:
        blockers.append("target_window_not_foreground")

    if mouse_click_ready and cursor:
        click_backend = "computer_use_backend"
    elif mouse_click_ready and (sendinput or mouse_event):
        click_backend = "win32_sendinput_backend"
    elif mouse_click_ready and pyautogui:
        click_backend = "pyautogui_backend"
    else:
        click_backend = "dry_run_backend"
    input_ready = bool(keyboard_input_ready and mouse_move_ready and mouse_click_ready and target_window_found and target_window_foreground)

    return InputGatewayHealth(
        input_gateway_ready=input_ready,
        real_input_allowed=real_input_allowed,
        keyboard_input_ready=keyboard_input_ready,
        mouse_move_ready=mouse_move_ready,
        cursor_read_ready=cursor,
        cursor_read_access_denied=cursor_access_denied,
        mouse_click_ready=mouse_click_ready,
        target_window_found=target_window_found,
        target_window_foreground=target_window_foreground,
        current_foreground_window=current_foreground,
        same_desktop_session_ready=same_session,
        same_integrity_ready=same_integrity,
        interactive_desktop_ready=interactive,
        click_backend=click_backend,
        blockers=_dedupe(blockers),
        details=payload,
    )


def enrich_target_window_readiness(readiness: InputGatewayHealth, config: V3TaskConfig | None) -> InputGatewayHealth:
    if config is None:
        return readiness
    status = target_window_status(config)
    found = bool(status.get("target_window_found"))
    foreground = bool(status.get("target_window_foreground"))
    blockers = [item for item in readiness.blockers if item not in {"target_window_not_found", "target_window_not_foreground"}]
    if not found:
        blockers.append("target_window_not_found")
    elif not foreground:
        blockers.append("target_window_not_foreground")
    readiness.target_window_found = found
    readiness.target_window_foreground = foreground
    current = status.get("current_foreground_window")
    if isinstance(current, dict):
        readiness.current_foreground_window = current
    readiness.input_gateway_ready = bool(
        readiness.keyboard_input_ready
        and readiness.mouse_move_ready
        and readiness.mouse_click_ready
        and readiness.target_window_found
        and readiness.target_window_foreground
    )
    readiness.blockers = _dedupe(blockers)
    details = dict(readiness.details)
    details["target_window"] = status
    readiness.details = details
    return readiness


def blocked_reason_for_action(action_type: str, readiness: InputGatewayHealth) -> str | None:
    if not readiness.real_input_allowed:
        return "real_input_disabled"
    if not readiness.interactive_desktop_ready:
        return "interactive_desktop_not_ready"
    if not readiness.same_desktop_session_ready:
        return "same_desktop_session_not_ready"
    if not readiness.same_integrity_ready:
        return "same_integrity_not_ready"
    if not readiness.target_window_found:
        return "target_window_not_found"
    if not readiness.target_window_foreground:
        return "target_window_not_foreground"
    if action_type in {"key_hold", "key_press", "hotkey"}:
        return None if readiness.keyboard_input_ready else _keyboard_blocker(readiness)
    if action_type in {"mouse_move", "mouse_move_small"}:
        return None if readiness.mouse_move_ready else "mouse_move_not_ready"
    if action_type in {"mouse_click", "click", "ui_click", "drag", "scroll"}:
        if readiness.mouse_click_ready:
            return None
        return "cursor_read_access_denied" if readiness.cursor_read_access_denied else "mouse_click_not_ready"
    return None


def list_visible_windows() -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    user32 = ctypes.windll.user32
    windows: list[dict[str, object]] = []
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_title(hwnd)
        if not title:
            return True
        pid = _window_pid(hwnd)
        windows.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "process_name": _process_name(pid),
                "pid": pid,
                "visible": True,
                "foreground": int(hwnd) == int(user32.GetForegroundWindow()),
            }
        )
        return True

    user32.EnumWindows(enum_proc(callback), 0)
    return windows


def focus_target_window(config: V3TaskConfig | None) -> dict[str, object]:
    target = find_target_window(config)
    if target is None:
        return {
            "ok": False,
            "focused": False,
            "blocked_reason": "target_window_not_found",
            "target_window": None,
            "current_foreground_window": current_foreground_window(),
        }
    if os.name != "nt":
        return {"ok": False, "focused": False, "blocked_reason": "not_windows", "target_window": target, "current_foreground_window": None}
    user32 = ctypes.windll.user32
    hwnd = int(target["hwnd"])
    try:
        user32.ShowWindow(hwnd, 5)
        focused = bool(user32.SetForegroundWindow(hwnd))
    except Exception as exc:  # pragma: no cover - depends on interactive desktop.
        return {
            "ok": False,
            "focused": False,
            "blocked_reason": f"set_foreground_failed:{exc}",
            "target_window": target,
            "current_foreground_window": current_foreground_window(),
        }
    status = target_window_status(config)
    foreground = bool(status.get("target_window_foreground"))
    return {
        "ok": foreground,
        "focused": focused and foreground,
        "blocked_reason": None if foreground else "target_window_not_foreground",
        "target_window": target,
        "current_foreground_window": status.get("current_foreground_window"),
    }


def target_window_status(config: V3TaskConfig | None) -> dict[str, object]:
    current = current_foreground_window()
    target = find_target_window(config)
    if target is None:
        return {
            "target_window_found": False,
            "target_window_foreground": False,
            "target_window": None,
            "current_foreground_window": current,
        }
    return {
        "target_window_found": True,
        "target_window_foreground": bool(current and int(current.get("hwnd") or 0) == int(target.get("hwnd") or 0)),
        "target_window": target,
        "current_foreground_window": current,
    }


def find_target_window(config: V3TaskConfig | None) -> dict[str, object] | None:
    if config is None:
        return None
    target_hwnd = int(config.target_window_hwnd or 0)
    target_title = (config.target_window_title or "").strip().casefold()
    target_process = (config.target_process_name or "").strip().casefold()
    for window in list_visible_windows():
        hwnd_match = target_hwnd > 0 and int(window.get("hwnd") or 0) == target_hwnd
        title_match = bool(target_title and target_title in str(window.get("title") or "").casefold())
        process_match = bool(target_process and target_process == str(window.get("process_name") or "").casefold())
        if hwnd_match or (title_match and (not target_process or process_match)):
            return window
    return None


def current_foreground_window() -> dict[str, object] | None:
    if os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    hwnd = int(user32.GetForegroundWindow())
    if not hwnd:
        return None
    pid = _window_pid(hwnd)
    return {
        "hwnd": hwnd,
        "title": _window_title(hwnd),
        "process_name": _process_name(pid),
        "pid": pid,
        "visible": bool(user32.IsWindowVisible(hwnd)),
        "foreground": True,
    }


def _probe_ok(value: object) -> bool:
    return isinstance(value, dict) and value.get("ok") is True


def _probe_callable(value: object) -> bool:
    return isinstance(value, dict) and (value.get("callable") is True or value.get("ok") is True)


def _available(value: object) -> bool:
    return isinstance(value, dict) and value.get("available") is True


def _probe_error(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    error = value.get("error")
    return error if isinstance(error, str) else ""


def _is_access_denied(error: str) -> bool:
    normalized = error.casefold()
    return "access is denied" in normalized or "access denied" in normalized or "拒绝访问" in error


def _real_input_allowed() -> bool:
    return os.environ.get("APP_SHOT_ALLOW_REAL_INPUT", "").strip() == "1"


def _target_found(payload: dict[str, Any]) -> bool:
    target = payload.get("target_process")
    if isinstance(target, dict):
        return bool(target.get("found") is True)
    return False


def _target_foreground(payload: dict[str, Any]) -> bool:
    target = payload.get("target_process")
    if isinstance(target, dict):
        return bool(target.get("foreground") is True or target.get("is_foreground") is True)
    return False


def _foreground_from_payload(payload: dict[str, Any]) -> dict[str, object] | None:
    foreground = payload.get("foreground_window")
    return foreground if isinstance(foreground, dict) else None


def _keyboard_blocker(readiness: InputGatewayHealth) -> str:
    details = readiness.details if isinstance(readiness.details, dict) else {}
    if not _probe_callable(details.get("sendinput")):
        return "sendinput_not_callable"
    return "keyboard_input_not_ready"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _window_title(hwnd: int) -> str:
    if os.name != "nt":
        return ""
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _window_pid(hwnd: int) -> int:
    if os.name != "nt":
        return 0
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _process_name(pid: int) -> str | None:
    if os.name != "nt" or not pid:
        return None
    kernel32 = ctypes.windll.kernel32
    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return None
    try:
        size = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)
    return None
