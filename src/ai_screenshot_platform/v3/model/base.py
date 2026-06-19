from __future__ import annotations

from abc import ABC, abstractmethod

from ai_screenshot_platform.v3.schemas import ModelRequest, ModelResult, ProviderHealth


class UiModelProvider(ABC):
    provider_name: str

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def classify_scene(self, request: ModelRequest) -> ModelResult:
        raise NotImplementedError

    @abstractmethod
    def propose_visual_candidates(self, request: ModelRequest) -> ModelResult:
        raise NotImplementedError

    @abstractmethod
    def rank_click_candidates(self, request: ModelRequest) -> ModelResult:
        raise NotImplementedError
