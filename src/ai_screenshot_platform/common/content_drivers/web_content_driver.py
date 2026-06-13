from __future__ import annotations

from ai_screenshot_platform.common.content_drivers.contracts import (
    ContentDriverPlan,
    ContentDriverStep,
)


class WebContentDriver:
    def plan(self, context: dict) -> ContentDriverPlan:
        return ContentDriverPlan(
            "web",
            [
                ContentDriverStep("scroll", "滚动网页有效内容区", {"delta_y": 600}),
                ContentDriverStep("wait", "等待内容稳定", {"duration_ms": 500}),
                ContentDriverStep("capture_hint", "提示采集内容区截图", {"content_area_only": True}),
            ],
        )
