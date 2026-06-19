from __future__ import annotations

import json
from pathlib import Path


REQUIRED_PROVIDER_KEYS = {"name", "type", "path", "enabled", "sha256_required"}


def load_model_manifest(path: str | Path) -> dict[str, object]:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"model manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def validate_model_manifest(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    providers = manifest.get("providers")
    if not isinstance(providers, list):
        return ["providers must be a list"]
    for index, provider in enumerate(providers):
        if not isinstance(provider, dict):
            errors.append(f"providers[{index}] must be an object")
            continue
        missing = REQUIRED_PROVIDER_KEYS - set(provider)
        if missing:
            errors.append(f"providers[{index}] missing keys: {', '.join(sorted(missing))}")
    return errors
