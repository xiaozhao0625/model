from __future__ import annotations

from ai_screenshot_platform.v3.model.base import UiModelProvider
from ai_screenshot_platform.v3.model.mock_ui_provider import MockUiModelProvider
from ai_screenshot_platform.v3.model.omniparser_provider import OmniParserProvider
from ai_screenshot_platform.v3.model.showui_provider import ShowUiProvider
from ai_screenshot_platform.v3.schemas import ModelRequest, ModelResult, ProviderHealth


class UiModelRegistry:
    def __init__(self, providers: list[UiModelProvider] | None = None) -> None:
        self.providers = providers or [MockUiModelProvider(), ShowUiProvider(), OmniParserProvider()]

    def health(self) -> list[ProviderHealth]:
        return [provider.health() for provider in self.providers]

    def primary_ready(self) -> bool:
        return any(health.provider == "showui" and health.status == "ready" and health.enabled for health in self.health())

    def classify_scene(self, request: ModelRequest) -> ModelResult:
        return self._first_ok("classify_scene", request)

    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        return self._first_ok("propose_visual_candidates", request)

    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        return self._first_ok("rank_click_candidates", request)

    def _first_ok(self, method: str, request: ModelRequest) -> ModelResult:
        fallback: ModelResult | None = None
        for provider in self.providers:
            result = getattr(provider, method)(request)
            if result.status == "ok":
                return result
            fallback = result
        return fallback or ModelResult(provider="none", status="unavailable", error="no model provider configured")
