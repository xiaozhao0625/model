from __future__ import annotations

from ai_screenshot_platform.v3.schemas import ActionDecision


class ClickExecutor:
    def execute(self, decision: ActionDecision) -> dict[str, object]:
        if not decision.allowed:
            return {"executed": False, "reason": decision.reason}
        return {
            "executed": False,
            "reason": "real_click_disabled_by_default",
            "would_click": [decision.candidate.click_x, decision.candidate.click_y] if decision.candidate else None,
        }
