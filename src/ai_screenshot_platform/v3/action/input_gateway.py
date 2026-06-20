from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ai_screenshot_platform.v3.schemas import InputGatewayHealth


def default_diagnosis_path() -> Path:
    explicit = os.environ.get("APP_SHOT_INPUT_GATEWAY_DIAGNOSIS")
    if explicit:
        return Path(explicit)
    home = Path(os.environ.get("APP_SHOT_HOME", "D:/work/app-shot"))
    return home / "logs" / "input_gateway_diagnosis.json"


def load_input_gateway_readiness(path: str | Path | None = None) -> InputGatewayHealth:
    diagnosis_path = Path(path) if path is not None else default_diagnosis_path()
    if not diagnosis_path.is_file():
        return InputGatewayHealth(
            diagnosis_path=str(diagnosis_path),
            blockers=["input_gateway_not_measured"],
            details={"diagnosis_present": False},
        )
    try:
        payload = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return InputGatewayHealth(
            diagnosis_path=str(diagnosis_path),
            blockers=[f"input_gateway_diagnosis_invalid:{exc}"],
            details={"diagnosis_present": True},
        )
    readiness = input_gateway_readiness_from_diagnosis(payload if isinstance(payload, dict) else {})
    readiness.diagnosis_path = str(diagnosis_path)
    return readiness


def input_gateway_readiness_from_diagnosis(payload: dict[str, Any]) -> InputGatewayHealth:
    cursor = _probe_ok(payload.get("get_cursor_pos"))
    set_cursor = _probe_ok(payload.get("set_cursor_pos"))
    sendinput = _probe_callable(payload.get("sendinput"))
    mouse_event = _probe_callable(payload.get("mouse_event"))
    pyautogui = _available(payload.get("pyautogui"))
    same_session = bool(payload.get("same_desktop_session_ready") is True or payload.get("same_desktop_session") is True)
    same_integrity = bool(payload.get("same_integrity_ready") is True or payload.get("same_integrity") is True)
    interactive = bool(payload.get("interactive_desktop_ready") is True or _probe_ok(payload.get("interactive_desktop")))
    mouse_click_ready = bool((set_cursor and (sendinput or mouse_event)) or pyautogui)
    blockers: list[str] = []

    cursor_error = _probe_error(payload.get("get_cursor_pos"))
    if not cursor:
        if _is_access_denied(cursor_error):
            blockers.append("GetCursorPos access denied")
        else:
            blockers.append("cursor_read_not_ready")
    if not mouse_click_ready:
        blockers.append("mouse_click_not_ready")
    if not same_session:
        blockers.append("same_desktop_session_not_ready")
    if not same_integrity:
        blockers.append("same_integrity_not_ready")
    if not interactive:
        blockers.append("interactive_desktop_not_ready")

    safe_context = same_session and same_integrity and interactive
    if cursor and mouse_click_ready and safe_context:
        click_backend = "computer_use_backend"
        input_ready = True
    elif (sendinput or mouse_event) and set_cursor and safe_context:
        click_backend = "win32_sendinput_backend"
        input_ready = True
    elif pyautogui and safe_context:
        click_backend = "pyautogui_backend"
        input_ready = True
    else:
        click_backend = "dry_run_backend"
        input_ready = False

    return InputGatewayHealth(
        input_gateway_ready=input_ready,
        cursor_read_ready=cursor,
        mouse_click_ready=mouse_click_ready,
        same_desktop_session_ready=same_session,
        same_integrity_ready=same_integrity,
        interactive_desktop_ready=interactive,
        click_backend=click_backend,
        blockers=blockers,
        details=payload,
    )


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
