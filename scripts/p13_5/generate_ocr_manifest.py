from __future__ import annotations

import argparse
import json
from pathlib import Path


ROLE_ROOTS = {"M0": r"E:\work", "W1": r"D:\work", "W2": r"D:\work", "W3": r"D:\work"}


def manifest_for(role: str) -> dict:
    root = ROLE_ROOTS[role]
    preferred = role in {"W2", "W3"}
    central = role == "M0"
    optional = role == "W1"
    return {
        "schema_version": "p13.5.0",
        "role": role,
        "root": root,
        "enabled": False,
        "install_now": False,
        "download_weights_now": False,
        "online_inference_enabled": False,
        "engines": [
            {
                "name": "paddleocr",
                "enabled": False,
                "status": "planned",
                "install_priority": "preferred" if preferred else "central_fallback" if central else "optional",
                "install_scope": "local_worker" if preferred else "central" if central else "optional_idle_only",
                "runtime_dir": rf"{root}\ocr\engines\paddleocr",
                "venv": rf"{root}\model_runtime\venvs\ocr-runtime",
                "source": "official_or_pypi",
                "version": "to_be_selected",
                "hash_recorded": False,
                "idle_only": True,
                "manual_confirmation_required": True,
            },
            {
                "name": "easyocr",
                "enabled": False,
                "status": "planned",
                "install_priority": "fallback",
                "install_scope": "optional_idle_only" if optional else "local_or_central_fallback",
                "runtime_dir": rf"{root}\ocr\engines\easyocr",
                "venv": rf"{root}\model_runtime\venvs\ocr-runtime",
                "source": "official_or_pypi",
                "version": "to_be_selected",
                "hash_recorded": False,
                "idle_only": True,
                "manual_confirmation_required": True,
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local P13.5 OCR manifest without installing OCR.")
    parser.add_argument("--role", choices=sorted(ROLE_ROOTS), default="M0")
    parser.add_argument("--output", default="deploy/ocr_manifest.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest_for(args.role), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "written", "output": str(output), "role": args.role, "enabled": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
