from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.master.api.app import create_app
from ai_screenshot_platform.master.core.config import MasterSettings


app = create_app(MasterSettings.from_env())
