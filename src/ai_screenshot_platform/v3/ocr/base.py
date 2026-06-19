from __future__ import annotations

from abc import ABC, abstractmethod

from ai_screenshot_platform.v3.schemas import OcrResult, ProviderHealth


class OcrProvider(ABC):
    provider_name: str

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def recognize(self, image_path: str) -> OcrResult:
        raise NotImplementedError
