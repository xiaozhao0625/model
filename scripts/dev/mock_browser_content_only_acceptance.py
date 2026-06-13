from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.common.quality_gate.browser_content_gate import BrowserContentGate  # noqa: E402
from ai_screenshot_platform.common.quality_gate.contracts import ScreenshotQualityInput  # noqa: E402


def main() -> None:
    result = BrowserContentGate().evaluate(
        ScreenshotQualityInput(
            image_id="web",
            platform_type="web",
            worker_type="web",
            content_area_only=True,
            metadata={"browser_chrome_visible": False, "taskbar_visible": False},
        )
    )
    print(
        json.dumps(
            {
                "content_area_only": True,
                "accepted": result.accepted,
                "reject_reason": result.reject_reason,
                "browser_chrome_visible": result.has_browser_chrome,
                "taskbar_visible": result.has_os_taskbar,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
