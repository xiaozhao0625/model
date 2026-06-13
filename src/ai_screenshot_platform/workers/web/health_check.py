from __future__ import annotations

from ai_screenshot_platform.workers.runtime.health import (
    ToolHealth,
    check_python_module,
)


def check_web_playwright_health() -> ToolHealth:
    return check_python_module(
        "playwright",
        required_for="web real capture smoke",
        display_name="playwright",
    )
