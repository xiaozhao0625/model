from __future__ import annotations

from ai_screenshot_platform.v3.schemas import ProviderHealth


class FastTextLanguageProvider:
    provider_name = "fasttext_language"

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self._available = False
        self._error: str | None = None
        try:
            import fasttext  # type: ignore  # noqa: F401

            self._available = bool(model_path)
        except Exception as exc:
            self._error = str(exc)

    def health(self) -> ProviderHealth:
        if not self._available:
            return ProviderHealth(
                provider=self.provider_name,
                status="unavailable",
                enabled=False,
                reason="fasttext_optional_model_missing",
                details={"model_path": self.model_path, "error": self._error},
            )
        return ProviderHealth(provider=self.provider_name, status="ready", enabled=False, details={"model_path": self.model_path})
