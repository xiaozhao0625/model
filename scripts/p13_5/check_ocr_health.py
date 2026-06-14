from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROLE_ROOTS = {"M0": r"E:\work", "W1": r"D:\work", "W2": r"D:\work", "W3": r"D:\work"}


def engine_status(engine: str, root: str) -> dict:
    package_name = "paddleocr" if engine == "paddleocr" else "easyocr"
    package_found = importlib.util.find_spec(package_name) is not None
    runtime_dir = Path(root) / "ocr" / "engines" / engine
    return {
        "engine": engine,
        "enabled": False,
        "status": "import_ok" if package_found else "planned_missing",
        "runtime_dir": str(runtime_dir),
        "runtime_dir_exists": runtime_dir.exists(),
        "package_found": package_found,
        "version": "not_imported",
        "install_attempted": False,
        "weights_downloaded": False,
        "next_action": "manual install confirmation required before P13.5.1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check planned OCR runtime health without installing OCR.")
    parser.add_argument("--role", choices=sorted(ROLE_ROOTS), default="M0")
    args = parser.parse_args()
    root = ROLE_ROOTS[args.role]
    payload = {
        "schema_version": "p13.5.0",
        "role": args.role,
        "online_inference_enabled": False,
        "install_attempted": False,
        "engines": [engine_status("paddleocr", root), engine_status("easyocr", root)],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
