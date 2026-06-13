from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_MODELS = {
    "ui_tars",
    "showui",
    "qwen_vl",
    "omniparser",
    "gui_actor",
    "os_atlas",
}
ALLOWED_LOAD_MODES = {"resident", "on_demand"}


class ManifestCheckError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ManifestCheckError(f"manifest not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ManifestCheckError(f"invalid JSON in manifest: {path}") from error


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        raise ManifestCheckError("models must be a non-empty list")

    model_ids: list[str] = []
    load_modes: list[str] = []
    for model in models:
        if not isinstance(model, dict):
            raise ManifestCheckError("model entry must be an object")
        model_id = require_string(model, "model_id")
        require_string(model, "provider_type")
        require_string(model, "display_name")
        require_string(model, "target_machine")
        require_string(model, "local_path")
        load_mode = require_string(model, "load_mode")
        if load_mode not in ALLOWED_LOAD_MODES:
            raise ManifestCheckError(f"invalid load_mode for {model_id}: {load_mode}")
        vram_budget = model.get("vram_budget_gb")
        if not isinstance(vram_budget, int) or vram_budget <= 0:
            raise ManifestCheckError(f"vram_budget_gb must be a positive integer for {model_id}")
        require_string(model, "health_check_mode")
        model_ids.append(model_id)
        load_modes.append(load_mode)

    missing_models = REQUIRED_MODELS - set(model_ids)
    if missing_models:
        raise ManifestCheckError(f"missing required models: {sorted(missing_models)}")

    return {
        "valid": True,
        "manifest_name": manifest.get("manifest_name"),
        "model_count": len(models),
        "model_ids": model_ids,
        "load_modes": sorted(set(load_modes)),
        "requires_model_files": False,
    }


def require_string(model: dict[str, Any], key: str) -> str:
    value = model.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestCheckError(f"{key} is required")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a model manifest JSON file.")
    parser.add_argument("--manifest", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = validate_manifest(load_json(Path(args.manifest)))
    except ManifestCheckError as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
