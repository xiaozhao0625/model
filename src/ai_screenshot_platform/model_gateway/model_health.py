from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_screenshot_platform.model_gateway.model_paths import ModelPathResolver


@dataclass(frozen=True)
class ModelHealthResult:
    model_id: str
    provider_type: str
    available: bool
    status: str
    reason: str
    local_path: Path
    missing_files: list[str]
    gpu_required: bool
    vram_budget_gb: int


class ModelHealthChecker:
    def __init__(self, manifest_path: str | Path) -> None:
        self.resolver = ModelPathResolver(manifest_path)

    def check_all(self) -> list[ModelHealthResult]:
        return [self.check(info.model_id) for info in self.resolver.resolve_all()]

    def check(self, model_id: str) -> ModelHealthResult:
        info = self.resolver.resolve(model_id)
        entry = info.entry
        if entry.load_mode == "disabled":
            status = "disabled"
            available = False
            reason = "model is disabled by manifest"
        elif not info.exists or info.missing_files:
            status = "missing_files"
            available = False
            reason = "model path or expected files are missing"
        else:
            status = "available"
            available = True
            reason = "model files are present"
        return ModelHealthResult(
            model_id=info.model_id,
            provider_type=info.provider_type,
            available=available,
            status=status,
            reason=reason,
            local_path=info.local_path,
            missing_files=info.missing_files,
            gpu_required=entry.gpu_required,
            vram_budget_gb=entry.vram_budget_gb,
        )
