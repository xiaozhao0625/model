from __future__ import annotations

import os
from pathlib import Path

from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.schemas import ModelRequest, ModelResult, ProviderHealth


class ShowUiProvider(UiModelProvider):
    provider_name = "showui"

    def __init__(self, model_dir: str | None = None, enabled: bool = False) -> None:
        self.model_dir = Path(model_dir) if model_dir is not None else _default_showui_dir()
        self.enabled = enabled

    def health(self) -> ProviderHealth:
        if not self.model_dir.exists():
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="showui_weights_missing",
                details={"model_dir": str(self.model_dir)},
            )
        return ProviderHealth(
            provider=self.provider_name,
            status="degraded" if not self.enabled else "ready",
            enabled=self.enabled,
            reason="weights_present_but_disabled" if not self.enabled else "enabled",
            details={"model_dir": str(self.model_dir)},
        )

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        return self._unavailable_result()

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return self._unavailable_result()

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        return self._unavailable_result()

    def _unavailable_result(self) -> ModelResult:
        health = self.health()
        return ModelResult(provider=self.provider_name, status=health.status, error=health.reason)


def _default_showui_dir() -> Path:
    explicit = os.environ.get("APP_SHOT_SHOWUI_MODEL_DIR")
    if explicit:
        return Path(explicit)
    model_root = os.environ.get("APP_SHOT_MODELS")
    if model_root:
        return Path(model_root) / "showui" / "ShowUI-2B"
    return Path("models/showui")
