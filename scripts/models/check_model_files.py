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

from ai_screenshot_platform.model_gateway.model_health import (  # noqa: E402
    ModelHealthChecker,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check model files from manifest.")
    parser.add_argument(
        "--manifest",
        default="configs/model_gateway/model_manifest.example.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = [asdict(item) for item in ModelHealthChecker(args.manifest).check_all()]
    for item in results:
        item["local_path"] = str(item["local_path"])
    print(json.dumps({"models": results}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
