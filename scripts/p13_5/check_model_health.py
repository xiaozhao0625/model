from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ROLE_ROOTS = {"M0": r"E:\work", "W1": r"D:\work", "W2": r"D:\work", "W3": r"D:\work"}
PROVIDERS = {
    "omniparser": {"min_vram_gb": 8, "estimated_vram_gb": "6-8"},
    "showui": {"min_vram_gb": 6, "estimated_vram_gb": "4-6"},
    "qwen_vl": {"min_vram_gb": 12, "estimated_vram_gb": "10-14"},
}


def gpu_report() -> dict:
    if shutil.which("nvidia-smi") is None:
        return {"status": "missing", "gpus": []}
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return {"status": "failed", "error": result.stderr.strip(), "gpus": []}
    gpus = []
    for line in result.stdout.splitlines():
        parts = [item.strip() for item in line.split(",")]
        if len(parts) >= 4:
            gpus.append(
                {
                    "name": parts[0],
                    "memory_total_mb": int(parts[1]),
                    "memory_free_mb": int(parts[2]),
                    "driver_version": parts[3],
                }
            )
    return {"status": "available" if gpus else "missing", "gpus": gpus}


def provider_status(provider: str, root: str) -> dict:
    model_dir = Path(root) / "models" / provider
    weights = list(model_dir.glob("*.safetensors")) + list(model_dir.glob("*.pt")) + list(model_dir.glob("*.onnx"))
    status = "missing_weights" if not weights else "planned_weights_present"
    return {
        "provider": provider,
        "enabled": False,
        "status": status,
        "model_dir": str(model_dir),
        "model_dir_exists": model_dir.exists(),
        "weights_found_count": len(weights),
        "gpu_required": True,
        "min_vram_gb": PROVIDERS[provider]["min_vram_gb"],
        "estimated_vram_gb": PROVIDERS[provider]["estimated_vram_gb"],
        "inference_attempted": False,
        "download_attempted": False,
        "next_action": "record source/version/hash before any download or load",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check planned model provider health without downloading or loading models.")
    parser.add_argument("--role", choices=sorted(ROLE_ROOTS), default="M0")
    args = parser.parse_args()
    root = ROLE_ROOTS[args.role]
    payload = {
        "schema_version": "p13.5.0",
        "role": args.role,
        "online_inference_enabled": False,
        "download_attempted": False,
        "gpu": gpu_report(),
        "providers": [provider_status(provider, root) for provider in PROVIDERS],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
