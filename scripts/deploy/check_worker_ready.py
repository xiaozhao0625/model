from __future__ import annotations

import argparse
import json
import shutil


TOOLS_BY_WORKER = {
    "pc_game": ["obs64", "ffmpeg"],
    "pc_app_web": ["playwright", "python"],
    "android": ["adb"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-type", required=True, choices=sorted(TOOLS_BY_WORKER))
    args = parser.parse_args()
    tools = {tool: ("available" if shutil.which(tool) else "unavailable") for tool in TOOLS_BY_WORKER[args.worker_type]}
    print(
        json.dumps(
            {
                "worker_type": args.worker_type,
                "tools": tools,
                "real_capture_started": False,
                "missing_tools_are_skipped": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
