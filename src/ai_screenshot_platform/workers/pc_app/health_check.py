from __future__ import annotations

from ai_screenshot_platform.workers.runtime.health import (
    ToolHealth,
    check_python_module,
)


def check_pc_app_health() -> dict[str, ToolHealth]:
    return {
        "pywinauto": check_python_module(
            "pywinauto",
            required_for="pc app focus and window automation smoke",
        ),
        "mss": check_python_module(
            "mss",
            required_for="pc app region screenshot smoke",
        ),
        "dxcam": check_python_module(
            "dxcam",
            required_for="pc app high-performance screenshot smoke",
        ),
    }
