from __future__ import annotations

import argparse
import json
from pathlib import Path


ROLE_ROOTS = {"M0": r"E:\work", "W1": r"D:\work", "W2": r"D:\work", "W3": r"D:\work"}


def providers_for(role: str) -> list[dict]:
    root = ROLE_ROOTS[role]
    heavy_allowed = role == "M0"
    light_preferred = role in {"W2", "W3"}
    game_worker = role == "W1"
    providers = [
        {
            "name": "omniparser",
            "enabled": False,
            "status": "planned",
            "model_dir": rf"{root}\models\omniparser",
            "planned_role": "central_heavy" if heavy_allowed else "local_light_optional" if light_preferred else "idle_only_optional",
            "gpu_required": True,
            "min_vram_gb": 8,
            "estimated_vram_gb": "6-8",
            "download_now": False,
            "idle_only": not heavy_allowed,
            "manual_confirmation_required": True,
        },
        {
            "name": "showui",
            "enabled": False,
            "status": "planned",
            "model_dir": rf"{root}\models\showui",
            "planned_role": "central_or_local_light" if not game_worker else "idle_only_optional",
            "gpu_required": True,
            "min_vram_gb": 6,
            "estimated_vram_gb": "4-6",
            "download_now": False,
            "idle_only": True,
            "manual_confirmation_required": True,
        },
        {
            "name": "qwen_vl",
            "enabled": False,
            "status": "planned",
            "model_dir": rf"{root}\models\qwen_vl",
            "planned_role": "central_only" if heavy_allowed else "m0_fallback",
            "gpu_required": True,
            "min_vram_gb": 12,
            "estimated_vram_gb": "10-14",
            "download_now": False,
            "idle_only": True,
            "manual_confirmation_required": True,
        },
    ]
    if role in {"W1", "W3"}:
        providers[-1]["status"] = "blocked_on_worker_heavy_model_policy"
    return providers


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local P13.5 model manifest without downloading models.")
    parser.add_argument("--role", choices=sorted(ROLE_ROOTS), default="M0")
    parser.add_argument("--output", default="deploy/model_manifest.json")
    args = parser.parse_args()

    payload = {
        "schema_version": "p13.5.0",
        "role": args.role,
        "root": ROLE_ROOTS[args.role],
        "enabled": False,
        "download_now": False,
        "online_inference_enabled": False,
        "providers": providers_for(args.role),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "written", "output": str(output), "role": args.role, "enabled": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
