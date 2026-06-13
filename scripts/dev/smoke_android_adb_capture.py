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


def main() -> None:
    health = check_android_adb_health()
    print(
        json.dumps(
            {
                "status": "available" if health.available else "skipped",
                "adb": asdict(health),
                "note": "P10 smoke does not require a running emulator by default.",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
