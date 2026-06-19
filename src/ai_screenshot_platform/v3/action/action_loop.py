from __future__ import annotations

from ai_screenshot_platform.v3.action.click_executor import ClickExecutor
from ai_screenshot_platform.v3.action.safety_gate import SafetyGate
from ai_screenshot_platform.v3.schemas import FusedCandidate


class ActionLoop:
    def __init__(self, safety_gate: SafetyGate | None = None, executor: ClickExecutor | None = None) -> None:
        self.safety_gate = safety_gate or SafetyGate()
        self.executor = executor or ClickExecutor()

    def observe_or_click(self, candidate: FusedCandidate, observe_only: bool = True) -> dict[str, object]:
        decision = self.safety_gate.evaluate("click", candidate=candidate, observe_only=observe_only)
        result = self.executor.execute(decision)
        return {"decision": decision.model_dump(), "result": result}
