from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_screenshot_platform.master.api.app import create_app  # noqa: E402
from ai_screenshot_platform.master.core.config import MasterSettings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Master API over HTTP.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database-url", default="sqlite:///runs/master/master.db")
    parser.add_argument("--data-root", default="runs/master")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import uvicorn

    app = create_app(
        MasterSettings(
            database_url=args.database_url,
            redis_url="memory://",
            env="development",
            data_root=args.data_root,
        )
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
