from __future__ import annotations

from dataclasses import dataclass

from ai_screenshot_platform.common.action_gateway.contracts import ActionGatewayRequest
from ai_screenshot_platform.common.action_gateway.execution_guard import ActionGateway


@dataclass(frozen=True)
class AndroidInputResult:
    status: str
    reason: str


class AndroidInputController:
    def __init__(self, screen_width: int = 1080, screen_height: int = 1920) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.gateway = ActionGateway()

    def tap(self, x: int, y: int) -> AndroidInputResult:
        if not (0 <= x < self.screen_width and 0 <= y < self.screen_height):
            return AndroidInputResult("blocked", "coordinate_out_of_bounds")
        decision = self.gateway.evaluate(ActionGatewayRequest(action_type="tap", instruction="safe tap"))
        return AndroidInputResult("skipped" if decision.allowed else "blocked", "real_input_not_enabled")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int) -> AndroidInputResult:
        if min(x1, y1, x2, y2) < 0 or x1 >= self.screen_width or x2 >= self.screen_width:
            return AndroidInputResult("blocked", "coordinate_out_of_bounds")
        return AndroidInputResult("skipped", "real_input_not_enabled")

    def back(self) -> AndroidInputResult:
        return AndroidInputResult("skipped", "real_input_not_enabled")

    def home(self) -> AndroidInputResult:
        return AndroidInputResult("skipped", "real_input_not_enabled")

    def menu(self) -> AndroidInputResult:
        return AndroidInputResult("skipped", "real_input_not_enabled")

    def text(self, input_text: str) -> AndroidInputResult:
        return AndroidInputResult("blocked", "text_input_disabled_by_default")
