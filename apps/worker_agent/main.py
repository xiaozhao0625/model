from __future__ import annotations

import json
import sys
from pathlib import Path
import argparse


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.worker_agent.config import WorkerAgentConfigLoader
from ai_screenshot_platform.worker_agent.master_client import MasterApiClient
from ai_screenshot_platform.worker_agent.runtime import WorkerRuntime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Worker Agent once over HTTP.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--worker-id")
    return parser.parse_args()


def main(config_path: str, worker_id: str | None = None) -> None:
    configs = WorkerAgentConfigLoader.load_many(config_path)
    config = next(
        (
            item
            for item in configs
            if worker_id is None or item.worker_id == worker_id
        ),
        None,
    )
    if config is None:
        raise SystemExit(f"worker_id not found in config: {worker_id}")
    runtime = WorkerRuntime(
        config=config,
        client=MasterApiClient(config.master_url),
    )
    print(json.dumps(runtime.start_once(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = parse_args()
    main(args.config, args.worker_id)
