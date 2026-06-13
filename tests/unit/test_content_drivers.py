from __future__ import annotations

from ai_screenshot_platform.common.content_drivers.pc_app_content_driver import PcAppContentDriver
from ai_screenshot_platform.common.content_drivers.web_content_driver import WebContentDriver


def test_content_drivers_return_safe_variation_plans():
    web = WebContentDriver().plan({"url": "https://example.com"})
    pc = PcAppContentDriver().plan({"window_title": "Editor"})

    assert web.steps
    assert pc.steps
    assert all(step.action_type != "send_chat" for step in web.steps + pc.steps)
