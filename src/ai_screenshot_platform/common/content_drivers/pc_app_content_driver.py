from __future__ import annotations

from ai_screenshot_platform.common.content_drivers.contracts import (
    ContentDriverPlan,
    ContentDriverStep,
)


class PcAppContentDriver:
    def plan(self, context: dict) -> ContentDriverPlan:
        return ContentDriverPlan(
            "pc_app",
            [
                ContentDriverStep("focus_safe_panel", "聚焦安全内容区域", {}),
                ContentDriverStep("scroll", "滚动文档或列表内容", {"delta_y": 400}),
                ContentDriverStep("capture_hint", "提示采集低频内容截图", {"bucket": "low"}),
            ],
        )
