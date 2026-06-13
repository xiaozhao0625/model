from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.workers.android.health_check import (  # noqa: E402
    check_android_adb_health,
)
from ai_screenshot_platform.workers.pc_app.health_check import (  # noqa: E402
    check_pc_app_health,
)
from ai_screenshot_platform.workers.pc_game.health_check import (  # noqa: E402
    check_pc_game_health,
)
from ai_screenshot_platform.workers.web.health_check import (  # noqa: E402
    check_web_playwright_health,
)


def main() -> None:
    pc_app = check_pc_app_health()
    pc_game = check_pc_game_health()
    payload = {
        "playwright": asdict(check_web_playwright_health()),
        "pywinauto": asdict(pc_app["pywinauto"]),
        "mss": asdict(pc_app["mss"]),
        "dxcam": asdict(pc_app["dxcam"]),
        "obs": asdict(pc_game["obs"]),
        "ffmpeg": asdict(pc_game["ffmpeg"]),
        "adb": asdict(check_android_adb_health()),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
