from __future__ import annotations

from dataclasses import dataclass

from ai_screenshot_platform.common.model_gateway.contracts import (
    ModelGatewayProvider,
    ModelTaskType,
)
from ai_screenshot_platform.common.model_gateway.provider_config import (
    ProviderConfig,
)


class ProviderRegistryError(ValueError):
    pass


class ProviderCapabilityError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderRegistryEntry:
    config: ProviderConfig
    provider: ModelGatewayProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ProviderRegistryEntry] = {}

    def register(
        self,
        provider_config: ProviderConfig,
        provider_instance: ModelGatewayProvider,
    ) -> None:
        self._entries[provider_config.provider_name] = ProviderRegistryEntry(
            config=provider_config,
            provider=provider_instance,
        )

    def get(self, provider_name: str) -> ModelGatewayProvider:
        try:
            return self._entries[provider_name].provider
        except KeyError as exc:
            raise ProviderRegistryError(f"unknown provider: {provider_name}") from exc

    def list_enabled(self) -> list[ProviderConfig]:
        return [
            entry.config
            for entry in self._entries.values()
            if entry.config.enabled
        ]

    def select_for_task(
        self,
        task_type: ModelTaskType | str,
    ) -> list[ModelGatewayProvider]:
        parsed_task_type = (
            task_type if isinstance(task_type, ModelTaskType) else ModelTaskType(task_type)
        )
        providers: list[ModelGatewayProvider] = []
        for entry in self._entries.values():
            if not entry.config.enabled:
                continue
            if self._supports_task(entry.config, parsed_task_type):
                providers.append(entry.provider)
        return providers

    def _supports_task(
        self,
        config: ProviderConfig,
        task_type: ModelTaskType,
    ) -> bool:
        if task_type == ModelTaskType.SCENE_CLASSIFY:
            return config.capabilities.supports_scene_classify
        if task_type == ModelTaskType.GROUND:
            return config.capabilities.supports_ground
        if task_type == ModelTaskType.ACT:
            return config.capabilities.supports_act
        return False
