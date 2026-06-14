from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect P13.5 distributed OCR/model planning report.")
    parser.add_argument("--matrix", default="deploy/distributed_ocr_model_matrix.example.json")
    parser.add_argument("--output", default="deploy_output/p13_5_distributed_ocr_model_plan.json")
    args = parser.parse_args()

    matrix = load_json(Path(args.matrix))
    payload = {
        "schema_version": "p13.5.0",
        "status": "planned_only",
        "matrix": matrix,
        "downloaded_models": False,
        "installed_ocr": False,
        "online_inference_enabled": False,
        "enabled_true_count": 0,
        "next_action": "Review and approve per-role OCR/model download plan before P13.5.1.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "written", "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
