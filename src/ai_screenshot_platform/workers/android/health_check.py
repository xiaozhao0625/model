from __future__ import annotations

from ai_screenshot_platform.workers.runtime.health import ToolHealth, check_command


def check_android_adb_health() -> ToolHealth:
    return check_command("adb", required_for="android real capture smoke")
