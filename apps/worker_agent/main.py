from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.worker_agent.config import WorkerAgentConfigLoader
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime


def main(config_path: str) -> None:
    config = WorkerAgentConfigLoader.load_many(config_path)[0]
    runtime = WorkerRuntime(
        config=config,
        client=MasterApiClient(config.master_url),
    )
    print(json.dumps(runtime.start_once(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m apps.worker_agent.main <config.json>")
    main(sys.argv[1])
