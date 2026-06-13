from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_LOAD_MODES = {"resident", "on_demand", "disabled"}


@dataclass(frozen=True)
class ModelManifestEntry:
    model_id: str
    provider_type: str
    display_name: str
    target_machine: str
    local_path: str
    enabled_by_default: bool
    load_mode: str
    gpu_required: bool
    vram_budget_gb: int
    health_check_mode: str
    notes: str
    expected_files: list[str]
    download: dict[str, Any]
    runtime: dict[str, Any]


@dataclass(frozen=True)
class ModelPathInfo:
    model_id: str
    provider_type: str
    local_path: Path
    exists: bool
    missing_files: list[str]
    target_machine: str
    load_mode: str
    entry: ModelManifestEntry


class ModelManifestError(ValueError):
    pass


class ModelPathResolver:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()
        self.model_root = str(self.manifest.get("model_root", "models"))

    def resolve_all(self) -> list[ModelPathInfo]:
        return [self.resolve(entry.model_id) for entry in self.entries()]

    def resolve(self, model_id: str) -> ModelPathInfo:
        entry = next((item for item in self.entries() if item.model_id == model_id), None)
        if entry is None:
            raise ModelManifestError(f"unknown model_id: {model_id}")
        local_path = self._resolve_local_path(entry)
        missing_files = [
            name for name in entry.expected_files if not (local_path / name).exists()
        ]
        return ModelPathInfo(
            model_id=entry.model_id,
            provider_type=entry.provider_type,
            local_path=local_path,
            exists=local_path.exists(),
            missing_files=missing_files,
            target_machine=entry.target_machine,
            load_mode=entry.load_mode,
            entry=entry,
        )

    def entries(self) -> list[ModelManifestEntry]:
        models = self.manifest.get("models")
        if not isinstance(models, list) or not models:
            raise ModelManifestError("models must be a non-empty list")
        return [self._parse_entry(item) for item in models]

    def _load_manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _parse_entry(self, payload: dict[str, Any]) -> ModelManifestEntry:
        load_mode = str(payload["load_mode"])
        if load_mode not in ALLOWED_LOAD_MODES:
            raise ModelManifestError(f"invalid load_mode: {load_mode}")
        expected_files = payload.get("expected_files")
        if not isinstance(expected_files, list):
            raise ModelManifestError("expected_files must be a list")
        download = payload.get("download")
        runtime = payload.get("runtime")
        if not isinstance(download, dict) or not isinstance(runtime, dict):
            raise ModelManifestError("download and runtime must be objects")
        return ModelManifestEntry(
            model_id=str(payload["model_id"]),
            provider_type=str(payload["provider_type"]),
            display_name=str(payload["display_name"]),
            target_machine=str(payload["target_machine"]),
            local_path=str(payload["local_path"]),
            enabled_by_default=bool(payload["enabled_by_default"]),
            load_mode=load_mode,
            gpu_required=bool(payload["gpu_required"]),
            vram_budget_gb=int(payload["vram_budget_gb"]),
            health_check_mode=str(payload["health_check_mode"]),
            notes=str(payload.get("notes", "")),
            expected_files=[str(item) for item in expected_files],
            download=dict(download),
            runtime=dict(runtime),
        )

    def _resolve_local_path(self, entry: ModelManifestEntry) -> Path:
        raw = Path(entry.local_path)
        if raw.is_absolute():
            return raw
        env_root = os.environ.get("MODEL_ROOT")
        if env_root:
            parts = raw.parts
            if parts and parts[0] == self.model_root:
                return Path(env_root, *parts[1:])
            return Path(env_root) / raw
        return (self.manifest_path.parent / ".." / ".." / raw).resolve()
