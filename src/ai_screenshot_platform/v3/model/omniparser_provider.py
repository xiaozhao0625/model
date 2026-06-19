from __future__ import annotations

from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.schemas import ModelRequest, ModelResult, ProviderHealth


class OmniParserProvider(UiModelProvider):
    provider_name = "omniparser"

    def __init__(self, license_accepted: bool = False) -> None:
        self.license_accepted = license_accepted

    def health(self) -> ProviderHealth:
        if not self.license_accepted:
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="license_gate_not_accepted",
            )
        return ProviderHealth(provider=self.provider_name, status="degraded", enabled=False, reason="optional_provider_not_configured")

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        return self._blocked()

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return self._blocked()

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        return self._blocked()

    def _blocked(self) -> ModelResult:
        health = self.health()
        return ModelResult(provider=self.provider_name, status=health.status, error=health.reason)
