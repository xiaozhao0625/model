from __future__ import annotations

import os
import time
from collections.abc import Callable

from ai_screenshot_platform.v3.schemas import ActionDecision


class ClickExecutor:
    def __init__(
        self,
        allow_real_click: bool | None = None,
        click_backend: Callable[[int, int], None] | None = None,
    ) -> None:
        self.allow_real_click = (
            os.environ.get("APP_SHOT_ALLOW_REAL_CLICK", "").strip() == "1"
            if allow_real_click is None
            else allow_real_click
        )
        self.click_backend = click_backend or _windows_left_click

    def execute(self, decision: ActionDecision) -> dict[str, object]:
        click_target = [decision.candidate.click_x, decision.candidate.click_y] if decision.candidate else None
        if not decision.allowed:
            return {"executed": False, "reason": decision.reason, "status": "blocked", "would_click": click_target}
        if not decision.candidate:
            return {"executed": False, "reason": "missing_candidate", "status": "stopped", "would_click": None}
        if not self.allow_real_click:
            return {
                "executed": False,
                "reason": "real_click_disabled_by_default",
                "status": "stopped",
                "would_click": click_target,
            }
        self.click_backend(decision.candidate.click_x, decision.candidate.click_y)
        return {
            "executed": True,
            "reason": "real_click_executed",
            "clicked": click_target,
        }


def _windows_left_click(x: int, y: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
