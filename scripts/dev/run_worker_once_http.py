from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.worker_agent.config import (  # noqa: E402
    WorkerAgentConfigLoader,
)
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient  # noqa: E402
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Worker Agent HTTP cycle.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--worker-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = WorkerAgentConfigLoader.load_many(args.config)
    config = next(
        (
            item
            for item in configs
            if args.worker_id is None or item.worker_id == args.worker_id
        ),
        None,
    )
    if config is None:
        raise SystemExit(f"worker_id not found in config: {args.worker_id}")
    result = WorkerRuntime(
        config=config,
        client=MasterApiClient(config.master_url),
    ).start_once()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
