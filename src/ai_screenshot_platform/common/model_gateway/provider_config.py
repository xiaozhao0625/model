from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class ProviderConfigError(ValueError):
    pass


class ProviderType(StrEnum):
    MOCK = "mock"
    UI_TARS = "ui_tars"
    SHOWUI = "showui"
    QWEN_VL = "qwen_vl"
    OMNIPARSER = "omniparser"
    GUI_ACTOR = "gui_actor"
    OS_ATLAS = "os_atlas"


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_scene_classify: bool
    supports_ground: bool
    supports_act: bool
    requires_gpu: bool
    default_device: str


@dataclass(frozen=True)
class ProviderConfig:
    provider_name: str
    provider_type: ProviderType
    enabled: bool
    capabilities: ProviderCapabilities
    config: dict[str, Any] = field(default_factory=dict)


class ProviderConfigLoader:
    @classmethod
    def load(cls, path: str | Path) -> list[ProviderConfig]:
        resolved_path = Path(path).resolve()
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        providers = payload.get("providers")
        if not isinstance(providers, list):
            raise ProviderConfigError("provider config must contain providers list")
        return [cls._parse_provider(item) for item in providers]

    @classmethod
    def _parse_provider(cls, payload: dict[str, Any]) -> ProviderConfig:
        try:
            provider_type = ProviderType(str(payload["provider_type"]))
        except ValueError as exc:
            raise ProviderConfigError(
                f"unknown provider_type: {payload.get('provider_type')}"
            ) from exc

        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, dict):
            raise ProviderConfigError("provider capabilities must be an object")

        return ProviderConfig(
            provider_name=str(payload["provider_name"]),
            provider_type=provider_type,
            enabled=bool(payload.get("enabled", False)),
            capabilities=ProviderCapabilities(
                supports_scene_classify=bool(
                    capabilities["supports_scene_classify"]
                ),
                supports_ground=bool(capabilities["supports_ground"]),
                supports_act=bool(capabilities["supports_act"]),
                requires_gpu=bool(capabilities["requires_gpu"]),
                default_device=str(capabilities["default_device"]),
            ),
            config=dict(payload.get("config", {})),
        )
