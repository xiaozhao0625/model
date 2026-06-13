from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.workers.pc_game.health_check import (  # noqa: E402
    check_pc_game_health,
)


def main() -> None:
    health = check_pc_game_health()
    available = health["obs"].available and health["ffmpeg"].available
    print(
        json.dumps(
            {
                "status": "available" if available else "skipped",
                "obs": asdict(health["obs"]),
                "ffmpeg": asdict(health["ffmpeg"]),
                "note": "P10 smoke only checks optional tool readiness; no game input is executed.",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
