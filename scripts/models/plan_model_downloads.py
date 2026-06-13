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

from ai_screenshot_platform.model_gateway.download_plan import (  # noqa: E402
    ModelDownloadPlanner,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan model downloads without downloading.")
    parser.add_argument(
        "--manifest",
        default="configs/model_gateway/model_manifest.example.json",
    )
    parser.add_argument("--write-plan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    items = [asdict(item) for item in ModelDownloadPlanner(args.manifest).plan()]
    for item in items:
        item["target_path"] = str(item["target_path"])
    payload = {
        "dry_run": True,
        "downloads_started": False,
        "items": items,
    }
    if args.write_plan:
        Path(args.write_plan).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
