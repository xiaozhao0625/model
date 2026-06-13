from __future__ import annotations

from pathlib import Path

from ai_screenshot_platform.common.model_gateway.contracts import (
    ModelGatewayProvider,
    ModelTaskType,
)
from ai_screenshot_platform.common.model_gateway.mock_provider import (
    MockModelGatewayProvider,
)
from ai_screenshot_platform.model_gateway.model_health import (
    ModelHealthChecker,
    ModelHealthResult,
)
from ai_screenshot_platform.model_gateway.model_paths import (
    ModelPathInfo,
    ModelPathResolver,
)
from ai_screenshot_platform.model_gateway.provider_runtime import (
    ProviderRuntimeConfig,
    ProviderRuntimeConfigLoader,
)
from ai_screenshot_platform.model_gateway.providers.gui_actor_provider import (
    GuiActorProvider,
)
from ai_screenshot_platform.model_gateway.providers.omniparser_provider import (
    OmniParserProvider,
)
from ai_screenshot_platform.model_gateway.providers.os_atlas_provider import (
    OsAtlasProvider,
)
from ai_screenshot_platform.model_gateway.providers.qwen_vl_provider import (
    QwenVLProvider,
)
from ai_screenshot_platform.model_gateway.providers.showui_provider import (
    ShowUIProvider,
)
from ai_screenshot_platform.model_gateway.providers.ui_tars_provider import (
    UITarsProvider,
)


class ModelRuntimeManager:
    def __init__(
        self,
        manifest_path: str | Path,
        runtime_config_path: str | Path,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.runtime_config = ProviderRuntimeConfigLoader.load(runtime_config_path)
        self.resolver = ModelPathResolver(manifest_path)
        self.health_checker = ModelHealthChecker(manifest_path)
        self._loaded: dict[str, ModelGatewayProvider] = {}

    def list_models(self) -> list[ModelPathInfo]:
        return self.resolver.resolve_all()

    def check_health(self) -> list[ModelHealthResult]:
        return self.health_checker.check_all()

    def select_provider(
        self,
        task_type: ModelTaskType | str,
    ) -> ModelGatewayProvider:
        selected_name = self.runtime_config.default_provider
        if selected_name != "mock":
            provider = self.get_provider(selected_name)
            health = getattr(provider, "health", lambda: None)()
            if health is not None and getattr(health, "available", False):
                return provider
        return self.get_provider(self.runtime_config.fallback_provider)

    def get_provider(self, provider_type: str) -> ModelGatewayProvider:
        if provider_type == "mock":
            return MockModelGatewayProvider()
        return self.load_provider(provider_type)

    def load_provider(self, provider_type: str) -> ModelGatewayProvider:
        if provider_type in self._loaded:
            return self._loaded[provider_type]
        info = next(
            (
                item
                for item in self.resolver.resolve_all()
                if item.provider_type == provider_type
            ),
            None,
        )
        if info is None:
            raise ValueError(f"unknown provider_type: {provider_type}")
        enabled = provider_type in self.runtime_config.enabled_providers
        provider = self._make_provider(provider_type, info.local_path, enabled)
        self._loaded[provider_type] = provider
        return provider

    def unload_provider(self, provider_type: str) -> None:
        self._loaded.pop(provider_type, None)

    def _make_provider(
        self,
        provider_type: str,
        model_path: Path,
        enabled: bool,
    ) -> ModelGatewayProvider:
        providers = {
            "showui": ShowUIProvider,
            "omniparser": OmniParserProvider,
            "qwen_vl": QwenVLProvider,
            "ui_tars": UITarsProvider,
            "gui_actor": GuiActorProvider,
            "os_atlas": OsAtlasProvider,
        }
        try:
            return providers[provider_type](model_path=model_path, enabled=enabled)
        except KeyError as exc:
            raise ValueError(f"unsupported provider_type: {provider_type}") from exc
