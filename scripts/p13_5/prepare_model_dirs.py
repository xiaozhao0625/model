from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_NODES = {
    "M0": Path(r"E:\work"),
    "W1": Path(r"D:\work"),
    "W2": Path(r"D:\work"),
    "W3": Path(r"D:\work"),
}

SUBDIRS = [
    "models",
    "models\\manifest",
    "models\\downloads",
    "models\\omniparser",
    "models\\showui",
    "models\\qwen_vl",
    "ocr",
    "ocr\\engines",
    "ocr\\engines\\paddleocr",
    "ocr\\engines\\easyocr",
    "ocr\\cache",
    "ocr\\reports",
    "model_runtime",
    "model_runtime\\venvs",
    "model_runtime\\logs",
    "model_runtime\\health",
    "model_runtime\\smoke_outputs",
]


def role_dirs(role: str) -> list[Path]:
    root = DEFAULT_NODES[role]
    return [root / item for item in SUBDIRS]


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or create P13.5 OCR/model runtime directories.")
    parser.add_argument("--role", choices=sorted(DEFAULT_NODES), default="M0")
    parser.add_argument("--create", action="store_true", help="Create directories. Default is plan-only.")
    args = parser.parse_args()

    rows = []
    for directory in role_dirs(args.role):
        exists_before = directory.exists()
        if args.create:
            directory.mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "role": args.role,
                "path": str(directory),
                "exists_before": exists_before,
                "exists_after": directory.exists(),
                "action": "created_or_exists" if args.create else "planned_only",
            }
        )

    print(json.dumps({"role": args.role, "create": args.create, "directories": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
