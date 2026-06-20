from __future__ import annotations

import os
import time
from collections.abc import Callable

from ai_screenshot_platform.v3.action.input_gateway import load_input_gateway_readiness
from ai_screenshot_platform.v3.schemas import ActionDecision


class ClickExecutor:
    def __init__(
        self,
        allow_real_click: bool | None = None,
        click_backend: Callable[[int, int], None] | None = None,
        click_backend_name: str | None = None,
        target_client_rect: tuple[int, int, int, int] | None = None,
    ) -> None:
        self.allow_real_click = (
            os.environ.get("APP_SHOT_ALLOW_REAL_CLICK", "").strip() == "1"
            if allow_real_click is None
            else allow_real_click
        )
        self.target_client_rect = target_client_rect
        if click_backend is not None:
            self.click_backend = click_backend
            self.click_backend_name = click_backend_name or "custom_backend"
        else:
            readiness = load_input_gateway_readiness()
            requested_backend = os.environ.get("APP_SHOT_CLICK_BACKEND", "").strip()
            self.click_backend_name = requested_backend or _in_process_backend_name(readiness.click_backend)
            self.click_backend = _windows_sendinput_click if self.click_backend_name != "dry_run_backend" else _dry_run_click

    def execute(self, decision: ActionDecision) -> dict[str, object]:
        click_target = [decision.candidate.click_x, decision.candidate.click_y] if decision.candidate else None
        if not decision.allowed:
            return {
                "executed": False,
                "reason": decision.reason,
                "status": "blocked",
                "would_click": click_target,
                "click_backend": self.click_backend_name,
            }
        if not decision.candidate:
            return {
                "executed": False,
                "reason": "missing_candidate",
                "status": "stopped",
                "would_click": None,
                "click_backend": self.click_backend_name,
            }
        if not self.allow_real_click:
            return {
                "executed": False,
                "reason": "real_click_disabled_by_default",
                "status": "stopped",
                "would_click": click_target,
                "click_backend": self.click_backend_name,
            }
        guard = self._client_area_guard(decision.candidate.click_x, decision.candidate.click_y)
        if guard:
            return {
                "executed": False,
                "reason": guard,
                "status": "blocked",
                "would_click": click_target,
                "click_backend": self.click_backend_name,
            }
        if self.click_backend_name == "dry_run_backend":
            return {
                "executed": False,
                "reason": "input_gateway_not_ready",
                "status": "stopped",
                "would_click": click_target,
                "click_backend": self.click_backend_name,
            }
        self.click_backend(decision.candidate.click_x, decision.candidate.click_y)
        return {
            "executed": True,
            "reason": "real_click_executed",
            "clicked": click_target,
            "click_backend": self.click_backend_name,
        }

    def _client_area_guard(self, x: int, y: int) -> str | None:
        if self.target_client_rect is None:
            return None
        left, top, right, bottom = self.target_client_rect
        if x < left or x > right or y < top or y > bottom:
            return "outside_target_client_area"
        return None


def _windows_sendinput_click(x: int, y: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)

    class MouseInput(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("mi", MouseInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("union", InputUnion)]

    extra = ctypes.c_ulong(0)
    inputs = (Input * 2)(
        Input(type=0, union=InputUnion(mi=MouseInput(0, 0, 0, 0x0002, 0, ctypes.pointer(extra)))),
        Input(type=0, union=InputUnion(mi=MouseInput(0, 0, 0, 0x0004, 0, ctypes.pointer(extra)))),
    )
    sent = user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(Input))
    if sent != 2:
        raise OSError("SendInput failed")


def _dry_run_click(x: int, y: int) -> None:
    return None


def _in_process_backend_name(readiness_backend: str) -> str:
    if readiness_backend == "computer_use_backend":
        return "win32_sendinput_backend"
    return readiness_backend
