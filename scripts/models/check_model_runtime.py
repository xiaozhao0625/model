from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.model_gateway.runtime_manager import (  # noqa: E402
    ModelRuntimeManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check model runtime configuration.")
    parser.add_argument(
        "--manifest",
        default="configs/model_gateway/model_manifest.example.json",
    )
    parser.add_argument(
        "--runtime-config",
        default="configs/model_gateway/provider_runtime.example.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manager = ModelRuntimeManager(args.manifest, args.runtime_config)
    health = [asdict(item) for item in manager.check_health()]
    for item in health:
        item["local_path"] = str(item["local_path"])
    selected = manager.select_provider("act")
    print(
        json.dumps(
            {
                "model_count": len(manager.list_models()),
                "selected_provider": selected.provider_name,
                "health": health,
                "loads_real_models": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
