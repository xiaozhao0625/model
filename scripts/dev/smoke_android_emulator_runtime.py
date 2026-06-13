from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.workers.android.android_runtime_health import AndroidRuntimeHealthCheck  # noqa: E402


def main() -> None:
    result = AndroidRuntimeHealthCheck().check()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
