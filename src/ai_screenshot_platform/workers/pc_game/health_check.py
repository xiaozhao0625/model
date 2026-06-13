from __future__ import annotations

from ai_screenshot_platform.workers.runtime.health import (
    ToolHealth,
    check_command,
    check_python_module,
)


def check_pc_game_health() -> dict[str, ToolHealth]:
    obs_module = check_python_module(
        "obsws_python",
        required_for="pc game obs websocket smoke",
        display_name="obs-websocket python client",
    )
    obs_command = check_command("obs64", required_for="pc game obs smoke")
    obs_available = obs_module.available and obs_command.available
    return {
        "obs": ToolHealth(
            name="obs",
            available=obs_available,
            version=None,
            reason="obs command and websocket client are available"
            if obs_available
            else f"{obs_command.reason}; {obs_module.reason}",
            required_for="pc game obs smoke",
        ),
        "ffmpeg": check_command("ffmpeg", required_for="pc game frame extraction smoke"),
    }
